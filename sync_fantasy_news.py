import os
import requests
import json
import re
import xml.etree.ElementTree as ET
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

# ==============================================================================
# 0. CONFIGURATION & URL SANITIZER
# ==============================================================================

def clean_url(url: str) -> str:
    """Strips markdown link syntax and whitespace."""
    if not url:
        return ""
    match = re.search(r'https?://[^\s\)\]\'"]+', str(url))
    return match.group(0) if match else str(url).strip()

def get_active_groq_key() -> str:
    """Retrieves Groq API Key from (in order): Streamlit secrets, .streamlit/secrets.toml, env var.
    On Streamlit Cloud there is no secrets.toml file — the key lives in st.secrets and
    (when this runs as a subprocess) in the GROQ_API_KEY env var passed by the parent app."""
    # 1. Streamlit secrets (works when imported inside the running app)
    try:
        import streamlit as st  # noqa
        if hasattr(st, "secrets") and "GROQ_API_KEY" in st.secrets:
            k = str(st.secrets["GROQ_API_KEY"]).strip().strip('"').strip("'")
            if k:
                return k
    except Exception:
        pass
    # 2. Local secrets.toml (local dev)
    if os.path.exists(".streamlit/secrets.toml"):
        try:
            with open(".streamlit/secrets.toml", "r") as f:
                for line in f:
                    if "GROQ_API_KEY" in line and "=" in line:
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
    # 3. Environment variable (subprocess path)
    return os.getenv("GROQ_API_KEY", "").strip().strip('"').strip("'")

def get_available_groq_models(api_key: str):
    """Queries Groq /v1/models to select valid active chat models."""
    try:
        res = requests.get(
            clean_url("https://api.groq.com/openai/v1/models"),
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=4
        )
        if res.status_code == 200:
            active_ids = [m["id"] for m in res.json().get("data", [])]
            valid = [
                m for m in active_ids 
                if not any(k in m.lower() for k in ["whisper", "guard", "audio", "safeguard", "embed", "vision", "orpheus"])
            ]
            # Best available free reasoning models first. gpt-oss-120b is the
            # strongest general model available on standard Groq keys for nuanced
            # beat-report synthesis (the "caught 10/12, beat the DB" reads);
            # gpt-oss-20b is the faster fallback.
            preferred = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.6-27b", "llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
            ordered = [p for p in preferred if p in valid] + [v for v in valid if v not in preferred]
            if ordered:
                return ordered
    except Exception:
        pass
    # Fallback list only contains models commonly available on Groq keys.
    return ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.6-27b"]

def clean_name(name):
    """Normalizes player name and resolves common alias spellings."""
    if not isinstance(name, str):
        return ""
    name = name.lower().strip()
    name = re.sub(r"[^\w\s]", "", name)
    name = re.sub(r"\b(jr|sr|iii|ii|iv|v)\b", "", name)
    name = " ".join(name.split())
    
    # Common phonetic and media aliases
    aliases = {
        "jeremiah love": "jeremiyah love",
        "cam akers": "camerun akers",
        "gabe davis": "gabriel davis",
        "mitch trubisky": "mitchell trubisky",
        "chig okazie": "chigoziem okonkwo",
        "chig okonkwo": "chigoziem okonkwo",
        "hollywood brown": "marquise brown"
    }
    return aliases.get(name, name)

def clean_snippet_text(text, max_len=180):
    text = " ".join(text.split())
    text = re.sub(r"^(Rotowire|CBS Sports|Fantasy Staff|RotoBaller|FFToday|32BeatWriters|FantasySP|Twitter)\s*[:\-]\s*", "", text, flags=re.IGNORECASE)
    if len(text) > max_len:
        return text[:max_len].rsplit(' ', 1)[0] + "..."
    return text

def extract_players_fast(text, registry, primary_only=False):
    """Fast proper-noun extractor matching 2-word names against the registry.

    Beat blurbs lead with their SUBJECT ("Puka Nacua left practice ..."), so when
    primary_only=True we return just the player named in the first ~140 chars —
    this prevents attaching an article to a star it merely *mentions* later
    (the wrong-player bug where a Bijan contract note landed on Gibbs/CMC)."""
    found = []
    if not text or len(text) < 10:
        return found
    scan = text if not primary_only else text[:110]
    if primary_only:
        # Strip leading boilerplate so the real subject is at the front.
        scan = re.sub(r'^(fantasy impact|news|update|report|injury)\s*[:\-]\s*', '', scan, flags=re.IGNORECASE)
    for m in re.finditer(r'\b[A-Z][a-zA-Z\.\'-]+\s+[A-Z][a-zA-Z\.\'-]+\b', scan):
        c_cand = clean_name(m.group(0))
        if c_cand in registry:
            found.append(registry[c_cand])
            if primary_only:
                break  # first (subject) player only
    # de-dupe preserving order
    seen, out = set(), []
    for f in found:
        if f not in seen:
            seen.add(f); out.append(f)
    return out

# ==============================================================================
# 1. PARALLEL GROQ LLM BEAT SENTIMENT WORKER
# ==============================================================================

