import os
import requests
import json
import re
import streamlit as st

OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/generate")
LOCAL_MODEL = os.getenv("LOCAL_LLM_MODEL", "llama3.1:8b")

VERIFIED_GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "openai/gpt-oss-20b",
    "qwen/qwen3.6-27b"
]

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

def parse_clean_output(text: str) -> str:
    """Strips thinking tags, reasoning preambles, and raw HTML tags cleanly."""
    if not text:
        return "⚠️ No response generated. Please click again."
    
    # 1. Strip complete <think>...</think> tags
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    
    # 2. If <think> was unclosed (due to token limits), extract the real bullet points
    if "<think>" in text:
        parts = re.split(r'</think>', text)
        if len(parts) > 1:
            text = parts[-1]
        else:
            m = re.search(r'(\n\s*[\*\-•]\s+\*{0,2}(?:Verdict|Tactical|Rival|Action|Cutoff|Target)[\s\S]*)', text, flags=re.IGNORECASE)
            if m:
                text = m.group(1)
            else:
                text = re.sub(r'<think>.*', '', text, flags=re.DOTALL)

    # 3. Strip any leftover thinking preambles
    text = re.sub(r'(?i)here\'?s\s+a\s+thinking\s+process:.*?(?=\n\s*[\*\-•\d]|\Z)', '', text, flags=re.DOTALL)
    
    # 4. Strip stray XML/HTML tags
    text = re.sub(r'</?[a-zA-Z0-9_\-]+>', '', text)
    
    # 5. Clean up excessive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()

def query_groq_api(prompt: str, system_prompt: str = "You are an elite quantitative fantasy football auction draft strategist. Output ONLY 2-3 direct markdown bullet points. Do NOT output internal reasoning, outlines, or preambles.") -> str:
    """Ultra-fast cloud inference via Groq verified production models."""
    api_key = get_active_groq_key()
    if not api_key:
        return "⚠️ Missing GROQ_API_KEY. Add `GROQ_API_KEY` to Streamlit Secrets or `.streamlit/secrets.toml`."
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    last_err = ""
    for model_name in VERIFIED_GROQ_MODELS:
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 1024
        }
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=8)
            if res.status_code == 200:
                data = res.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                cleaned = parse_clean_output(content)
                if cleaned:
                    return cleaned
            else:
                last_err = f"HTTP {res.status_code}: {res.text}"
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
        "options": {"temperature": 0.2, "num_predict": 400}
    }
    try:
        res = requests.post(OLLAMA_API_URL, json=payload, timeout=2)
        if res.status_code == 200:
            resp = res.json().get("response", "").strip()
            return parse_clean_output(resp)
    except Exception:
        pass
    return ""

def query_llm_hybrid(prompt: str, system_prompt: str = "You are an elite fantasy football auction strategist. Return exactly 2-3 direct markdown bullet points with specific dollar numbers.") -> str:
    """Routes to local Ollama if online; otherwise routes directly to Groq Cloud."""
    local_resp = query_local_ollama(prompt, system_prompt)
    if local_resp:
        return f"**[Local Ollama]**\n\n{local_resp}"
    
    groq_resp = query_groq_api(prompt, system_prompt)
    return f"**[Groq Cloud]**\n\n{groq_resp}"

# ==============================================================================
# 3 LIVE AI WAR ROOM ENGINES
# ==============================================================================

def generate_tactical_advice(player_name, pos, fair_val, mkt_val, max_bid_to, inflation_index, news_note, my_budget, rivals_summary):
    prompt = f"""
SITUATION:
- Player: {player_name} ({pos})
- Model Fair Value: ${fair_val} | Market ADP: ${mkt_val} | Target Ceiling: ${max_bid_to}
- Draft Room Inflation: {inflation_index}x (>1.0x overpaying room, <1.0x bargains)
- Medical / News Intel: {news_note if news_note else 'Healthy & Active'}
- My Budget Remaining: ${my_budget}
- Active Rivals in Room: {rivals_summary}

TASK:
Provide exactly 3 direct bullet points:
* **Verdict & Price Ceiling**: State whether to Anchor, Price-Enforce Trap, or Fade, with the exact hard dollar drop-out limit.
* **Tactical Execution**: Why and how to manage the bidding velocity on this asset.
* **Rival Exploit**: Name a specific manager from the active room to bait or avoid fighting.

Do NOT output an analysis outline or thinking process. Start immediately with the first bullet point.
"""
    return query_llm_hybrid(prompt)

def generate_ai_nomination(nom_intent, unpicked_summary, rivals_summary, my_needs):
    prompt = f"""
SITUATION:
- Tactical Intent: {nom_intent}
- My Lineup Needs: {my_needs}
- Rival Budgets & Needs: {rivals_summary}
- Top Available Players: {unpicked_summary}

TASK:
Provide exactly 2 direct bullet points:
* **Target Nomination**: Name ONE exact player to put on the auction block right now.
* **Psychological Trap**: Explain how this drains specific rivals (e.g. Kopite, Chaitu, Harsha) or protects your targets.

Do NOT output an outline or thinking process. Start immediately with the first bullet point.
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