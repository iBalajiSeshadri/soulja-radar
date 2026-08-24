import os
import requests
import json
import re
from datetime import datetime

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

# ==============================================================================
# 0. CONFIGURATION & GROQ LLM RESOLUTION
# ==============================================================================

def get_active_groq_key() -> str:
    """Safely retrieves Groq API Key from secrets.toml or environment."""
    if os.path.exists(".streamlit/secrets.toml"):
        try:
            with open(".streamlit/secrets.toml", "r") as f:
                for line in f:
                    if "GROQ_API_KEY" in line and "=" in line:
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
    return os.getenv("GROQ_API_KEY", "").strip().strip('"').strip("'")

VERIFIED_GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "openai/gpt-oss-20b",
    "qwen/qwen3.6-27b"
]

def clean_name(name):
    if not isinstance(name, str):
        return ""
    name = name.lower().strip()
    name = re.sub(r"[^\w\s]", "", name)
    name = re.sub(r"\b(jr|sr|iii|ii|iv|v)\b", "", name)
    return " ".join(name.split())

def clean_snippet_text(text, max_len=160):
    text = " ".join(text.split())
    text = re.sub(r"^(Rotowire|CBS Sports|Fantasy Staff|RotoBaller|FFToday|32BeatWriters)\s*[:\-]\s*", "", text, flags=re.IGNORECASE)
    if len(text) > max_len:
        return text[:max_len].rsplit(' ', 1)[0] + "..."
    return text

def parse_is_fresh(time_str):
    if not time_str:
        return True
    t = time_str.lower().strip()
    if any(k in t for k in ['m ago', 'h ago', 'min', 'hour', 'today', 'yesterday', 'aug', 'sep']):
        return True
    day_match = re.search(r'(\d+)\s*d\b', t) or re.search(r'(\d+)\s*day', t)
    if day_match:
        return int(day_match.group(1)) <= 4
    return False

def extract_headline_subject(raw_text):
    if ':' not in raw_text:
        return None, raw_text
    
    parts = raw_text.split(':', 1)
    subject_raw = parts[0].strip()
    headline_text = parts[1].strip()
    
    subject_clean = re.sub(r"^[A-Za-z0-9\s\.\-]+\'\s*", "", subject_raw).strip()
    subject_clean = re.sub(r"\s+(QB|RB|WR|TE|K|DEF|LB|DL|DB|DE|DT|CB|S|ILB|OLB|SS|FS)\s*\|.*$", "", subject_clean, flags=re.IGNORECASE).strip()
    return subject_clean, headline_text

# ==============================================================================
# 1. BATCH GROQ LLM BEAT SENTIMENT & CRUNCHY NOTE GENERATOR
# ==============================================================================

def analyze_beat_articles_with_groq(articles_batch):
    """
    Sends raw beat snippets to Groq to extract:
    1. Actionable semantic tag (TIER_JUMPER, ROLE_PINCH, VET_MAINTENANCE, INJURY_ALERT, CLEARED, NOISE)
    2. Clamped safe multiplier (0.75x to 1.15x)
    3. 1-sentence crunchy fantasy insight
    """
    api_key = get_active_groq_key()
    if not api_key:
        return {}

    prompt_items = []
    for idx, item in enumerate(articles_batch):
        prompt_items.append({
            "id": idx,
            "player": item["player_name"],
            "source": item.get("source_name", "Beat Wire"),
            "report": item["raw_text"][:300]
        })

    system_prompt = """You are an expert quantitative fantasy football beat analyst.
Read these beat writer blurbs (from 32BeatWriters, local beat reporters, and news wires) and return structured fantasy insights.

TAG CLASSIFICATION RULES:
- TIER_JUMPER: Concrete 1st-team target domination, depth chart ascent, manufactured touch design. (Multiplier: 1.06 to 1.15)
- ROLE_PINCH: Loss of goal-line or 3rd-down pass snaps to backups, 50/50 committee squeeze. (Multiplier: 0.84 to 0.94)
- VET_MAINTENANCE: Precautionary veteran rest, minor soreness with zero regular-season structural risk. (Multiplier: 0.96 to 0.99)
- INJURY_ALERT: Actual multi-week sprain, surgery, PUP, or IR designation. (Multiplier: 0.75 to 0.88)
- CLEARED: Full participant in 11-on-11 contact after prior injury. (Multiplier: 1.00 to 1.03)
- NOISE: Preseason fluff ("best shape of life", generic quotes). (Multiplier: 1.00)

Return JSON ONLY as a list of objects:
[
  {
    "id": 0,
    "player_name": "Player Name",
    "tag": "TIER_JUMPER | ROLE_PINCH | VET_MAINTENANCE | INJURY_ALERT | CLEARED | NOISE",
    "multiplier": 1.10,
    "crunchy_note": "1 concise sentence translating beat report to schematic volume, target share, or health status."
  }
]
"""

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    for model_name in VERIFIED_GROQ_MODELS:
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Analyze these {len(prompt_items)} articles:\n" + json.dumps(prompt_items)}
            ],
            "temperature": 0.1,
            "max_tokens": 2048,
            "response_format": {"type": "json_object"} if "llama-3" in model_name else None
        }
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=12)
            if res.status_code == 200:
                raw_content = res.json()["choices"][0]["message"]["content"]
                raw_content = re.sub(r'^```json\s*', '', raw_content.strip())
                raw_content = re.sub(r'\s*```$', '', raw_content.strip())
                
                parsed = json.loads(raw_content)
                if isinstance(parsed, dict) and "items" in parsed:
                    parsed = parsed["items"]
                elif isinstance(parsed, dict) and len(parsed) == 1:
                    parsed = list(parsed.values())[0]

                results = {}
                for entry in parsed:
                    if not isinstance(entry, dict):
                        continue
                    item_id = entry.get("id")
                    if item_id is not None and item_id < len(articles_batch):
                        p_meta = articles_batch[item_id]
                        mult = float(entry.get("multiplier", 1.0))
                        mult = max(0.75, min(1.15, mult)) # Strict Clamp Guardrail
                        
                        src_label = p_meta.get("source_name", "BEAT WIRE")
                        results[p_meta["player_name"]] = {
                            "multiplier": round(mult, 2),
                            "type": entry.get("tag", "BEAT"),
                            "note": f"📰 {src_label}: {entry.get('crunchy_note', p_meta['snippet'])}",
                            "source_url": p_meta["source_url"]
                        }
                if results:
                    return results
        except Exception as e:
            print(f"⚠️ LLM Model ({model_name}) parse note: {e}")
            continue
            
    return {}

