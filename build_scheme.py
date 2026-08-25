"""
build_scheme.py — LLM-powered coaching-scheme extractor.

Fetches the RotoGrinders 2026 team-by-team preview (one authoritative, current
source covering all 32 teams: HC/OC/DC/play-caller, scheme tendencies, and the
players who benefit) and uses Groq to turn each team's section into structured
JSON. Writes coaching_scheme.json in the exact shape app.py's
load_coaching_scheme() consumes:

  {
    "_meta": {...},
    "_defense": { "<TEAM>": {dc, scheme, idp:{player:why}, note}, ... },
    "<TEAM>":   {hc, oc, caller, scheme, beneficiaries:{player:why}, risk:{player:why}, note},
    ...
  }

Grounded extraction only — the model is told to use ONLY the section text and
never invent players. Re-runnable; one Groq call per team (~32 calls).
"""

import json
import os
import re
import sys
import time
import requests

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

ARTICLE_URL = "https://rotogrinders.com/articles/2026-nfl-team-previews-4213312"

# Local Ollama config (used when USE_OLLAMA=1 or Groq is unavailable/capped).
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

# Full team name (as it appears in the article "## " headers) -> app abbreviation.
TEAM_ABBR = {
    "Arizona Cardinals": "ARI", "Atlanta Falcons": "ATL", "Baltimore Ravens": "BAL",
    "Buffalo Bills": "BUF", "Carolina Panthers": "CAR", "Chicago Bears": "CHI",
    "Cincinnati Bengals": "CIN", "Cleveland Browns": "CLE", "Dallas Cowboys": "DAL",
    "Denver Broncos": "DEN", "Detroit Lions": "DET", "Green Bay Packers": "GB",
    "Houston Texans": "HOU", "Indianapolis Colts": "IND", "Jacksonville Jaguars": "JAC",
    "Kansas City Chiefs": "KC", "Las Vegas Raiders": "LV", "Los Angeles Chargers": "LAC",
    "Los Angeles Rams": "LAR", "Miami Dolphins": "MIA", "Minnesota Vikings": "MIN",
    "New England Patriots": "NE", "New Orleans Saints": "NO", "New York Giants": "NYG",
    "New York Jets": "NYJ", "Philadelphia Eagles": "PHI", "Pittsburgh Steelers": "PIT",
    "San Francisco 49ers": "SF", "Seattle Seahawks": "SEA", "Tampa Bay Buccaneers": "TB",
    "Tennessee Titans": "TEN", "Washington Commanders": "WAS",
}


def get_groq_key():
    try:
        import streamlit as st  # noqa
        if hasattr(st, "secrets") and "GROQ_API_KEY" in st.secrets:
            k = str(st.secrets["GROQ_API_KEY"]).strip().strip('"').strip("'")
            if k:
                return k
    except Exception:
        pass
    if os.path.exists(".streamlit/secrets.toml"):
        try:
            for line in open(".streamlit/secrets.toml"):
                if "GROQ_API_KEY" in line and "=" in line:
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
    return os.getenv("GROQ_API_KEY", "").strip().strip('"').strip("'")


def groq_models(key):
    try:
        r = requests.get("https://api.groq.com/openai/v1/models",
                         headers={"Authorization": f"Bearer {key}"}, timeout=6)
        if r.status_code == 200:
            ids = [m["id"] for m in r.json().get("data", [])]
            # Prefer 20b: it has a separate daily token budget from 120b and is
            # plenty capable for this structured extraction. 120b/qwen as fallback.
            pref = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3.6-27b"]
            ordered = [p for p in pref if p in ids]
            if ordered:
                return ordered
    except Exception:
        pass
    return ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]


def fetch_article_text():
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                             "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}
    r = requests.get(ARTICLE_URL, headers=headers, timeout=20)
    r.raise_for_status()
    if BS4_AVAILABLE:
        soup = BeautifulSoup(r.text, "html.parser")
        # main article body — get_text keeps the "## Team" structure as plain headings
        return soup.get_text("\n")
    return re.sub(r"<[^>]+>", " ", r.text)