def parse_llm_batch_response(raw_text: str, batch_map: dict):
    """Token-aware fuzzy name matcher with thinking suppression."""
    clean_text = re.sub(r'<think>[\s\S]*?</think>', '', raw_text, flags=re.DOTALL)
    clean_text = re.sub(r'```(?:json)?', '', clean_text).strip()
    
    results = {}
    match = re.search(r'\[[\s\S]*\]', clean_text)
    if match:
        try:
            items = json.loads(match.group(0))
            for it in items:
                p_name = it.get("name") or it.get("player_name") or it.get("player")
                if not p_name: 
                    continue
                
                c_p = clean_name(p_name)
                matched_orig = None
                
                for b_name in batch_map:
                    if clean_name(b_name) == c_p:
                        matched_orig = b_name
                        break
                
                if not matched_orig:
                    p_tokens = set(c_p.split())
                    for b_name in batch_map:
                        b_tokens = set(clean_name(b_name).split())
                        if len(p_tokens & b_tokens) >= 2 or (len(p_tokens) == 1 and p_tokens.issubset(b_tokens)):
                            matched_orig = b_name
                            break

                if matched_orig:
                    tag = str(it.get("tag") or "BEAT").upper().strip()
                    if tag in ["NOISE", "ROUTINE", "NONE"]:
                        continue

                    mult = float(it.get("mult") or it.get("multiplier") or 1.0)
                    mult = max(0.75, min(1.15, mult))
                    note = str(it.get("note") or it.get("crunchy_note") or "").strip()

                    meta_src = batch_map[matched_orig]
                    src_label = meta_src.get('source_name', 'BEAT WIRE')
                    raw_lc = str(meta_src.get('raw_text', '')).lower()

                    # HARD ANTI-FABRICATION GUARD (enforced in code, not just the prompt):
                    # If the source was ONLY an injury/roster status line (no real
                    # performance text), the model is NOT allowed to conjure camp
                    # performance ("separation", "flashes", "beat the CB", "standout").
                    injury_only = ("INJURY WIRE" in src_label.upper() or raw_lc.startswith("official injury wire")) \
                        and not any(k in raw_lc for k in ["caught", "target", "route", "beat ", "reps", "1st-team",
                                                          "first-team", "practice report", "standout", "explosive",
                                                          "quote", "said", "coach", "yards", "touchdown", "snaps"])
                    if injury_only:
                        FABRICATION = ["separation", "flash", "beat the", "standout", "explosive", "burst",
                                       "red zone drills", "consistent catches", "deep threat", "impressive",
                                       "agility", "reps with the", "shining", "dominat"]
                        if any(f in note.lower() for f in FABRICATION):
                            note = ""  # drop the invented camp read; fall back to the factual snippet below
                        # a bare injury line can never be an upgrade
                        if tag in ("TIER_JUMPER", "SUPERFLEX_EDGE", "WAIVER_SURGE"):
                            tag = "QUESTIONABLE" if "questionable" in raw_lc else "INJURY_ALERT"
                        if mult > 1.0:
                            mult = 0.90 if "questionable" in raw_lc else 0.82

                    # Quality gate: reject generic, detail-free notes so the intel
                    # column never shows fluff like "positive camp buzz".
                    GENERIC_JUNK = [
                        "positive camp buzz", "trending up", "looking good", "injury report",
                        "camp standout", "one to watch", "buzz", "report", "update", "n/a", "none"
                    ]
                    note_l = note.lower()
                    is_generic = (len(note) < 25) or (note_l in GENERIC_JUNK) or all(
                        w in ("positive", "camp", "buzz", "trending", "up", "looking", "good", "report")
                        for w in re.findall(r"[a-z]+", note_l)
                    ) if note else True
                    if is_generic:
                        # Fall back to the richest raw snippet rather than a vague label.
                        note = meta_src.get('snippet', '') or note

                    results[matched_orig] = {
                        "multiplier": round(mult, 2),
                        "type": tag,
                        "note": note if note else meta_src['snippet'],
                        "source_url": meta_src.get('source_url', '')
                    }
        except Exception:
            pass
    return results

