import os
import requests
import json
import streamlit as st

OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/generate")
LOCAL_MODEL = os.getenv("LOCAL_LLM_MODEL", "llama3.1:8b")

PREFERRED_GROQ_MODELS = [
    "openai/gpt-oss-20b",
    "qwen/qwen3.6-27b",
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-120b",
    "gemma2-9b-it"
]

def get_active_groq_key() -> str:
    """Safely retrieves the Groq API key from Streamlit secrets or environment."""
    try:
        if hasattr(st, "secrets") and "GROQ_API_KEY" in st.secrets:
            return str(st.secrets["GROQ_API_KEY"]).strip().strip('"').strip("'")
    except Exception:
        pass
    return os.getenv("GROQ_API_KEY", "").strip()

def resolve_groq_model(api_key: str) -> str:
    """Queries Groq's active model catalog to select the best available chat model."""
    try:
        res = requests.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=3
        )
        if res.status_code == 200:
            active_ids = [m["id"] for m in res.json().get("data", [])]
            for candidate in PREFERRED_GROQ_MODELS:
                if candidate in active_ids:
                    return candidate
            chat_models = [m for m in active_ids if "whisper" not in m and "guard" not in m]
            if chat_models:
                return chat_models[0]
    except Exception:
        pass
    return PREFERRED_GROQ_MODELS[0]

def query_groq_api(prompt: str, system_prompt: str = "You are an elite quantitative fantasy football auction strategist. Provide direct, tactical bullet points. No introductory filler.") -> str:
    """Ultra-fast cloud inference via Groq API."""
    api_key = get_active_groq_key()
    if not api_key:
        return "⚠️ Missing Groq API Key. Add `GROQ_API_KEY` to Streamlit Secrets or `.streamlit/secrets.toml`."
    
    selected_model = resolve_groq_model(api_key)
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": selected_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 250
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=6)
        if res.status_code == 200:
            return res.json()["choices"][0]["message"]["content"].strip()
        
        # Fallback to secondary candidates if selected model returned an error
        for alt_model in PREFERRED_GROQ_MODELS:
            if alt_model != selected_model:
                payload["model"] = alt_model
                res_alt = requests.post(url, headers=headers, json=payload, timeout=4)
                if res_alt.status_code == 200:
                    return res_alt.json()["choices"][0]["message"]["content"].strip()
                    
        return f"⚠️ Groq API Error ({res.status_code}): {res.text}"
    except Exception as e:
        return f"⚠️ Groq Connection Error: {e}"

def query_local_ollama(prompt: str, system_prompt: str = "") -> str:
    """Queries local Ollama endpoint if online."""
    full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
    payload = {
        "model": LOCAL_MODEL,
        "prompt": full_prompt,
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": 200}
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
# 3 LIVE AI WAR ROOM ENGINES
# ==============================================================================

def generate_tactical_advice(player_name, pos, fair_val, mkt_val, max_bid_to, inflation_index, news_note, my_budget, rivals_summary):
    prompt = f"""
SITUATION:
- Player: {player_name} ({pos})
- Model True Value: ${fair_val} | Market ADP: ${mkt_val} | Target Ceiling: ${max_bid_to}
- Draft Inflation: {inflation_index}x (>1.0x overpaying, <1.0x bargains)
- Medical / Intel: {news_note if news_note else 'Healthy & Active'}
- My Remaining Budget: ${my_budget}
- Active Rivals Context: {rivals_summary}

TASK:
Give 2-3 direct bullet points on:
1. Exact bid/fade verdict (Anchor stud vs. Price-enforce trap vs. Fade).
2. The exact hard dollar cutoff where I must drop out.
3. Specific rival to exploit or avoid bidding against on this player.
No introductory text.
"""
    return query_llm_hybrid(prompt)

def generate_ai_nomination(nom_intent, unpicked_summary, rivals_summary, my_needs):
    prompt = f"""
SITUATION:
- Tactical Intent: {nom_intent}
- My Needs: {my_needs}
- Rival Budgets: {rivals_summary}
- Available Players: {unpicked_summary}

TASK:
Name ONE specific player to nominate right now and give 2 short bullet points explaining why this forces rival spending (e.g. Kopite, Chaitu, Harsha) or protects my targets.
"""
    return query_llm_hybrid(prompt)

def ask_ai_strategist(user_query, live_draft_state):
    prompt = f"""
LIVE DRAFT CONTEXT:
{live_draft_state}

USER QUESTION:
{user_query}

TASK:
Provide a razor-sharp, quantitative tactical answer in 2-3 sentences. Reference specific manager budgets or values when relevant.
"""
    return query_llm_hybrid(prompt)