def split_team_sections(text):
    """Return {full_team_name: section_text} by scanning for each team's name as a
    standalone heading line and slicing until the next team's heading."""
    lines = text.splitlines()
    # find the line index where each team's section starts (a line that is exactly the team name)
    starts = {}
    names = list(TEAM_ABBR.keys())
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s in names and s not in starts:
            # heuristic: a real section header is followed soon by "2025 Record" or "COACHING"
            look = "\n".join(lines[i:i + 12])
            if "Record" in look or "COACHING" in look:
                starts[s] = i
    ordered = sorted(starts.items(), key=lambda kv: kv[1])
    sections = {}
    for idx, (name, start) in enumerate(ordered):
        end = ordered[idx + 1][1] if idx + 1 < len(ordered) else len(lines)
        sections[name] = "\n".join(lines[start:end]).strip()
    return sections


SYSTEM_PROMPT = """You extract structured 2026 NFL coaching/scheme data for a fantasy app.
You are given ONE team's section from a team-preview article. Use ONLY that text.

Return a SINGLE valid JSON object (no prose, no markdown fences) with these keys:
{
  "hc": "head coach name",
  "oc": "offensive coordinator name",
  "caller": "primary offensive play-caller name",
  "dc": "defensive coordinator name",
  "off_scheme": "one concise phrase describing the offensive scheme/tendencies",
  "def_scheme": "one concise phrase describing the defensive scheme/tendencies (or '' if not described)",
  "off_changed": true/false (true ONLY if the team changed its HC, OC, or offensive play-caller for 2026 per the text; false if the text says continuity/'didn't make a change'/same staff),
  "def_changed": true/false (true ONLY if the team changed its defensive coordinator for 2026 per the text; false if the DC returns/continuity),
  "beneficiaries": { "Player Name": "one specific sentence on why this OFFENSIVE player benefits (only if the text clearly says so)" },
  "risk": { "Player Name": "one specific sentence on why this OFFENSIVE player is a risk/downgrade (only if the text clearly says so)" },
  "idp": { "Player Name": "one specific sentence on why this DEFENSIVE (IDP) player benefits (only if the text clearly says so)" },
  "note": "one short summary sentence of the fantasy takeaway"
}

RULES:
- Use ONLY names and reasoning present in the provided text. NEVER invent players, coaches, stats, or schemes.
- Offensive beneficiaries/risk = QB/RB/WR/TE only. idp = defensive players (edge/DL/LB/DB) only.
- If the text doesn't clearly support a field, use "" or {} — do not guess.
- Keep each reason to ONE concrete sentence quoting the specific detail (role, volume, scheme fit, injury).
"""


def ollama_available():
    """True if a local Ollama server responds and has the target model."""
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        if r.status_code == 200:
            names = [m.get("name", "") for m in r.json().get("models", [])]
            # match "llama3.1:8b" or bare "llama3.1"
            return any(OLLAMA_MODEL == n or OLLAMA_MODEL.split(":")[0] == n.split(":")[0]
                       for n in names)
    except Exception:
        pass
    return False


def _parse_json_blob(content):
    content = re.sub(r"```(?:json)?", "", content)
    content = re.sub(r"<think>[\s\S]*?</think>", "", content).strip()  # qwen-style
    m = re.search(r"\{[\s\S]*\}", content)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None


def extract_team_ollama(section_text, team_name):
    user = f"TEAM: {team_name}\n\nSECTION:\n{section_text[:6000]}"
    try:
        r = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "stream": False,
                "format": "json",          # ask Ollama for strict JSON
                "options": {"temperature": 0.1, "num_ctx": 8192},
                "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                             {"role": "user", "content": user}],
            },
            timeout=180,
        )
        if r.status_code == 200:
            content = r.json().get("message", {}).get("content", "")
            return _parse_json_blob(content)
    except Exception as e:
        print(f"      ollama error: {e}")
    return None


def extract_team(section_text, team_name, key, models):
    user = f"TEAM: {team_name}\n\nSECTION:\n{section_text[:6000]}"
    for model in models:
        for attempt in range(4):
            try:
                r = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json={"model": model, "temperature": 0.1, "max_tokens": 1200,
                          "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                                       {"role": "user", "content": user}]},
                    timeout=40,
                )
                if r.status_code == 200:
                    content = r.json()["choices"][0]["message"]["content"]
                    content = re.sub(r"```(?:json)?", "", content)
                    content = re.sub(r"<think>[\s\S]*?</think>", "", content).strip()  # qwen
                    m = re.search(r"\{[\s\S]*\}", content)
                    if m:
                        return json.loads(m.group(0))
                    break  # got 200 but unparseable — try next model
                elif r.status_code == 429:
                    msg = r.text
                    wait = 3.0
                    mm = re.search(r"try again in (\d+)m([\d.]+)s", msg)
                    ms = re.search(r"try again in ([\d.]+)s", msg)
                    if mm:
                        wait = int(mm.group(1)) * 60 + float(mm.group(2))
                    elif ms:
                        wait = float(ms.group(1))
                    if "per day" in msg or "TPD" in msg or wait > 45:
                        break  # daily cap on this model — fall through to next model
                    time.sleep(min(wait + 0.5, 45))
                else:
                    break
            except Exception:
                time.sleep(2)
    return None