def process_single_groq_batch(batch_items, api_key, candidate_models):
    """Worker function for concurrent thread pool execution with strict signal extraction."""
    if not batch_items or not api_key:
        return {}

    batch_map = {item["player_name"]: item for item in batch_items}
    prompt_payload = [
        {
            "name": item["player_name"],
            "source": item.get("source_name", "Beat Wire"),
            # Keep more of the raw report so the model has the concrete details
            # (catch totals, coverage wins, snap counts, coach quotes) to crunch.
            "report": item["raw_text"][:600]
        }
        for item in batch_items
    ]

    system_prompt = f"""You are an elite NFL fantasy football beat reporter and film analyst.
You are given {len(prompt_payload)} REAL beat reports, camp notes, injury wires, and Superflex takeaways.
Your job is to CRUNCH each raw report into ONE genuine, specific scouting insight a sharp manager can act on.

TAG CRITERIA (pick the single best-fit tag):
- TIER_JUMPER: Concrete camp dominance / winning a starting job / manufactured-touch design / breakout usage. (mult 1.06-1.15)
  ** HIGHEST-CONFIDENCE TIER_JUMPER = VACATED ROLE: this player inherits a DEPARTED teammate's
     targets/touches/role (the teammate was traded, left in free agency, is injured/out, or retired).
     Examples of the pattern: "With [Teammate] gone/traded/injured, [Player] inherits the vacated
     touches/targets/lead role." When you see this, tag TIER_JUMPER, use mult 1.10-1.15, and the note
     MUST name the departed teammate and the specific vacated volume (e.g. "Inherits the ~250 touches
     vacated by [Teammate]'s trade — now the clear lead back"). This is the single most valuable signal. **
- SUPERFLEX_EDGE: 2QB/Superflex value surge, dual-threat rushing floor, late-round QB leverage. (mult 1.05-1.12)
- CLEARED: Full participant in 11-on-11 contact after an injury. (mult 1.00-1.03)
- WAIVER_SURGE: Surging pickup (+thousands of adds in 24h) signaling a role/opportunity spike. (mult 1.04-1.08)
- VET_MAINTENANCE: Precautionary veteran rest / minor soreness, no regular-season risk. (mult 0.96-0.99)
- ROLE_PINCH: Losing goal-line/3rd-down snaps, committee squeeze, target competition. (mult 0.84-0.94)
- QUESTIONABLE: Soft-tissue strain, limited practice, game-time-decision risk. (mult 0.86-0.92)
- INJURY_ALERT: Multi-week structural injury, surgery, PUP, or IR. (mult 0.75-0.85)
- NOISE: Generic fluff, routine quote, or no draft impact -> use tag "NOISE" and it will be dropped.

TAG-SELECTION LOGIC (critical — the tag must match the SENTIMENT of the note):
- If the report is POSITIVE for the player (dominating, earning targets/snaps, beating defenders,
  winning a job, explosive, promoted up the depth chart) -> it MUST be a positive tag
  (TIER_JUMPER / SUPERFLEX_EDGE / CLEARED / WAIVER_SURGE) with a multiplier >= 1.00.
  NEVER tag a clearly positive report as ROLE_PINCH or any downgrade.
- ROLE_PINCH is ONLY for the player LOSING work (their OWN snaps/touches shrinking). If the player
  is the one WINNING the job at a teammate's expense, that is a TIER_JUMPER for THIS player.
- Only use a downgrade tag (ROLE_PINCH / QUESTIONABLE / INJURY_ALERT / VET_MAINTENANCE) when the
  report is genuinely negative or health-related FOR THIS player.

CRUNCHY NOTE RULES (this is the most important part):
- The note MUST contain the CONCRETE, SPECIFIC detail from the report, not a generic label.
  GOOD: "Caught 10 of 12 targets in the joint practice and beat the starting CB on back-to-back reps down the seam."
  GOOD: "Working as the clear 1st-team RB, taking every goal-line rep; backup has been demoted to scout team."
  GOOD: "Looked explosive in pads — reporters clocked two 40+ yard TD runs and praised his burst through the hole."
  GOOD: "Hamstring strain, held out of team drills; considered week-to-week, handcuff RB seeing 1st-team work."
  BAD (never do this): "Positive camp buzz." / "Injury report." / "Trending up." / "Looking good in camp."
- If the raw report is vague or has NO concrete detail, tag it "NOISE" — do NOT invent details.
- If the report is ONLY an injury/roster STATUS line (e.g. "Questionable (Undisclosed) - Limited practice",
  "Placed on PUP", "IR") with NO performance description, you MUST NOT invent camp performance, separation,
  routes, or "flashes". Report ONLY the injury status factually and tag it INJURY_ALERT/QUESTIONABLE/CLEARED.
  NEVER tag a bare injury line as TIER_JUMPER.
- DO NOT tag as TIER_JUMPER (these are NOISE or their own tag, not tier-jumps):
  * a generic depth-chart/projection line with no performance detail (e.g. "Active starting DB
    projection on depth chart") — that is NOISE, not a jump.
  * a bare waiver/add-count line with no role reason (e.g. "+20,000 adds") — that is WAIVER_SURGE at most.
  * an injury-return/participation line ("participated in agility drills", "did side work") — that is
    CLEARED/QUESTIONABLE, never TIER_JUMPER.
  A TIER_JUMPER requires a CONCRETE performance/role/opportunity reason, ideally a vacated role.
- Never fabricate stats, defenders, or quotes that are not supported by the report text.
- One sentence, present tense, punchy, specific.

OUTPUT FORMAT: Return ONLY a valid JSON array, no prose:
[
  {{"name": "Player Name", "tag": "TIER_JUMPER", "mult": 1.10, "note": "One specific, detail-rich sentence pulled from the report."}}
]
"""

    url = clean_url("[https://api.groq.com/openai/v1/chat/completions](https://api.groq.com/openai/v1/chat/completions)")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    for model_name in candidate_models:
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Analyze these {len(prompt_payload)} beat reports:\n" + json.dumps(prompt_payload)}
            ],
            "temperature": 0.1,
            "max_tokens": 2400
        }
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=15)
            if res.status_code == 200:
                raw_content = res.json()["choices"][0]["message"]["content"]
                results = parse_llm_batch_response(raw_content, batch_map)
                if results:
                    return results
            elif res.status_code == 429:
                time.sleep(1.0)
        except Exception:
            continue

    # ── OLLAMA (local Llama) FALLBACK ─────────────────────────────────────────
    # If Groq is capped/unavailable/empty, fall back to a local Ollama model so the
    # pipeline stays up (no daily token cap, free). Quality is a notch below
    # gpt-oss-120b but solid for this structured crunch.
    ollama_res = process_batch_ollama(system_prompt, prompt_payload, batch_map)
    if ollama_res:
        return ollama_res

    return {}


def process_batch_ollama(system_prompt, prompt_payload, batch_map):
    """Local Ollama fallback for the beat-crunch when Groq is unavailable/capped."""
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    try:
        # quick reachability check
        tags = requests.get(f"{ollama_url}/api/tags", timeout=3)
        if tags.status_code != 200:
            return {}
    except Exception:
        return {}
    try:
        r = requests.post(
            f"{ollama_url}/api/chat",
            json={"model": ollama_model, "stream": False, "format": "json",
                  "options": {"temperature": 0.1, "num_ctx": 8192},
                  "messages": [
                      {"role": "system", "content": system_prompt},
                      {"role": "user", "content": f"Analyze these {len(prompt_payload)} beat reports:\n"
                                                   + json.dumps(prompt_payload)}]},
            timeout=180,
        )
        if r.status_code == 200:
            content = r.json().get("message", {}).get("content", "")
            return parse_llm_batch_response(content, batch_map)
    except Exception:
        pass
    return {}

# ==============================================================================
# 2. MAIN NEWS AGGREGATION PIPELINE
# ==============================================================================

print("==================================================================")
print("  SOULJA SOULJA MULTI-SOURCE BEAT, IDP & SUPERFLEX AGGREGATOR")
print("==================================================================")