# ==============================================================================
# 2. MAIN MULTI-SOURCE PIPELINE (SLEEPER + FFTODAY + CBS + 32BEATWRITERS)
# ==============================================================================

print("==================================================================")
print("  SOULJA SOULJA MULTI-SOURCE BEAT & INJURY AGGREGATOR")
print("==================================================================")

camp_overrides = {}
headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

# 1. Universal Player Registry from Sleeper API
print("\n1. Building universal NFL player registry from Sleeper API...")
player_registry = {}
p_db = {}
try:
    p_db = requests.get("https://api.sleeper.app/v1/players/nfl", timeout=12).json()
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

# 2. Source A: Sleeper Official Real-Time Injury Wire (Offense + IDP)
print("\n2. [SOURCE 1] Ingesting Sleeper Official API Injury Wire...")
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
        if rotowire_id:
            wire_link = f"https://www.rotowire.com/football/player/{slug_name}-{rotowire_id}"
        else:
            wire_link = f"https://www.rotoballer.com/nfl/player-news?player={slug_name}"
            
        if status in ['IR', 'PUP', 'Sus', 'Out'] or inj_status in ['IR', 'Out', 'PUP', 'Doubtful']:
            desc = f"{inj_status or status}"
            if inj_body: desc += f" ({inj_body})"
            if inj_notes: 
                clean_n = re.sub(r'<[^>]+>', '', inj_notes)
                desc += f" - {clean_n[:120]}"
                
            camp_overrides[p_name] = {
                "multiplier": 0.20 if status in ['IR', 'PUP', 'Out'] else 0.50,
                "type": "INJURY",
                "note": f"❌ INJURY WIRE: {desc}",
                "source_url": wire_link
            }
            sleeper_injuries_found += 1
            
        elif inj_status == 'Questionable' and p_name not in camp_overrides:
            desc = f"Questionable ({inj_body})" if inj_body else "Questionable"
            if inj_notes:
                clean_n = re.sub(r'<[^>]+>', '', inj_notes)
                desc += f" - {clean_n[:120]}"
                
            camp_overrides[p_name] = {
                "multiplier": 0.88,
                "type": "QUESTIONABLE",
                "note": f"🩹 INJURY WIRE: {desc}",
                "source_url": wire_link
            }
            sleeper_injuries_found += 1
            
    print(f"✓ Ingested {sleeper_injuries_found} official injury designations!")

