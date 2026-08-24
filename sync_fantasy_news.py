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
            preferred = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3.6-27b", "llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
            ordered = [p for p in preferred if p in valid] + [v for v in valid if v not in preferred]
            if ordered:
                return ordered
    except Exception:
        pass
    return ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3.6-27b"]

def clean_name(name):
    if not isinstance(name, str):
        return ""
    name = name.lower().strip()
    name = re.sub(r"[^\w\s]", "", name)
    name = re.sub(r"\b(jr|sr|iii|ii|iv|v)\b", "", name)
    return " ".join(name.split())

def clean_snippet_text(text, max_len=180):
    text = " ".join(text.split())
    text = re.sub(r"^(Rotowire|CBS Sports|Fantasy Staff|RotoBaller|FFToday|32BeatWriters|FantasySP)\s*[:\-]\s*", "", text, flags=re.IGNORECASE)
    if len(text) > max_len:
        return text[:max_len].rsplit(' ', 1)[0] + "..."
    return text

def extract_players_fast(text, registry):
    """
    O(1) Fast Proper Noun Extractor: Matches capitalized 2-word names against registry in 0.0001s.
    """
    found = []
    if not text or len(text) < 10:
        return found
    candidates = re.findall(r'\b[A-Z][a-zA-Z\.\'-]+\s+[A-Z][a-zA-Z\.\'-]+\b', text)
    for cand in candidates:
        c_cand = clean_name(cand)
        if c_cand in registry:
            found.append(registry[c_cand])
    return list(set(found))

# ==============================================================================
# 1. PARALLEL GROQ LLM BATCH WORKER
# ==============================================================================

def parse_llm_batch_response(raw_text: str, batch_map: dict):
    """Token-aware fuzzy name matcher with thinking suppression."""
    clean_text = re.sub(r'<think>.*?</think>', '', raw_text, flags=re.DOTALL)
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
                    mult = float(it.get("mult") or it.get("multiplier") or 1.0)
                    mult = max(0.75, min(1.15, mult)) # Clamped guardrail
                    tag = str(it.get("tag") or "BEAT").upper()
                    note = str(it.get("note") or it.get("crunchy_note") or "").strip()
                    meta = batch_map[matched_orig]
                    
                    src_label = meta.get('source_name', 'BEAT WIRE')
                    results[matched_orig] = {
                        "multiplier": round(mult, 2),
                        "type": tag,
                        "note": f"📰 {src_label}: {note if note else meta['snippet']}",
                        "source_url": meta.get('source_url', '')
                    }
        except Exception:
            pass
    return results