# Start from a clean slate each run so stale/hallucinated notes from prior runs
# never persist. All sources are re-scraped fresh below.
camp_overrides = {}

scraped_intel_by_player = {}

# Source tiers: real beat/article text (with performance detail) should WIN over a
# bare injury-status line for the same player. Higher = richer, more crunchable.
_SOURCE_RANK = {
    "INJURY WIRE": 1, "WAIVER SURGE": 2, "FFTODAY IDP": 2,
    "CBS": 3, "FFTODAY NEWS": 3, "FFTODAY ARTICLE": 3, "FFTODAY RSS": 3,
    "YAHOO": 3, "FOOTBALLGUYS": 3, "PFF": 4, "NFL.COM": 4,
    "ROTOBALLER": 4, "FANTASYSP": 4, "CBS RSS": 4, "FANTASYPROS": 5,
    "ROTOWIRE": 5, "32BEAT": 5, "TWITTER": 5,
}

def _src_rank(name):
    up = str(name).upper()
    best = 0
    for key, val in _SOURCE_RANK.items():
        if key in up:
            best = max(best, val)
    return best or 3

def add_intel(c_p, entry):
    """Merge an intel entry, letting richer sources / longer real text override a
    bare injury-status line so the LLM gets actual camp performance to crunch."""
    existing = scraped_intel_by_player.get(c_p)
    if existing is None:
        scraped_intel_by_player[c_p] = entry
        return
    new_rank = _src_rank(entry.get("source_name", ""))
    old_rank = _src_rank(existing.get("source_name", ""))
    new_len = len(str(entry.get("raw_text", "")))
    old_len = len(str(existing.get("raw_text", "")))
    # Prefer higher source tier; tie-break on longer (more detailed) report text.
    if new_rank > old_rank or (new_rank == old_rank and new_len > old_len):
        scraped_intel_by_player[c_p] = entry

web_headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': '[https://www.google.com/](https://www.google.com/)'
}
reddit_headers = {'User-Agent': 'python:soulja-fantasy-aggregator:v2.2 (by /u/DjBallz)'}

# 1. Universal Player Registry from Sleeper API
print("\n1. Building universal NFL player registry from Sleeper API...")
player_registry = {}
p_db = {}
try:
    p_db = requests.get(clean_url("[https://api.sleeper.app/v1/players/nfl](https://api.sleeper.app/v1/players/nfl)"), timeout=12).json()
    for pid, pdata in p_db.items():
        fn = pdata.get('first_name', '')
        ln = pdata.get('last_name', '')
        full = f"{fn} {ln}".strip()
        c_full = clean_name(full)
        if len(c_full) > 4:
            player_registry[c_full] = full
    print(f"✓ Registry loaded ({len(player_registry)} active player names).")
except Exception as e:
    print(f"Registry notice: {e}")

# 2. Source A: Sleeper Official Injury Wire & Active Camp Reports
print("\n2. [SOURCE 1] Ingesting Sleeper Official Injury Wire & Queuing for LLM...")
sleeper_injuries_found = 0
if p_db:
    for pid, pdata in p_db.items():
        status = pdata.get('status')
        inj_status = pdata.get('injury_status')
        inj_body = pdata.get('injury_body_part') or ''
        inj_notes = pdata.get('injury_notes') or ''
        fn = pdata.get('first_name', '')
        ln = pdata.get('last_name', '')
        p_name = f"{fn} {ln}".strip()
        
        if not p_name or not pdata.get('team'):
            continue

        slug_name = clean_name(p_name).replace(" ", "-")
        rotowire_id = pdata.get('rotowire_id')
        wire_link = clean_url(f"[https://www.rotowire.com/football/player/](https://www.rotowire.com/football/player/){slug_name}-{rotowire_id}") if rotowire_id else clean_url(f"[https://www.rotoballer.com/nfl/player-news?player=](https://www.rotoballer.com/nfl/player-news?player=){slug_name}")
            
        if status in ['IR', 'PUP', 'Sus', 'Out'] or inj_status in ['IR', 'Out', 'PUP', 'Doubtful', 'Questionable'] or inj_notes:
            desc = f"{inj_status or status or 'Report'}"
            if inj_body: desc += f" ({inj_body})"
            if inj_notes: 
                clean_n = re.sub(r'<[^>]+>', '', inj_notes)
                desc += f" - {clean_n}"
                
            c_p = clean_name(p_name)
            add_intel(c_p, {
                "player_name": p_name,
                "raw_text": f"Official Injury Wire: {desc}",
                "snippet": clean_snippet_text(desc),
                "source_url": wire_link,
                "source_name": "INJURY WIRE"
            })
            sleeper_injuries_found += 1
            
    print(f"✓ Ingested and queued {sleeper_injuries_found} Sleeper injury records for LLM analysis!")

# 3. Source B: Twitter Beat Aggregation via Reddit Real-Time Feeds (r/nfl + r/fantasyfootball)
print("\n3. [SOURCE 2] Ingesting Live Twitter Beat Reports via Curated Feeds...")
twitter_matched = 0
reddit_endpoints = [
    ("[https://www.reddit.com/r/nfl/search.json?q=flair%3A%22Roster+Move%22+OR+flair%3A%22News%22&restrict_sr=1&sort=new&limit=40](https://www.reddit.com/r/nfl/search.json?q=flair%3A%22Roster+Move%22+OR+flair%3A%22News%22&restrict_sr=1&sort=new&limit=40)", "TWITTER NFL"),
    ("[https://www.reddit.com/r/fantasyfootball/search.json?q=flair%3ANews&restrict_sr=1&sort=new&limit=40](https://www.reddit.com/r/fantasyfootball/search.json?q=flair%3ANews&restrict_sr=1&sort=new&limit=40)", "TWITTER BEAT")
]