# 3. Source B: FFToday IDP Wire & Beat Profiles (DL=50, LB=60, DB=70)
print("\n3. [SOURCE 2] Ingesting FFToday IDP Player Wire & Statuses...")
idp_wire_matched = 0
if BS4_AVAILABLE:
    idp_pos_urls = [
        ("DL", "https://www.fftoday.com/rankings/playerproj.php?PosID=50"),
        ("LB", "https://www.fftoday.com/rankings/playerproj.php?PosID=60"),
        ("DB", "https://www.fftoday.com/rankings/playerproj.php?PosID=70")
    ]
    for pos_label, url in idp_pos_urls:
        try:
            res = requests.get(url, headers=headers, timeout=8)
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
                            full_url = f"https://www.fftoday.com{href}" if href.startswith('/') else href
                            
                            row_text = row.get_text()
                            if any(k in row_text.lower() for k in ['out', 'ir', 'pup', 'doubtful', 'inj']):
                                if orig_player not in camp_overrides:
                                    camp_overrides[orig_player] = {
                                        "multiplier": 0.60,
                                        "type": "INJURY",
                                        "note": f"🩹 FFTODAY IDP WIRE: Active injury designation on {pos_label} depth chart",
                                        "source_url": full_url
                                    }
                                    idp_wire_matched += 1
                            elif orig_player not in camp_overrides:
                                camp_overrides[orig_player] = {
                                    "multiplier": 1.00,
                                    "type": "BEAT",
                                    "note": f"🛡️ FFTODAY IDP: Core starting {pos_label} projection",
                                    "source_url": full_url
                                }
                                idp_wire_matched += 1
        except Exception as e:
            print(f"⚠️ FFToday IDP parser notice for {pos_label}: {e}")

print(f"✓ Ingested {idp_wire_matched} FFToday IDP player profiles!")

# 4. Collection for LLM Batch Analysis (CBS + 32BeatWriters)
articles_to_analyze = []

# Source C: CBS Sports Feed
print("\n4. [SOURCE 3] Scraping CBS RotoWire Feed...")
cbs_fresh = 0
for page in range(1, 10):
    cbs_url = f"https://www.cbssports.com/fantasy/football/players/news/all/{page}/"
    try:
        res = requests.get(cbs_url, headers=headers, timeout=8)
        if res.status_code == 200 and BS4_AVAILABLE:
            soup = BeautifulSoup(res.text, 'html.parser')
            articles = soup.find_all('div', class_='tag-article') or soup.find_all('div', class_='article')
            
            for art in articles:
                raw_text = art.get_text().strip()
                if len(raw_text) < 20: continue
                    
                date_tag = art.find('span', class_='article-date') or art.find('span', class_='timestamp') or art.find('time')
                time_str = date_tag.get_text().strip() if date_tag else "recent"
                is_fresh = parse_is_fresh(time_str)

                link_tag = art.find('a', href=True)
                source_link = f"https://www.cbssports.com{link_tag['href']}" if link_tag and link_tag['href'].startswith('/') else "https://www.cbssports.com/fantasy/football/news/"

                subject_candidate, headline = extract_headline_subject(raw_text)
                if not subject_candidate: continue
                    
                c_sub = clean_name(subject_candidate)
                if c_sub in player_registry and is_fresh:
                    orig_player = player_registry[c_sub]
                    snippet = clean_snippet_text(f"{subject_candidate}: {headline}")
                    articles_to_analyze.append({
                        "player_name": orig_player,
                        "raw_text": f"{headline}. {raw_text}",
                        "snippet": snippet,
                        "source_url": source_link,
                        "source_name": f"CBS BEAT ({time_str})"
                    })
                    cbs_fresh += 1
        else:
            break
    except Exception:
        break

print(f"✓ Found {cbs_fresh} fresh CBS beat reports.")

# Source D: 32BeatWriters Feed Aggregator (https://www.32beatwriters.com/)
print("\n5. [SOURCE 4] Scraping 32BeatWriters.com Aggregator Feed...")
beatwriters_matched = 0
if BS4_AVAILABLE:
    try:
        bw_url = "https://www.32beatwriters.com/"
        res_bw = requests.get(bw_url, headers=headers, timeout=10)
        if res_bw.status_code == 200:
            soup = BeautifulSoup(res_bw.text, 'html.parser')
            
            # 32BeatWriters structure matches player names, reporter credits, and blurbs
            text_blocks = soup.find_all(['div', 'article', 'li', 'p', 'section'])
            for block in text_blocks:
                b_text = block.get_text().strip()
                if len(b_text) < 30 or len(b_text) > 800:
                    continue
                
                # Check for player name mentions from registry
                for c_name, full_pname in player_registry.items():
                    if len(c_name) > 5 and re.search(r'\b' + re.escape(c_name) + r'\b', clean_name(b_text)):
                        # Look for beat writer attribution if present
                        source_match = re.search(r'Source:\s*([A-Za-z\s\.\-]+)', b_text, re.IGNORECASE)
                        reporter_name = source_match.group(1).strip() if source_match else "32BeatWriters"
                        
                        articles_to_analyze.append({
                            "player_name": full_pname,
                            "raw_text": b_text,
                            "snippet": clean_snippet_text(b_text),
                            "source_url": "https://www.32beatwriters.com/",
                            "source_name": f"32BEAT ({reporter_name})"
                        })
                        beatwriters_matched += 1
                        break
    except Exception as e:
        print(f"⚠️ 32BeatWriters scraping notice: {e}")

