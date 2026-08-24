import os
import requests
import json
import streamlit as st

OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/generate")
LOCAL_MODEL = os.getenv("LOCAL_LLM_MODEL", "llama3.1:8b")

# Candidate Groq models in order of speed and capability
CANDIDATE_GROQ_MODELS = [
    "openai/gpt-oss-20b",
    "llama-3.3-70b-versatile",
    "qwen/qwen3.6-27b",
    "openai/gpt-oss-120b",
    "llama-3.1-8b-instant"
]

def get_active_groq_key() -> str:
    """Safely retrieves the Groq API key from Streamlit secrets or environment."""
    try:
        if hasattr(st, "secrets") and "GROQ_API_KEY" in st.secrets:
            return st.secrets["GROQ_API_KEY"]
    except Exception:
        pass
    return os.getenv("GROQ_API_KEY", "")

def get_available_groq_model(api_key: str) -> str:
    """Queries Groq /v1/models to find the best active chat model."""
    try:
        res = requests.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {api_key.strip()}"},
            timeout=3
        )
        if res.status_code == 200:
            available = [m["id"] for m in res.json().get("data", [])]
            for candidate in CANDIDATE_GROQ_MODELS:
                if candidate in available:
                    return candidate
            if available:
                # Return the first text completion model available
                text_models = [m for m in available if "whisper" not in m and "guard" not in m]
                if text_models:
                    return text_models[0]
    except Exception:
        pass
    return CANDIDATE_GROQ_MODELS[0]

def query_groq_api(prompt: str, system_prompt: str = "You are a quantitative fantasy football auction draft analyst. Be direct, tactical, and concise. No fluff.") -> str:
    """Ultra-fast cloud inference via Groq API (~300-1000 tokens/sec)."""
    api_key = get_active_groq_key()
    if not api_key:
        return "⚠️ Missing Groq API Key. Add `GROQ_API_KEY` to Streamlit Secrets or .streamlit/secrets.toml."
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json"
    }
    
    # Auto-resolve best available active model
    active_model = get_available_groq_model(api_key)
    
    payload = {
        "model": active_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.25,
        "max_tokens": 220
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=6)
        if res.status_code == 200:
            return res.json()["choices"][0]["message"]["content"].strip()
        
        # Fallback loop across candidates if specific model fails
        for fallback_model in CANDIDATE_GROQ_MODELS:
            if fallback_model != active_model:
                payload["model"] = fallback_model
                res_fb = requests.post(url, headers=headers, json=payload, timeout=4)
                if res_fb.status_code == 200:
                    return res_fb.json()["choices"][0]["message"]["content"].strip()
                    
        return f"⚠️ Groq API Error ({res.status_code}): {res.text}"
    except Exception as e:
        return f"⚠️ Groq Connection Notice: {e}"

def query_local_ollama(prompt: str, system_prompt: str = "") -> str:
    """Queries local Ollama endpoint if available."""
    full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
    payload = {
        "model": LOCAL_MODEL,
        "prompt": full_prompt,
        "stream": False,
        "options": {"temperature": 0.25, "num_predict": 180}
    }
    try:
        res = requests.post(OLLAMA_API_URL, json=payload, timeout=2)
        if res.status_code == 200:
            return res.json().get("response", "").strip()
    except Exception:
        pass
    return ""

def query_llm_hybrid(prompt: str, system_prompt: str = "You are an elite fantasy football auction strategist.") -> str:
    """Routes to local Ollama if online; otherwise routes directly to Groq Cloud."""
    local_resp = query_local_ollama(prompt, system_prompt)
    if local_resp:
        return f"*(Local Ollama)*\n\n{local_resp}"
    
    groq_resp = query_groq_api(prompt, system_prompt)
    return f"*(Groq Cloud)*\n\n{groq_resp}"

# ==============================================================================
# 3 LIVE AI FEATURES
# ==============================================================================

def generate_tactical_advice(player_name, pos, fair_val, mkt_val, max_bid_to, inflation_index, news_note, my_budget, rivals_summary):
    """Feature 1: Situational Bid / Fade Recommendation."""
    prompt = f"""
SITUATION:
- Player: {player_name} ({pos})
- Model True Value: ${fair_val} | Market ADP: ${mkt_val} | Recommended Max Bid-To: ${max_bid_to}
- Draft Room Inflation: {inflation_index}x (>1.0x overpaying, <1.0x bargains)
- Medical / Beat News: {news_note if news_note else 'Healthy & Active'}
- Your Budget Left: ${my_budget}
- Key Rivals & Tendencies: {rivals_summary}

TASK:
Give 2-3 direct bullet points on:
1. Exact bid/fade verdict (Anchor stud vs. Price-enforce trap vs. Fade).
2. The exact hard dollar cutoff where you must bail.
3. Specific rival to exploit or avoid bidding against on this player.
No conversational intro.
"""
    return query_llm_hybrid(prompt)

def generate_ai_nomination(nom_intent, unpicked_summary, rivals_summary, my_needs):
    """Feature 2: Psychological Nomination Trap Generator."""
    prompt = f"""
SITUATION:
- Tactical Intent: {nom_intent}
- Your Lineup Needs: {my_needs}
- Rival Budgets & Roster Openings: {rivals_summary}
- Available Top Players: {unpicked_summary}

TASK:
Name the EXACT player to nominate right now and give 2 short reasons why:
- Why this forces maximum capital spend from specific rivals (e.g. Kopite, Chaitu, Harsha).
- Why this protects your targets or accelerates room deflation.
"""
    return query_llm_hybrid(prompt)

def ask_ai_strategist(user_query, live_draft_state):
    """Feature 3: Interactive Mid-Draft War Room Chat."""
    prompt = f"""
LIVE DRAFT CONTEXT:
{live_draft_state}

USER QUESTION:
{user_query}

TASK:
Provide a razor-sharp, quantitative tactical answer in 2-3 sentences. Reference specific manager budgets or player values when relevant.
"""
    return query_llm_hybrid(prompt)