for r_url, src_label in reddit_endpoints:
    try:
        r_resp = requests.get(r_url, headers=reddit_headers, timeout=6)
        if r_resp.status_code == 200:
            posts = r_resp.json().get("data", {}).get("children", [])
            for post in posts:
                d = post.get("data", {})
                title = d.get("title", "")
                selftext = d.get("selftext", "")
                post_url = d.get("url", "[https://www.reddit.com](https://www.reddit.com)")
                full_text = f"{title}. {selftext}".strip()
                
                # Check player mentions including alias resolution
                matched_players = extract_players_fast(full_text, player_registry, primary_only=True)
                for full_pname in matched_players:
                    c_p = clean_name(full_pname)
                    rep_match = re.search(r'\[(.*?)\]', title)
                    reporter = rep_match.group(1).strip() if rep_match else src_label
                    add_intel(c_p, {
                        "player_name": full_pname,
                        "raw_text": full_text,
                        "snippet": clean_snippet_text(title),
                        "source_url": post_url,
                        "source_name": f"{src_label} ({reporter})"
                    })
                    twitter_matched += 1
    except Exception:
        pass

print(f"✓ Ingested {twitter_matched} curated real-time beat tweets & roster updates!")

# 4. Source C: FFToday IDP Positional Projections (DL=50, LB=60, DB=70)
print("\n4. [SOURCE 3] Ingesting FFToday IDP Player Wire & Statuses...")
idp_wire_matched = 0
if BS4_AVAILABLE:
    idp_pos_urls = [
        ("DL", clean_url("[https://www.fftoday.com/rankings/playerproj.php?PosID=50](https://www.fftoday.com/rankings/playerproj.php?PosID=50)")),
        ("LB", clean_url("[https://www.fftoday.com/rankings/playerproj.php?PosID=60](https://www.fftoday.com/rankings/playerproj.php?PosID=60)")),
        ("DB", clean_url("[https://www.fftoday.com/rankings/playerproj.php?PosID=70](https://www.fftoday.com/rankings/playerproj.php?PosID=70)"))
    ]
    for pos_label, url in idp_pos_urls:
        try:
            res = requests.get(url, headers=web_headers, timeout=8)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                rows = soup.find_all('tr')
                for row in rows:
                    link_tag = row.find('a', href=re.compile(r'stats/players/'))
                    if link_tag:
                        player_raw = link_tag.get_text().strip()
                        c_p = clean_name(player_raw)
                        if c_p in player_registry:
                            orig_player = player_registry[c_p]
                            href = link_tag['href']
                            full_url = clean_url(f"[https://www.fftoday.com](https://www.fftoday.com){href}") if href.startswith('/') else clean_url(href)
                            row_text = row.get_text()
                            
                            has_inj = any(k in row_text.lower() for k in ['out', 'ir', 'pup', 'doubtful', 'inj'])
                            c_matched = clean_name(orig_player)
                            desc_note = f"Active starting {pos_label} projection on FFToday depth chart" if not has_inj else f"Active injury designation on {pos_label} depth chart"
                            add_intel(c_matched, {
                                "player_name": orig_player,
                                "raw_text": f"FFToday IDP: {desc_note}",
                                "snippet": desc_note,
                                "source_url": full_url,
                                "source_name": "FFTODAY IDP"
                            })
                            idp_wire_matched += 1
        except Exception as e:
            print(f"⚠️ FFToday IDP notice ({pos_label}): {e}")

print(f"✓ Ingested {idp_wire_matched} FFToday IDP player profiles!")

# 5. Source D: FFToday News & Articles Hub
print("\n5. [SOURCE 4] Scraping FFToday News & Strategy Articles...")
fftoday_matched = 0
if BS4_AVAILABLE:
    fftoday_endpoints = [
        (clean_url("[https://www.fftoday.com/news/index.php](https://www.fftoday.com/news/index.php)"), "FFTODAY NEWS"),
        (clean_url("[https://www.fftoday.com/articles/index.php](https://www.fftoday.com/articles/index.php)"), "FFTODAY ARTICLE")
    ]
    for url, src_label in fftoday_endpoints:
        try:
            res = requests.get(url, headers=web_headers, timeout=8)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                blocks = soup.find_all(['tr', 'p', 'div', 'article'])
                for block in blocks:
                    b_text = block.get_text(separator=" ").strip()
                    if len(b_text) < 20 or len(b_text) > 1200:
                        continue
                    
                    matched_players = extract_players_fast(b_text, player_registry, primary_only=True)
                    for full_pname in matched_players:
                        c_p = clean_name(full_pname)
                        clean_b = clean_snippet_text(b_text)
                        add_intel(c_p, {
                            "player_name": full_pname,
                            "raw_text": b_text,
                            "snippet": clean_b,
                            "source_url": url,
                            "source_name": src_label
                        })
                        fftoday_matched += 1
        except Exception as e:
            print(f"⚠️ FFToday ({src_label}) notice: {e}")

print(f"✓ Extracted {fftoday_matched} live reports from FFToday!")