print(f"✓ Extracted {beatwriters_matched} beat nuggets from 32BeatWriters.com!")

# 6. Execute Batch LLM Beat Sentiment Analysis
print(f"\n6. Running Groq LLM Beat Sentiment Analysis on {len(articles_to_analyze)} total beat items...")
llm_evaluated_count = 0
if articles_to_analyze and get_active_groq_key():
    # Process up to 60 total items in batches of 20
    for i in range(0, min(len(articles_to_analyze), 60), 20):
        batch = articles_to_analyze[i:i+20]
        llm_results = analyze_beat_articles_with_groq(batch)
        for p_name, entry in llm_results.items():
            # Never overwrite severe official IR designations with mild blurb
            if p_name in camp_overrides and camp_overrides[p_name].get("type") == "INJURY" and camp_overrides[p_name].get("multiplier") <= 0.50:
                continue
            camp_overrides[p_name] = entry
            llm_evaluated_count += 1

print(f"✓ Groq LLM classified & enriched {llm_evaluated_count} player profiles with tactical notes!")

# Fallback regex for articles not evaluated by LLM
SEVERE_INJURY_REGEX = re.compile(r'\b(placed on ir|placed on pup|torn acl|torn achilles|out for season|suffered a knee|carted off|undergoing mri|ruled out|did not play due to injury|leaving on a cart)\b', re.IGNORECASE)
TWEAK_REGEX = re.compile(r'\b(hamstring|calf strain|ankle sprain|groin|limited in practice|questionable|game-time decision)\b', re.IGNORECASE)
CLEARANCE_REGEX = re.compile(r'\b(cleared|passed physical|off pup|removed from injury report|practicing in full|fully healthy)\b', re.IGNORECASE)

for art in articles_to_analyze:
    orig_player = art["player_name"]
    if orig_player not in camp_overrides:
        raw_text = art["raw_text"]
        snippet = art["snippet"]
        source_link = art["source_url"]
        src_label = art.get("source_name", "BEAT WIRE")

        if SEVERE_INJURY_REGEX.search(raw_text):
            camp_overrides[orig_player] = {
                "multiplier": 0.20, "type": "INJURY",
                "note": f"❌ {src_label}: {snippet}", "source_url": source_link
            }
        elif TWEAK_REGEX.search(raw_text):
            camp_overrides[orig_player] = {
                "multiplier": 0.88, "type": "QUESTIONABLE",
                "note": f"🩹 {src_label}: {snippet}", "source_url": source_link
            }
        elif CLEARANCE_REGEX.search(raw_text):
            camp_overrides[orig_player] = {
                "multiplier": 1.00, "type": "CLEARED",
                "note": f"✅ {src_label}: {snippet}", "source_url": source_link
            }
        else:
            camp_overrides[orig_player] = {
                "multiplier": 1.00, "type": "BEAT",
                "note": f"📰 {src_label}: {snippet}", "source_url": source_link
            }

# 7. Source E: Sleeper 24-Hour Live Trending Waiver Adds
print("\n7. [SOURCE 5] Querying Sleeper Live 24h Waiver Surges...")
try:
    trending_adds = requests.get("https://api.sleeper.app/v1/players/nfl/trending/add?lookback_hours=24&limit=30", timeout=5).json()
    adds_matched = 0
    if isinstance(trending_adds, list):
        for item in trending_adds:
            pid = str(item.get('player_id'))
            add_cnt = item.get('count', 0)
            if pid in p_db:
                p_info = p_db[pid]
                p_name = f"{p_info.get('first_name', '')} {p_info.get('last_name', '')}".strip()
                slug_name = clean_name(p_name).replace(" ", "-")
                wire_link = f"https://www.rotoballer.com/nfl/player-news?player={slug_name}"
                
                if p_name:
                    if p_name in camp_overrides:
                        camp_overrides[p_name]["note"] += f" | 🔥 SLEEPER SURGE (+{add_cnt} adds)"
                    else:
                        camp_overrides[p_name] = {
                            "multiplier": 1.06, "type": "BREAKOUT",
                            "note": f"🔥 WAIVER SPIKE: Surging camp pickup (+{add_cnt} adds in 24h)",
                            "source_url": wire_link
                        }
                    adds_matched += 1
    print(f"✓ Matched {adds_matched} surging waiver additions!")
except Exception as e:
    print(f"⚠️ Sleeper Notice: {e}")

# ==============================================================================
# 3. PERSIST OUTPUT TO CAMP_OVERRIDES.JSON
# ==============================================================================

with open("camp_overrides.json", "w") as f:
    json.dump(camp_overrides, f, indent=2)

print(f"\n✅ SUCCESS: Saved {len(camp_overrides)} multi-source overrides to 'camp_overrides.json'!")