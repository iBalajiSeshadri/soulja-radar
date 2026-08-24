import requests
import json
import re
import os

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

def clean_name(name):
    if not isinstance(name, str):
        return ""
    name = name.lower().strip()
    name = re.sub(r"[^\w\s]", "", name)
    name = re.sub(r"\b(jr|sr|iii|ii|iv|v)\b", "", name)
    return " ".join(name.split())

def clean_snippet_text(text, max_len=160):
    text = " ".join(text.split())
    text = re.sub(r"^(Rotowire|CBS Sports|Fantasy Staff|RotoBaller)\s*[:\-]\s*", "", text, flags=re.IGNORECASE)
    if len(text) > max_len:
        return text[:max_len].rsplit(' ', 1)[0] + "..."
    return text

def parse_is_fresh(time_str):
    if not time_str:
        return True
    t = time_str.lower().strip()
    if any(k in t for k in ['m ago', 'h ago', 'min', 'hour', 'today', 'yesterday']):
        return True
    day_match = re.search(r'(\d+)\s*d\b', t) or re.search(r'(\d+)\s*day', t)
    if day_match:
        return int(day_match.group(1)) <= 3
    return False

def extract_headline_subject(raw_text):
    if ':' not in raw_text:
        return None, raw_text
    
    parts = raw_text.split(':', 1)
    subject_raw = parts[0].strip()
    headline_text = parts[1].strip()
    
    # Strip team possessive prefixes (e.g. "Patriots'", "Bills'")
    subject_clean = re.sub(r"^[A-Za-z0-9\s\.\-]+\'\s*", "", subject_raw).strip()
    # Strip position/team suffixes (e.g. "Ray Davis RB | BUF")
    subject_clean = re.sub(r"\s+(QB|RB|WR|TE|K|DEF|LB|DL|DB)\s*\|.*$", "", subject_clean, flags=re.IGNORECASE).strip()
    
    return subject_clean, headline_text

print("==================================================================")
print("  SOULJA SOULJA SURGICAL SUBJECT-ISOLATED NEWS AGGREGATOR       ")
print("==================================================================")

camp_overrides = {}

# 1. Load Universal Player Registry
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

# 2. Source A: Sleeper Official Real-Time Injury Wire (Exact ID Match)
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
            if inj_body: 
                desc += f" ({inj_body})"
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

# 3. Source B: CBS Sports Stream (Surgical Subject Extraction + Direct Links)
headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
print("\n3. [SOURCE 2] Scraping CBS RotoWire Feed with Subject Isolation...")
cbs_fresh = 0
cbs_historical = 0

SEVERE_INJURY_REGEX = re.compile(r'\b(placed on ir|placed on pup|torn acl|torn achilles|out for season|suffered a knee|carted off|undergoing mri|ruled out|did not play due to injury|leaving on a cart)\b', re.IGNORECASE)
TWEAK_REGEX = re.compile(r'\b(hamstring|calf strain|ankle sprain|groin|limited in practice|questionable|game-time decision)\b', re.IGNORECASE)
CLEARANCE_REGEX = re.compile(r'\b(cleared|passed physical|off pup|removed from injury report|practicing in full|fully healthy)\b', re.IGNORECASE)

for page in range(1, 12):
    cbs_url = f"https://www.cbssports.com/fantasy/football/players/news/all/{page}/"
    try:
        res = requests.get(cbs_url, headers=headers, timeout=8)
        if res.status_code == 200 and BS4_AVAILABLE:
            soup = BeautifulSoup(res.text, 'html.parser')
            articles = soup.find_all('div', class_='tag-article') or soup.find_all('div', class_='article')
            
            for art in articles:
                raw_text = art.get_text().strip()
                if len(raw_text) < 20:
                    continue
                    
                date_tag = art.find('span', class_='article-date') or art.find('span', class_='timestamp') or art.find('time')
                time_str = date_tag.get_text().strip() if date_tag else "recent"
                is_fresh = parse_is_fresh(time_str)

                # Extract Direct Article URL if present
                link_tag = art.find('a', href=True)
                if link_tag and link_tag['href']:
                    href = link_tag['href']
                    source_link = f"https://www.cbssports.com{href}" if href.startswith('/') else href
                else:
                    source_link = "https://www.cbssports.com/fantasy/football/news/"

                # Extract Subject Player Name
                subject_candidate, headline = extract_headline_subject(raw_text)
                if not subject_candidate:
                    continue
                    
                c_sub = clean_name(subject_candidate)
                if c_sub in player_registry:
                    orig_player = player_registry[c_sub]
                    snippet = clean_snippet_text(f"{subject_candidate}: {headline}")

                    # Classification Logic
                    if SEVERE_INJURY_REGEX.search(raw_text) and is_fresh:
                        camp_overrides[orig_player] = {
                            "multiplier": 0.20,
                            "type": "INJURY",
                            "note": f"❌ CBS INTEL ({time_str}): {snippet}",
                            "source_url": source_link
                        }
                        cbs_fresh += 1
                    elif TWEAK_REGEX.search(raw_text) and is_fresh:
                        if orig_player not in camp_overrides or camp_overrides[orig_player].get("type") in ["BEAT", "HISTORICAL"]:
                            camp_overrides[orig_player] = {
                                "multiplier": 0.88,
                                "type": "QUESTIONABLE",
                                "note": f"🩹 CBS INTEL ({time_str}): {snippet}",
                                "source_url": source_link
                            }
                            cbs_fresh += 1
                    elif CLEARANCE_REGEX.search(raw_text) and is_fresh:
                        camp_overrides[orig_player] = {
                            "multiplier": 1.00,
                            "type": "HEALTHY",
                            "note": f"✅ CBS INTEL ({time_str}): {snippet}",
                            "source_url": source_link
                        }
                        cbs_fresh += 1
                    elif is_fresh:
                        if orig_player not in camp_overrides or camp_overrides[orig_player].get("type") == "HISTORICAL":
                            camp_overrides[orig_player] = {
                                "multiplier": 1.00,
                                "type": "BEAT",
                                "note": f"📰 BEAT WIRE ({time_str}): {snippet}",
                                "source_url": source_link
                            }
                            cbs_fresh += 1
                    else:
                        if orig_player not in camp_overrides:
                            camp_overrides[orig_player] = {
                                "multiplier": 1.00,
                                "type": "HISTORICAL",
                                "note": f"📰 RECENT WIRE ({time_str}): {snippet}",
                                "source_url": source_link
                            }
                            cbs_historical += 1
        else:
            break
    except Exception:
        break

print(f"✓ Processed CBS feed: {cbs_fresh} fresh subject updates & {cbs_historical} historical updates!")

# 4. Source C: Sleeper 24-Hour Live Trending Waiver Adds
print("\n4. [SOURCE 3] Querying Sleeper Live 24h Waiver Surges...")
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
                            "multiplier": 1.06,
                            "type": "BREAKOUT",
                            "note": f"🔥 WAIVER SPIKE: Surging camp pickup (+{add_cnt} adds in 24h)",
                            "source_url": wire_link
                        }
                    adds_matched += 1
    print(f"✓ Matched {adds_matched} surging waiver additions!")
except Exception as e:
    print(f"⚠️ Sleeper Notice: {e}")

with open("camp_overrides.json", "w") as f:
    json.dump(camp_overrides, f, indent=2)

print(f"\n✅ SUCCESS: Saved {len(camp_overrides)} subject-isolated overrides with source URLs to 'camp_overrides.json'!")