# 6. Source E: CBS Sports Deep Multi-Page News Archive & Superflex Hub
print("\n6. [SOURCE 5] Scraping CBS Sports Multi-Page News Archive & Superflex Hub...")
cbs_matched = 0
if BS4_AVAILABLE:
    cbs_pages = [
        (clean_url("[https://www.cbssports.com/fantasy/football/news/2026-superflex-podcast-mock-draft-waiting-on-qb-pays-off/](https://www.cbssports.com/fantasy/football/news/2026-superflex-podcast-mock-draft-waiting-on-qb-pays-off/)"), "CBS SUPERFLEX MOCK"),
        (clean_url("[https://www.cbssports.com/fantasy/football/draft-prep/](https://www.cbssports.com/fantasy/football/draft-prep/)"), "CBS DRAFT PREP"),
        (clean_url("[https://www.cbssports.com/fantasy/football/news/](https://www.cbssports.com/fantasy/football/news/)"), "CBS NEWS"),
        (clean_url("[https://www.cbssports.com/fantasy/football/](https://www.cbssports.com/fantasy/football/)"), "CBS WIRE")
    ]
    for p_num in range(1, 10):
        cbs_pages.append((clean_url(f"[https://www.cbssports.com/fantasy/football/players/news/all/](https://www.cbssports.com/fantasy/football/players/news/all/){p_num}/"), f"CBS ARCHIVE P{p_num}"))

    for page_url, src_label in cbs_pages:
        try:
            res = requests.get(page_url, headers=web_headers, timeout=6)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                article_blocks = soup.find_all(['div', 'article', 'section', 'h2', 'h3', 'h4', 'p', 'li'])
                for art in article_blocks:
                    raw_text = art.get_text(separator=" ").strip()
                    if len(raw_text) < 40 or len(raw_text) > 1500:
                        continue
                    # Skip site navigation / section-menu junk ("Explore ... News Scores
                    # Schedule Rankings Standings ...") that isn't real player news.
                    low = raw_text.lower()
                    nav_hits = sum(low.count(w) for w in ["explore", "scores", "schedule", "standings", "rankings", "watch live", "shop", "podcast"])
                    news_hits = any(w in low for w in ["caught", "targets", "practice", "camp", "snaps", "reps", "injury",
                                                       "questionable", "return", "starter", "backfield", "role", "yards",
                                                       "touchdown", "carries", "workload", "depth chart", "beat", "cleared"])
                    if nav_hits >= 3 or not news_hits:
                        continue

                    matched_players = extract_players_fast(raw_text, player_registry, primary_only=True)
                    for full_pname in matched_players:
                        c_p = clean_name(full_pname)
                        clean_b = clean_snippet_text(raw_text)
                        add_intel(c_p, {
                            "player_name": full_pname,
                            "raw_text": raw_text,
                            "snippet": clean_b,
                            "source_url": page_url,
                            "source_name": src_label
                        })
                        cbs_matched += 1
        except Exception:
            pass

print(f"✓ Extracted {cbs_matched} deep CBS Sports & Superflex mock updates across pages!")

# 7. Source F: 32BeatWriters Aggregator Feed
print("\n7. [SOURCE 6] Scraping 32BeatWriters.com Aggregator Feed...")
bw_matched = 0
try:
    res_bw = requests.get(clean_url("[https://www.32beatwriters.com/](https://www.32beatwriters.com/)"), headers=web_headers, timeout=8)
    if res_bw.status_code == 200:
        page_text = res_bw.text
        if BS4_AVAILABLE:
            soup = BeautifulSoup(page_text, 'html.parser')
            page_text = soup.get_text(separator="\n")
            
        bw_pattern = re.compile(
            r'[\*\•\-\–]?\s*([A-Za-z\.\'\-\s]+?)\.\s*([A-Z]{1,3})\s*[•·|\-]\s*([A-Za-z\s]+?)\.\s*([\s\S]+?)(?:Source:\s*([A-Za-z\s\.\-]+?)\.|\n\s*[\*\•\-\–]|\Z)', 
            re.MULTILINE
        )
        for m in bw_pattern.finditer(page_text):
            p_raw = m.group(1).strip()
            blurb = m.group(4).strip()
            reporter = m.group(5).strip() if m.group(5) else "32BeatWriters"
            c_p = clean_name(p_raw)
            
            matched_name = player_registry.get(c_p)
            if not matched_name:
                for k, v in player_registry.items():
                    if k == c_p or k in c_p:
                        matched_name = v
                        break
                        
            if matched_name and len(blurb) > 15:
                clean_b = " ".join(blurb.split())
                c_matched = clean_name(matched_name)
                scraped_intel_by_player[c_matched] = {
                    "player_name": matched_name,
                    "raw_text": f"{clean_b} (Reported by {reporter})",
                    "snippet": clean_b[:160],
                    "source_name": f"32BEAT ({reporter})",
                    "source_url": clean_url("[https://www.32beatwriters.com/](https://www.32beatwriters.com/)")
                }
                bw_matched += 1
except Exception as e:
    print(f"⚠️ 32BeatWriters notice: {e}")

print(f"✓ Extracted {bw_matched} beat nuggets from 32BeatWriters.com!")

# 7b. Source F2: High-quality free HTML news hubs (NFL.com, FantasyPros, PFF, Footballguys)
print("\n7b. [SOURCE 6b] Scraping NFL.com / FantasyPros / PFF / Footballguys news hubs...")
hub_matched = 0
NEWS_KEYWORDS = ["caught", "targets", "practice", "camp", "snaps", "reps", "injury",
                 "questionable", "return", "starter", "backfield", "role", "yards",
                 "touchdown", "carries", "workload", "depth chart", "beat", "cleared",
                 "qb1", "named", "activated", "fantasy impact", "trending", "1st-team",
                 "first-team", "separation", "explosive"]