def main():
    use_ollama = os.getenv("USE_OLLAMA", "").strip() in ("1", "true", "yes")
    key = get_groq_key()

    # Decide backend: explicit USE_OLLAMA, else Groq if key present, else Ollama.
    backend = None
    models = []
    if use_ollama:
        backend = "ollama"
    elif key:
        backend = "groq"
        models = groq_models(key)
    elif ollama_available():
        backend = "ollama"

    if backend == "ollama" and not ollama_available():
        print(f"ERROR: Ollama backend requested but server/model not reachable at "
              f"{OLLAMA_URL} (model {OLLAMA_MODEL}). Run `ollama serve` and "
              f"`ollama pull {OLLAMA_MODEL}`.")
        sys.exit(1)
    if backend is None:
        print("ERROR: no backend. Set GROQ_API_KEY, or run Ollama and set USE_OLLAMA=1.")
        sys.exit(1)

    print("1. Fetching RotoGrinders 2026 team preview...")
    text = fetch_article_text()
    sections = split_team_sections(text)
    print(f"   Split into {len(sections)} team sections.")
    if len(sections) < 20:
        print("   WARNING: found fewer sections than expected — article layout may have changed.")

    if backend == "ollama":
        print(f"2. Extracting per-team scheme via local Ollama ({OLLAMA_MODEL})...")
    else:
        print(f"2. Extracting per-team scheme via Groq ({models[0]})...")

    offense = {}
    defense = {}
    for name, section in sections.items():
        abbr = TEAM_ABBR.get(name)
        if not abbr:
            continue
        if backend == "ollama":
            data = extract_team_ollama(section, name)
        else:
            data = extract_team(section, name, key, models)
        if not data:
            print(f"   ! {abbr} ({name}): extraction failed, skipping")
            continue
        caller = data.get("caller") or data.get("oc") or ""
        offense[abbr] = {
            "hc": data.get("hc", ""),
            "oc": data.get("oc", ""),
            "caller": caller,
            "scheme": data.get("off_scheme", ""),
            "changed": bool(data.get("off_changed", False)),
            "beneficiaries": data.get("beneficiaries", {}) or {},
            "risk": data.get("risk", {}) or {},
            "note": data.get("note", ""),
        }
        defense[abbr] = {
            "dc": data.get("dc", ""),
            "scheme": data.get("def_scheme", ""),
            "changed": bool(data.get("def_changed", False)),
            "idp": data.get("idp", {}) or {},
            "note": data.get("note", ""),
        }
        nb = len(offense[abbr]["beneficiaries"])
        ni = len(defense[abbr]["idp"])
        print(f"   ✓ {abbr:3} {name:24} HC:{data.get('hc','?'):18} DC:{data.get('dc','?'):16} off+{nb} idp+{ni}")

    out = {
        "_meta": {
            "source": "RotoGrinders 2026 NFL Team-by-Team Preview (Derek Farnsworth / Notorious)",
            "source_url": ARTICLE_URL,
            "note": "LLM-extracted from a single authoritative current source. Grounded only in the article text; players/coaches not invented.",
            "generated_by": "build_scheme.py",
            "backend": (f"ollama:{OLLAMA_MODEL}" if backend == "ollama"
                        else f"groq:{models[0] if models else '?'}"),
        },
        "_defense": {**{"_src": ARTICLE_URL}, **defense},
    }
    out.update(offense)

    with open("coaching_scheme.json", "w") as f:
        json.dump(out, f, indent=2)
    print(f"\n✅ Wrote coaching_scheme.json — {len(offense)} offense teams, {len(defense)} defense teams.")


if __name__ == "__main__":
    main()
