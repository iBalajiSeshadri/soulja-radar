import os
import requests
import json
import streamlit as st

OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/generate")
LOCAL_MODEL = os.getenv("LOCAL_LLM_MODEL", "llama3.1:8b")

# Tested Groq chat models in priority order
PRIMARY_GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "llama3-70b-8192",
    "llama3-8b-8192"
]

def get_active_groq_key() -> str:
    """Safely retrieves the Groq API key from Streamlit secrets or environment."""
    try:
        if hasattr(st, "secrets") and "GROQ_API_KEY" in st.secrets:
            return str(st.secrets["GROQ_API_KEY"]).strip().strip('"').strip("'")
    except Exception:
        pass
    return os.getenv("GROQ_API_KEY", "").strip()

def query_groq_api(prompt: str, system_prompt: str = "You are an elite, quantitative fantasy football auction draft analyst. Provide direct, tactical bullet points. No conversational fluff.") -> str:
    """Ultra-fast cloud inference via Groq API."""
    api_key = get_active_groq_key()
    if not api_key:
        return "⚠️ Missing Groq API Key. Add `GROQ_API_KEY` to Streamlit Secrets or `.streamlit/secrets.toml`."
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    for model_name in PRIMARY_GROQ_MODELS:
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 250
        }
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=5)
            if res.status_code == 200:
                data = res.json()
                content = data["choices"][0]["message"]["content"].strip()
                if content:
                    return content
            elif res.status_code == 401:
                return "⚠️ Invalid Groq API Key. Please verify your key in Streamlit Secrets."
        except Exception:
            continue
            
    return "⚠️ Groq Service Busy: Try clicking again in 2 seconds."

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