if BS4_AVAILABLE:
    news_hubs = [
        ("https://www.rotowire.com/football/news.php", "ROTOWIRE"),
        ("https://www.nfl.com/news/", "NFL.COM"),
        ("https://www.fantasypros.com/nfl/player-news.php", "FANTASYPROS"),
        ("https://www.pff.com/news", "PFF"),
        ("https://www.footballguys.com/news", "FOOTBALLGUYS"),
    ]
    for hub_url, src_label in news_hubs:
        try:
            res = requests.get(clean_url(hub_url), headers=web_headers, timeout=8)
            if res.status_code != 200:
                continue
            soup = BeautifulSoup(res.text, 'html.parser')
            for block in soup.find_all(['p', 'li', 'h2', 'h3', 'h4', 'div', 'article']):
                raw_text = block.get_text(separator=" ").strip()
                if len(raw_text) < 40 or len(raw_text) > 1200:
                    continue
                low = raw_text.lower()
                nav_hits = sum(low.count(w) for w in ["explore", "scores", "schedule", "standings",
                                                      "rankings", "watch live", "shop", "podcast", "all articles"])
                if nav_hits >= 3 or not any(w in low for w in NEWS_KEYWORDS):
                    continue
                for full_pname in extract_players_fast(raw_text, player_registry, primary_only=True):
                    c_p = clean_name(full_pname)
                    add_intel(c_p, {
                        "player_name": full_pname,
                        "raw_text": raw_text,
                        "snippet": clean_snippet_text(raw_text),
                        "source_url": clean_url(hub_url),
                        "source_name": src_label
                    })
                    hub_matched += 1
        except Exception as e:
            print(f"⚠️ News hub notice ({src_label}): {e}")

print(f"✓ Extracted {hub_matched} reports from premium free news hubs!")

# 8. Source G: Free Multi-Source XML RSS Feeds
print("\n8. [SOURCE 7] Ingesting Non-Paywalled XML RSS Feeds...")
rss_matched = 0
rss_urls = [
    (clean_url("https://www.rotowire.com/rss/news.php?sport=NFL"), "ROTOWIRE"),
    (clean_url("https://www.rotowire.com/rss/news.php?sport=NFL&posID=RB"), "ROTOWIRE"),
    (clean_url("https://www.rotowire.com/rss/news.php?sport=NFL&posID=WR"), "ROTOWIRE"),
    (clean_url("https://www.rotowire.com/rss/news.php?sport=NFL&posID=QB"), "ROTOWIRE"),
    (clean_url("https://www.rotowire.com/rss/news.php?sport=NFL&posID=TE"), "ROTOWIRE"),
    (clean_url("https://sports.yahoo.com/nfl/rss/"), "YAHOO NFL"),
    (clean_url("https://www.rotoballer.com/feed"), "ROTOBALLER"),
    (clean_url("https://www.fantasysp.com/rss/nfl/allplayer/"), "FANTASYSP"),
    (clean_url("https://www.fantasysp.com/rss/nfl/headlines/"), "FANTASYSP WIRE"),
    (clean_url("https://www.fftoday.com/rss/news.xml"), "FFTODAY RSS"),
    (clean_url("https://www.cbssports.com/rss/headlines/fantasy/football/"), "CBS RSS")
]

for r_url, src_tag in rss_urls:
    try:
        r_res = requests.get(r_url, headers=web_headers, timeout=6)
        if r_res.status_code == 200:
            root = ET.fromstring(r_res.content)
            for item in root.findall(".//item")[:30]:
                title = item.find("title").text if item.find("title") is not None else ""
                desc = item.find("description").text if item.find("description") is not None else ""
                link = item.find("link").text if item.find("link") is not None else ""
                clean_desc = re.sub(r'<[^>]+>', '', desc).strip()
                full_body = f"{title}. {clean_desc}"

                # RotoWire/RotoBaller titles are "Player Name: Headline" — the subject
                # is explicit before the colon, so resolve it directly (most accurate).
                matched_players = []
                if ":" in title:
                    subj = title.split(":", 1)[0].strip()
                    c_subj = clean_name(subj)
                    if c_subj in player_registry:
                        matched_players = [player_registry[c_subj]]
                if not matched_players:
                    matched_players = extract_players_fast(full_body, player_registry, primary_only=True)

                for full_pname in matched_players:
                    c_p = clean_name(full_pname)
                    add_intel(c_p, {
                        "player_name": full_pname,
                        "raw_text": full_body,
                        "snippet": clean_snippet_text(full_body),
                        "source_url": clean_url(link) if link else "",
                        "source_name": src_tag
                    })
                    rss_matched += 1
    except Exception as e:
        print(f"⚠️ RSS Notice for {src_tag}: {e}")

print(f"✓ Ingested {rss_matched} RSS beat wire reports!")

# 9. Source H: Sleeper 24-Hour Live Trending Waiver Adds
print("\n9. [SOURCE 8] Querying Sleeper Live 24h Waiver Surges...")
trending_adds_count = 0
try:
    trending_adds = requests.get(clean_url("[https://api.sleeper.app/v1/players/nfl/trending/add?lookback_hours=24&limit=30](https://api.sleeper.app/v1/players/nfl/trending/add?lookback_hours=24&limit=30)"), timeout=5).json()
    if isinstance(trending_adds, list):
        for item in trending_adds:
            pid = str(item.get('player_id'))
            add_cnt = item.get('count', 0)
            if pid in p_db:
                p_info = p_db[pid]
                p_name = f"{p_info.get('first_name', '')} {p_info.get('last_name', '')}".strip()
                slug_name = clean_name(p_name).replace(" ", "-")
                wire_link = clean_url(f"[https://www.rotoballer.com/nfl/player-news?player=](https://www.rotoballer.com/nfl/player-news?player=){slug_name}")
                
                if p_name:
                    c_p = clean_name(p_name)
                    add_intel(c_p, {
                        "player_name": p_name,
                        "raw_text": f"Surging on waiver wire across competitive leagues (+{add_cnt} adds in last 24 hours). Opportunity breakout or camp role spike.",
                        "snippet": f"Waiver Surge (+{add_cnt} adds in 24h)",
                        "source_url": wire_link,
                        "source_name": "WAIVER SURGE"
                    })
                    trending_adds_count += 1
    print(f"✓ Matched {trending_adds_count} surging waiver additions!")
except Exception as e:
    print(f"⚠️ Sleeper Waiver Notice: {e}")

