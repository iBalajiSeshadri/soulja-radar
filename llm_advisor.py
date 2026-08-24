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
    """
    Bulletproof parser that strips XML thinking tags, reasoning scratchpads,
    mental refinement notes, and returns strictly the final clean markdown bullet points.
    """
    if not text:
        return "⚠️ No response generated. Please click again."
    
    # 1. Strip explicit <think>...</think> tags
    text = re.sub(r'<think>[\s\S]*?</think>', '', text, flags=re.DOTALL)
    
    # 2. Extract final clean bullet block if scratchpad is present
    final_bullets = re.findall(
        r'(?:^|\n)\s*[\*\-•]\s+\*{0,2}(?:Verdict|Momentum|Target|Reach|Run Risk|Roster|Stealth|Psychological|Exploit|Action|Value|Risk|Floor|Ceiling)[\s\S]*?'
        r'(?=(?:\n\s*[\*\-•]\s+\*{0,2}(?:Verdict|Momentum|Target|Reach|Run Risk|Roster|Stealth|Psychological|Exploit|Action|Value|Risk|Floor|Ceiling)|\Z))', 
        text, 
        flags=re.IGNORECASE
    )
    if len(final_bullets) >= 2:
        return "\n\n".join([b.strip() for b in final_bullets[-3:]]).strip()
        
    # 3. If standard bullet extractor fails, find any markdown bullets at the end
    all_bullets = re.findall(r'(?:^|\n)\s*[\*\-•]\s+[\s\S]*?(?=(?:\n\s*[\*\-•]|\Z))', text)
    valid_bullets = [
        b.strip() for b in all_bullets 
        if not any(k in b.lower() for k in [
            'deconstruct', 'formulate', 'mental refinement', 'check constraints', 
            'bullet 1:', 'bullet 2:', 'bullet 3:', 'self-correction', "let's verify"
        ])
    ]
    if len(valid_bullets) >= 2:
        return "\n\n".join(valid_bullets[-3:]).strip()

    # 4. Fallback noise cleanup
    noise_patterns = [
        r'(?i)groq cloud\]',
        r'(?i)constraints:[\s\S]*?(?=\n\s*[\*\-•]|\Z)',
        r'(?i)deconstruct requirements:[\s\S]*?(?=\n\s*[\*\-•]|\Z)',
        r'(?i)formulate content[\s\S]*?:[\s\S]*?(?=\n\s*[\*\-•]|\Z)',
        r'(?i)check constraints:[\s\S]*?(?=\n\s*[\*\-•]|\Z)',
        r'(?i)self-correction[\s\S]*?:[\s\S]*?(?=\n\s*[\*\-•]|\Z)',
        r'(?i)let\'?s verify[\s\S]*?(?=\n\s*[\*\-•]|\Z)',
        r'(?i)all constraints met[\s\S]*?(?=\n\s*[\*\-•]|\Z)'
    ]
    for p in noise_patterns:
        text = re.sub(p, '', text, flags=re.DOTALL)
        
    text = re.sub(r'</?[a-zA-Z0-9_\-]+>', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def query_groq_api(prompt: str, system_prompt: str = "You are an elite quantitative fantasy football strategist. Output ONLY direct markdown bullet points. Do NOT output internal reasoning.") -> str:
    """Inference via Groq verified production models."""
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
            "temperature": 0.1,
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
        "options": {"temperature": 0.1, "num_predict": 400}
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
        return local_resp
    
    groq_resp = query_groq_api(prompt, system_prompt)
    return groq_resp

# ==============================================================================
# LIVE AI WAR ROOM ENGINES (AUCTION + SNAKE + GROUNDED STRATEGIST)
# ==============================================================================

def generate_live_auction_advice(player_name, pos, fair_val, mkt_val, max_bid_to, inflation_index, news_note, my_budget, my_roster_summary, live_rivals_telemetry, recent_picks_ledger):
    prompt = f"""
LIVE AUCTION SITUATION:
- Nominated Player: {player_name} ({pos})
- Fair Value: ${fair_val} | Market ADP: ${mkt_val} | Hard Bid Limit: ${max_bid_to}
- Active Room Inflation: {inflation_index}x
- Medical / Intel: {news_note if news_note else 'Healthy & Active'}
- My Budget Left: ${my_budget}
- My Current Roster: {my_roster_summary}

LIVE ROOM TELEMETRY:
- Recent Picks Momentum: {recent_picks_ledger if recent_picks_ledger else 'Draft just started'}
- Active Rival Needs & Cap: {live_rivals_telemetry}

TASK:
Provide exactly 3 direct markdown bullet points (NO preambles, NO thinking process, start immediately with first bullet):
* **Verdict & Price Cutoff**: State Anchor Stud, Price-Enforce Trap, or Fade, with the exact hard dollar limit (${max_bid_to}).
* **Momentum & Roster Fit**: How this bid aligns with your current open roster gaps and recent draft velocity.
* **Target Rival Exploit**: Name a specific active manager with high cap and need at {pos} to push into overpaying.
"""
    return query_llm_hybrid(prompt)

def generate_snake_turn_advice(player_name, pos, adp_rank, vorp_val, tier_name, curr_pick, next_my_pick, my_roster_summary, teams_between_needs, news_note):
    distance = max(0, next_my_pick - curr_pick)
    prompt = f"""
LIVE SNAKE DRAFT SITUATION:
- Targeted Player: {player_name} ({pos}) | Tier: {tier_name}
- Consensus ADP: #{adp_rank} | True VORP: +{vorp_val} pts
- Current Overall Pick: #{curr_pick}
- Distance to Your Next Turn: {distance} picks away (Your next pick: #{next_my_pick})
- Medical / Intel: {news_note if news_note else 'Healthy & Active'}
- Your Current Roster: {my_roster_summary}

OPPONENTS ON THE CLOCK BEFORE YOUR NEXT PICK:
- Teams Picking In-Between & Their Roster Gaps: {teams_between_needs}

TASK:
Provide exactly 3 direct markdown bullet points (NO preambles, NO thinking process, start immediately with first bullet):
* **Reach vs. Wait Verdict**: State TAKE NOW or RISK WAITING, with survival odds to pick #{next_my_pick}.
* **Run Risk Assessment**: Which manager picking before your next turn is desperate for {pos} and will snipe him.
* **Roster Construction Impact**: How locking in this player solidifies your build archetype vs available alternatives.
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
Provide exactly 2 direct markdown bullet points (NO preambles, start immediately with first bullet):
* **Target Nomination**: Name ONE exact player to nominate right now.
* **Psychological Trap**: Explain how this drains specific rivals or establishes your positional advantage.
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

STRICT INSTRUCTIONS:
- Refer strictly to the grounded player values, VORPs, and ADPs provided above.
- Never hallucinate fake auction prices.
- Provide a razor-sharp, decisive recommendation in 2-3 direct markdown bullet points comparing their exact values and roster impact. Do NOT output internal reasoning or scratchpads.
"""
    return query_llm_hybrid(prompt)