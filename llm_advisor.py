import os
import requests
import json
import streamlit as st

OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/generate")
LOCAL_MODEL = os.getenv("LOCAL_LLM_MODEL", "llama3.1:8b")

def get_active_groq_key() -> str:
    """Safely retrieves the Groq API key from Streamlit secrets or environment."""
    key = ""
    try:
        if hasattr(st, "secrets") and "GROQ_API_KEY" in st.secrets:
            key = str(st.secrets["GROQ_API_KEY"])
    except Exception:
        pass
    if not key:
        key = os.getenv("GROQ_API_KEY", "")
    return key.strip().strip('"').strip("'")

def query_groq_api(prompt: str, system_prompt: str = "You are an elite quantitative fantasy football auction draft strategist. Give 2-3 direct tactical bullet points with exact dollar limits. No conversational filler.") -> str:
    """Fast cloud inference via Groq API."""
    api_key = get_active_groq_key()
    if not api_key:
        return "⚠️ Missing GROQ_API_KEY. Please verify it is added in Streamlit Secrets or `.streamlit/secrets.toml`."
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Priority models on Groq
    target_models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
    
    last_err = ""
    for model in target_models:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 250
        }
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=8)
            if res.status_code == 200:
                data = res.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                if content.strip():
                    return content.strip()
            else:
                last_err = f"HTTP {res.status_code}: {res.text}"
                if res.status_code != 404:
                    return f"⚠️ Groq API Error ({res.status_code}): {res.text}"
        except Exception as e:
            last_err = str(e)
            
    return f"⚠️ Groq Connection Issue: {last_err}"

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
- Medical / Beat News: {news_note if news_note else 'Healthy & Active'}
- My Budget Left: ${my_budget}
- Key Rivals Context: {rivals_summary}

TASK:
Give 2-3 direct bullet points on:
1. Exact bid/fade verdict (Anchor stud vs. Price-enforce trap vs. Fade).
2. The exact hard dollar cutoff where I must drop out.
3. Specific rival to exploit or avoid bidding against on this player.
No conversational intro.
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