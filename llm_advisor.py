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
    
    # Strip <think>...</think> tags
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    
    if "<think>" in text:
        parts = re.split(r'</think>', text)
        if len(parts) > 1:
            text = parts[-1]
        else:
            m = re.search(r'(\n\s*[\*\-•]\s+\*{0,2}(?:Verdict|Tactical|Rival|Action|Cutoff|Target|Reach|Survival)[\s\S]*)', text, flags=re.IGNORECASE)
            if m:
                text = m.group(1)
            else:
                text = re.sub(r'<think>.*', '', text, flags=re.DOTALL)

    # Strip thinking preambles
    text = re.sub(r'(?i)here\'?s\s+a\s+thinking\s+process:.*?(?=\n\s*[\*\-•\d]|\Z)', '', text, flags=re.DOTALL)
    text = re.sub(r'</?[a-zA-Z0-9_\-]+>', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()

def query_groq_api(prompt: str, system_prompt: str = "You are an elite quantitative fantasy football strategist. Output ONLY direct markdown bullet points. Do NOT output internal reasoning.") -> str:
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
            "temperature": 0.15,
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
        "options": {"temperature": 0.15, "num_predict": 400}
    }
    try:
        res = requests.post(OLLAMA_API_URL, json=payload, timeout=2)
        if res.status_code == 200:
            resp = res.json().get("response", "").strip()
            return parse_clean_output(resp)
    except Exception:
        pass
    return ""

def query_llm_hybrid(prompt: str, system_prompt: str = "You are an elite fantasy football draft strategist. Return exactly direct markdown bullet points.") -> str:
    """Routes to local Ollama if online; otherwise routes directly to Groq Cloud."""
    local_resp = query_local_ollama(prompt, system_prompt)
    if local_resp:
        return f"**[Local Ollama]**\n\n{local_resp}"
    
    groq_resp = query_groq_api(prompt, system_prompt)
    return f"**[Groq Cloud]**\n\n{groq_resp}"

# ==============================================================================
# LIVE AI WAR ROOM ENGINES (AUCTION + SNAKE + GROUNDED STRATEGIST)
# ==============================================================================

def generate_live_auction_advice(player_name, pos, fair_val, mkt_val, max_bid_to, inflation_index, news_note, my_budget, my_roster_summary, live_rivals_telemetry, recent_picks_ledger):
    prompt = f"""
LIVE AUCTION SITUATION:
- Nominated Player: {player_name} ({pos})
- Fair Value: ${fair_val} | Market ADP: ${mkt_val} | Hard Bid Limit: ${max_bid_to}
- Active Room Inflation: {inflation_index}x (>1.0x overpaying, <1.0x bargains)
- Medical / Intel: {news_note if news_note else 'Healthy & Active'}
- My Budget Left: ${my_budget}
- My Current Roster: {my_roster_summary}

LIVE ROOM TELEMETRY:
- Recent Picks Momentum: {recent_picks_ledger if recent_picks_ledger else 'Draft just started'}
- Active Rival Needs & Cap: {live_rivals_telemetry}

TASK:
Provide exactly 3 direct, tactical markdown bullet points:
* **Verdict & Price Cutoff**: State whether to Anchor Stud, Price-Enforce Trap, or Fade, with the exact hard dollar drop-out limit (${max_bid_to}).
* **Momentum & Roster Fit**: How this bid aligns with your current open roster gaps and recent draft velocity.
* **Target Rival Exploit**: Name a specific active manager with high cap and need at {pos} to push into overpaying.

Do NOT output preambles or analysis outlines. Start immediately with the first bullet point.
"""
    return query_llm_hybrid(prompt)

def generate_snake_turn_advice(player_name, pos, adp_rank, vorp_val, tier_name, curr_pick, next_my_pick, my_roster_summary, teams_between_needs, news_note):
    distance = max(0, next_my_pick - curr_pick)
    prompt = f"""
LIVE SNAKE DRAFT SITUATION:
- Targeted Player: {player_name} ({pos}) | Tier: {tier_name}
- Consensus ADP: #{adp_rank} | VORP Rating: +{vorp_val} pts
- Current Overall Pick: #{curr_pick}
- Distance to Your Next Turn: {distance} picks away (Your next pick: #{next_my_pick})
- Medical / Intel: {news_note if news_note else 'Healthy & Active'}
- Your Current Roster: {my_roster_summary}

OPPONENTS ON THE CLOCK BEFORE YOUR NEXT PICK:
- Teams Picking In-Between & Their Roster Gaps: {teams_between_needs}

TASK:
Provide exactly 3 direct, actionable markdown bullet points:
* **Reach vs. Wait Verdict**: State whether to TAKE NOW or RISK WAITING, with specific odds he survives back to pick #{next_my_pick}.
* **Run Risk Assessment**: Which managers picking between you are desperate for a {pos} and will snipe him if passed.
* **Roster Construction Impact**: How locking in this player solidifies your build archetype vs available alternatives.

Do NOT output preambles or analysis outlines. Start immediately with the first bullet point.
"""
    return query_llm_hybrid(prompt)

def generate_ai_nomination(nom_intent, unpicked_summary, rivals_summary, my_needs):
    prompt = f"""
SITUATION:
- Tactical Intent: {nom_intent}
- My Needs: {my_needs}
- Rival Budgets & Open Spots: {rivals_summary}
- Top Available Players: {unpicked_summary}

TASK:
Provide exactly 2 direct bullet points:
* **Target Nomination**: Name ONE exact player to put on the block right now.
* **Psychological Trap**: Explain how this drains specific rivals (e.g. Kopite, Chaitu, Harsha) or establishes your position advantage.

Do NOT output an outline or thinking process. Start immediately with the first bullet point.
"""
    return query_llm_hybrid(prompt)

def ask_ai_strategist(user_query, live_draft_state, player_telemetry_grounding=""):
    prompt = f"""
LIVE DRAFT CONTEXT:
{live_draft_state}

GROUNDED PLAYER DATABASE TELEMETRY:
{player_telemetry_grounding if player_telemetry_grounding else 'No specific player cards requested in query.'}

USER QUESTION:
{user_query}

STRICT QUANTITATIVE INSTRUCTIONS:
- You MUST use the exact dollar values, VORP numbers, and consensus ADPs provided in the GROUNDED PLAYER TELEMETRY above.
- NEVER invent or hallucinate fake auction prices (e.g. do not say studs are $10-$15).
- If draft format is Auction, refer strictly to dollar values ($). If Snake, refer strictly to round/pick numbers (#).
- Give a razor-sharp, decisive recommendation in 2-3 direct markdown bullet points comparing their exact True VORP values and roster construction impact.
"""
    return query_llm_hybrid(prompt)