# ==============================================================================
# 10. CONCURRENT PARALLEL GROQ LLM SENTIMENT ANALYSIS (PRIORITIZED)
# ==============================================================================

# Load the draft-board player set so we spend the LLM budget on players you can
# actually draft first, and real beat/news sources before the mass injury wire.
board_clean = set()
try:
    import csv
    with open("top_150_draft_board.csv") as _bf:
        for _row in csv.DictReader(_bf):
            cn = _row.get("clean_name") or clean_name(_row.get("player_name", ""))
            if cn:
                board_clean.add(cn)
except Exception:
    pass

# Sources that carry real performance/beat text worth crunching (vs. bare injury status).
RICH_SOURCES = ("32BEAT", "CBS", "FFTODAY NEWS", "FFTODAY ARTICLE", "ROTOBALLER",
                "FANTASYSP", "TWITTER", "WAIVER", "FFTODAY RSS", "CBS RSS",
                "ROTOWIRE", "NFL.COM", "FANTASYPROS", "PFF", "FOOTBALLGUYS", "YAHOO")

def _priority(item):
    cn = clean_name(item.get("player_name", ""))
    on_board = cn in board_clean
    src = str(item.get("source_name", "")).upper()
    rich = any(s in src for s in RICH_SOURCES)
    # higher score = analyzed first
    return (2 if on_board else 0) + (1 if rich else 0)

queue_list = sorted(scraped_intel_by_player.values(), key=_priority, reverse=True)
target_count = min(len(queue_list), 320)
print(f"\n10. Running Concurrent Parallel Groq LLM Analysis on {target_count} prioritized player reports "
      f"({sum(1 for i in queue_list[:target_count] if clean_name(i.get('player_name','')) in board_clean)} on your draft board)...")

llm_evaluated_count = 0
api_key = get_active_groq_key()
candidate_models = get_available_groq_models(api_key) if api_key else []

def _ollama_up():
    try:
        return requests.get(f"{os.getenv('OLLAMA_URL','http://localhost:11434')}/api/tags", timeout=3).status_code == 200
    except Exception:
        return False

# Run the LLM crunch if we have EITHER Groq OR a local Ollama fallback, so the
# pipeline stays up on local Llama when Groq is missing/capped.
_have_llm = bool(api_key) or _ollama_up()
if queue_list and _have_llm:
    if not api_key:
        print("   (no Groq key — using local Ollama/Llama fallback for the crunch)")
    batch_size = 5
    batches = [queue_list[i:i + batch_size] for i in range(0, target_count, batch_size)]
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(process_single_groq_batch, batch, api_key, candidate_models) for batch in batches]
        for future in as_completed(futures):
            try:
                batch_res = future.result()
                for p_name, entry in batch_res.items():
                    camp_overrides[p_name] = entry
                    llm_evaluated_count += 1
            except Exception:
                pass

print(f"✓ Groq LLM enriched {llm_evaluated_count} high-signal player profiles with crunchy tactical reads!")

# Fallback for remaining items
for art in queue_list[:target_count]:
    orig_player = art["player_name"]
    if orig_player not in camp_overrides:
        src_label = art.get("source_name", "BEAT WIRE")
        camp_overrides[orig_player] = {
            "multiplier": 1.04 if "WAIVER" in src_label else 1.00,
            "type": "WAIVER_SURGE" if "WAIVER" in src_label else ("INJURY_ALERT" if "INJURY" in src_label else "BEAT"),
            "note": art['snippet'],
            "source_url": art.get("source_url", "")
        }

# ==============================================================================
# 11. SANITIZE + VALIDATE OVERRIDES (kill junk keys, dupes, generic notes)
# ==============================================================================

def sanitize_overrides(raw: dict) -> dict:
    """Cleans the override map before persisting:
    - drops junk/placeholder keys (e.g. 'Duplicate Player', blanks, 1-word names)
    - clamps multipliers into a sane [0.75, 1.15] band
    - de-duplicates on normalized name (keeps the richest note)
    - drops entries with empty/generic notes so the intel column never shows fluff
    """
    JUNK_KEYS = {"duplicate player", "player", "unknown", "n/a", "none", "team", ""}
    GENERIC = {"positive camp buzz", "trending up", "looking good", "injury report",
               "report", "update", "buzz", "n/a", "none", "-", "—"}
    by_clean = {}
    for name, entry in raw.items():
        if not isinstance(entry, dict):
            continue
        cname = clean_name(name)
        if cname in JUNK_KEYS or len(cname) < 4 or len(cname.split()) < 2:
            continue
        note = str(entry.get("note", "")).strip()
        if not note or note.lower() in GENERIC:
            continue
        try:
            mult = float(entry.get("multiplier", 1.0))
        except (TypeError, ValueError):
            mult = 1.0
        entry["multiplier"] = round(max(0.75, min(1.15, mult)), 2)
        # de-dupe: keep the entry with the longer (more specific) note
        prev = by_clean.get(cname)
        if prev is None or len(note) > len(str(prev[1].get("note", ""))):
            by_clean[cname] = (name, entry)
    return {orig: entry for (orig, entry) in by_clean.values()}

before_count = len(camp_overrides)
camp_overrides = sanitize_overrides(camp_overrides)
print(f"✓ Sanitized overrides: {before_count} -> {len(camp_overrides)} (dropped junk keys, dupes, and generic notes).")

# ==============================================================================
# 12. PERSIST OUTPUT TO CAMP_OVERRIDES.JSON
# ==============================================================================

with open("camp_overrides.json", "w") as f:
    json.dump(camp_overrides, f, indent=2)

print(f"\n✅ SUCCESS: Saved {len(camp_overrides)} verified multi-source overrides to 'camp_overrides.json'!")