def process_single_groq_batch(batch_items, api_key, candidate_models):
    """Worker function for concurrent thread pool execution with 1:1 mandate."""
    if not batch_items or not api_key:
        return {}

    batch_map = {item["player_name"]: item for item in batch_items}
    prompt_payload = [
        {
            "name": item["player_name"],
            "source": item.get("source_name", "Beat Wire"),
            "report": item["raw_text"][:300]
        }
        for item in batch_items
    ]

    system_prompt = f"""You are an expert quantitative NFL fantasy football beat analyst.
Analyze these {len(prompt_payload)} genuine NFL beat reports and Superflex takeaways.

STRICT MANDATE:
You MUST return a JSON array containing EXACTLY {len(prompt_payload)} objects (one for every player listed). Do NOT omit any player.

TAG RULES:
- TIER_JUMPER: Concrete 1st-team target domination, depth chart ascent. (Multiplier: 1.06 to 1.15)
- SUPERFLEX_EDGE: Superflex/2QB draft value surge, QB tier leverage. (Multiplier: 1.05 to 1.12)
- ROLE_PINCH: Loss of goal-line/3rd-down snaps, committee split. (Multiplier: 0.84 to 0.94)
- VET_MAINTENANCE: Precautionary rest, zero regular-season structural risk. (Multiplier: 0.96 to 0.99)
- INJURY_ALERT: Multi-week sprain, PUP, or IR risk. (Multiplier: 0.75 to 0.88)
- CLEARED: Full participant in 11-on-11 contact. (Multiplier: 1.00 to 1.03)
- NOISE: Preseason fluff / neutral blurb. (Multiplier: 1.00)

OUTPUT FORMAT: Return a valid JSON array of {len(prompt_payload)} objects:
[
  {{"name": "Player Name", "tag": "TAG", "mult": 1.10, "note": "1 concise sentence on volume/role/leverage."}}
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
            "max_tokens": 1600
        }
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=9)
            if res.status_code == 200:
                raw_content = res.json()["choices"][0]["message"]["content"]
                results = parse_llm_batch_response(raw_content, batch_map)
                if results:
                    return results
            elif res.status_code == 429:
                time.sleep(1.0)
        except Exception:
            continue
            
    return {}

# ==============================================================================
# 2. MAIN NEWS AGGREGATION PIPELINE (GENUINE SIGNALS ONLY)
# ==============================================================================

print("==================================================================")
print("  SOULJA SOULJA MULTI-SOURCE BEAT, IDP & SUPERFLEX AGGREGATOR")
print("==================================================================")

camp_overrides = {}
scraped_intel_by_player = {}

web_headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': '[https://www.google.com/](https://www.google.com/)'
}

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

# 2. Source A: Sleeper Official Injury Wire & Real-Time Beat Blurbs
print("\n2. [SOURCE 1] Ingesting Sleeper Official Injury Wire & Active Notes...")
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
            
        elif inj_notes and len(inj_notes) > 15:
            clean_n = re.sub(r'<[^>]+>', '', inj_notes)
            c_p = clean_name(p_name)
            scraped_intel_by_player[c_p] = {
                "player_name": p_name,
                "raw_text": f"{inj_status or 'Report'}: {clean_n}",
                "snippet": clean_snippet_text(clean_n),
                "source_url": wire_link,
                "source_name": "SLEEPER WIRE"
            }
            
    print(f"✓ Ingested {sleeper_injuries_found} severe injuries & queued active camp notes!")

# 3. Source B: FFToday IDP Positional Projections (DL=50, LB=60, DB=70)
print("\n3. [SOURCE 2] Ingesting FFToday IDP Player Wire & Statuses...")
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
            print(f"⚠️ FFToday IDP notice ({pos_label}): {e}")

print(f"✓ Ingested {idp_wire_matched} FFToday IDP player profiles!")

# 4. Source C: FFToday Live News & Articles Hub
print("\n4. [SOURCE 3] Scraping FFToday News & Strategy Articles...")
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
                blocks = soup.find_all(['tr', 'p', 'div'])
                for block in blocks:
                    b_text = block.get_text(separator=" ").strip()
                    if len(b_text) < 35 or len(b_text) > 800:
                        continue
                    
                    matched_players = extract_players_fast(b_text, player_registry)
                    for full_pname in matched_players:
                        c_p = clean_name(full_pname)
                        if c_p not in scraped_intel_by_player:
                            clean_b = clean_snippet_text(b_text)
                            scraped_intel_by_player[c_p] = {
                                "player_name": full_pname,
                                "raw_text": b_text,
                                "snippet": clean_b,
                                "source_url": url,
                                "source_name": src_label
                            }
                            fftoday_matched += 1
        except Exception as e:
            print(f"⚠️ FFToday ({src_label}) notice: {e}")

print(f"✓ Extracted {fftoday_matched} live reports from FFToday!")

# 5. Source D: CBS Sports Multi-Page News Archive & Superflex Hub
print("\n5. [SOURCE 4] Scraping CBS Sports Multi-Page News Archive & Superflex Hub...")
cbs_matched = 0
if BS4_AVAILABLE:
    cbs_pages = [
        (clean_url("[https://www.cbssports.com/fantasy/football/news/2026-superflex-podcast-mock-draft-waiting-on-qb-pays-off/](https://www.cbssports.com/fantasy/football/news/2026-superflex-podcast-mock-draft-waiting-on-qb-pays-off/)"), "CBS SUPERFLEX MOCK"),
        (clean_url("[https://www.cbssports.com/fantasy/football/draft-prep/](https://www.cbssports.com/fantasy/football/draft-prep/)"), "CBS DRAFT PREP"),
        (clean_url("[https://www.cbssports.com/fantasy/football/news/](https://www.cbssports.com/fantasy/football/news/)"), "CBS NEWS"),
        (clean_url("[https://www.cbssports.com/fantasy/football/](https://www.cbssports.com/fantasy/football/)"), "CBS WIRE")
    ]
    for p_num in range(1, 9):
        cbs_pages.append((clean_url(f"[https://www.cbssports.com/fantasy/football/players/news/all/](https://www.cbssports.com/fantasy/football/players/news/all/){p_num}/"), f"CBS ARCHIVE P{p_num}"))

    for page_url, src_label in cbs_pages:
        try:
            res = requests.get(page_url, headers=web_headers, timeout=6)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                article_blocks = soup.find_all(['div', 'article', 'h2', 'h3', 'h4', 'p', 'li'])
                for art in article_blocks:
                    raw_text = art.get_text(separator=" ").strip()
                    if len(raw_text) < 35 or len(raw_text) > 750:
                        continue
                    
                    matched_players = extract_players_fast(raw_text, player_registry)
                    for full_pname in matched_players:
                        c_p = clean_name(full_pname)
                        if c_p not in scraped_intel_by_player:
                            clean_b = clean_snippet_text(raw_text)
                            scraped_intel_by_player[c_p] = {
                                "player_name": full_pname,
                                "raw_text": raw_text,
                                "snippet": clean_b,
                                "source_url": page_url,
                                "source_name": src_label
                            }
                            cbs_matched += 1
        except Exception:
            pass

print(f"✓ Extracted {cbs_matched} deep CBS Sports & Superflex mock updates across pages!")

# 6. Source E: 32BeatWriters Aggregator Feed
print("\n6. [SOURCE 5] Scraping 32BeatWriters.com Aggregator Feed...")
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

# 7. Source F: Free Multi-Source XML RSS Feeds
print("\n7. [SOURCE 6] Ingesting Non-Paywalled XML RSS Feeds...")
rss_matched = 0
rss_urls = [
    (clean_url("[https://www.rotoballer.com/feed](https://www.rotoballer.com/feed)"), "ROTOBALLER"),
    (clean_url("[https://www.fantasysp.com/rss/nfl/allplayer/](https://www.fantasysp.com/rss/nfl/allplayer/)"), "FANTASYSP"),
    (clean_url("[https://www.fantasysp.com/rss/nfl/headlines/](https://www.fantasysp.com/rss/nfl/headlines/)"), "FANTASYSP WIRE"),
    (clean_url("[https://www.fftoday.com/rss/news.xml](https://www.fftoday.com/rss/news.xml)"), "FFTODAY RSS"),
    (clean_url("[https://www.cbssports.com/rss/headlines/fantasy/football/](https://www.cbssports.com/rss/headlines/fantasy/football/)"), "CBS RSS")
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
                
                matched_players = extract_players_fast(full_body, player_registry)
                for full_pname in matched_players:
                    c_p = clean_name(full_pname)
                    if c_p not in scraped_intel_by_player:
                        scraped_intel_by_player[c_p] = {
                            "player_name": full_pname,
                            "raw_text": full_body,
                            "snippet": clean_snippet_text(full_body),
                            "source_url": clean_url(link) if link else clean_url("[https://www.rotoballer.com](https://www.rotoballer.com)"),
                            "source_name": src_tag
                        }
                        rss_matched += 1
    except Exception as e:
        print(f"⚠️ RSS Notice for {src_tag}: {e}")

print(f"✓ Ingested {rss_matched} RSS beat wire reports across free feeds!")

# 8. Source G: Sleeper 24-Hour Live Trending Waiver Adds
print("\n8. [SOURCE 7] Querying Sleeper Live 24h Waiver Surges...")
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
                    scraped_intel_by_player[c_p] = {
                        "player_name": p_name,
                        "raw_text": f"Surging on waiver wire across competitive leagues (+{add_cnt} adds in last 24 hours). Camp breakout or opportunity spike.",
                        "snippet": f"Waiver Surge (+{add_cnt} adds in 24h)",
                        "source_url": wire_link,
                        "source_name": "WAIVER SURGE"
                    }
                    trending_adds_count += 1
    print(f"✓ Matched {trending_adds_count} surging waiver additions!")
except Exception as e:
    print(f"⚠️ Sleeper Waiver Notice: {e}")

# ==============================================================================
# 9. CONCURRENT PARALLEL GROQ LLM SENTIMENT ANALYSIS (GENUINE SIGNALS ONLY)
# ==============================================================================

# Deduplicate queue strictly by verified player name (ONLY real reports)
queue_list = list(scraped_intel_by_player.values())
target_count = min(len(queue_list), 220)
print(f"\n9. Running Concurrent Parallel Groq LLM Analysis on {target_count} verified distinct player reports...")

llm_evaluated_count = 0
api_key = get_active_groq_key()
candidate_models = get_available_groq_models(api_key) if api_key else []

if queue_list and api_key:
    batch_size = 5
    batches = [queue_list[i:i + batch_size] for i in range(0, target_count, batch_size)]
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(process_single_groq_batch, batch, api_key, candidate_models) for batch in batches]
        for future in as_completed(futures):
            try:
                batch_res = future.result()
                for p_name, entry in batch_res.items():
                    # Preserve severe official IR designations
                    if p_name in camp_overrides and camp_overrides[p_name].get("type") == "INJURY" and camp_overrides[p_name].get("multiplier") <= 0.50:
                        continue
                    camp_overrides[p_name] = entry
                    llm_evaluated_count += 1
            except Exception:
                pass

print(f"✓ Groq LLM enriched {llm_evaluated_count} player profiles with tactical & Superflex insights!")

# Fallback for remaining genuine items in queue
for art in queue_list[:target_count]:
    orig_player = art["player_name"]
    if orig_player not in camp_overrides:
        src_label = art.get("source_name", "BEAT WIRE")
        camp_overrides[orig_player] = {
            "multiplier": 1.04 if "WAIVER" in src_label else 1.00,
            "type": "BREAKOUT" if "WAIVER" in src_label else ("SUPERFLEX" if "SUPERFLEX" in src_label else "BEAT"),
            "note": f"📰 {src_label}: {art['snippet']}",
            "source_url": art.get("source_url", "")
        }

# ==============================================================================
# 10. PERSIST OUTPUT TO CAMP_OVERRIDES.JSON
# ==============================================================================

with open("camp_overrides.json", "w") as f:
    json.dump(camp_overrides, f, indent=2)

print(f"\n✅ SUCCESS: Saved {len(camp_overrides)} verified multi-source overrides to 'camp_overrides.json'!")