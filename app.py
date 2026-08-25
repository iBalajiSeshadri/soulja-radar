import streamlit as st
import pandas as pd
import numpy as np
import requests
import json
import os
import re
import random
import subprocess
import sys
from llm_advisor import (
    generate_live_auction_advice, 
    generate_snake_turn_advice, 
    generate_ai_nomination, 
    ask_ai_strategist
)

# Page Configuration
st.set_page_config(
    page_title="Soulja Soulja Pro Radar",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

LEAGUE_ID = "1385816551680143360"

# Custom Styling & Badges
st.markdown("""
<style>
    .stApp { background-color: #0b0f19; color: #e2e8f0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    div[data-testid="stMetricValue"] { font-size: 1.6rem; color: #10b981; font-weight: 700; }
    div[data-testid="stMetricLabel"] { color: #94a3b8; font-size: 0.85rem; }
    .cliff-card { background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border-left: 4px solid #10b981; padding: 12px; border-radius: 6px; }
    .cliff-alert { border-left: 4px solid #ef4444 !important; }
    .landmine-tag { background-color: #ef444420; color: #f87171; padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 0.75rem; border: 1px solid #ef444440; }
    
    .t-last { padding: 2px 6px; border-radius: 4px; font-weight: 800; font-size: 0.72rem; letter-spacing: 0.5px; }
    .t-last-t1 { background-color: #dc2626; color: white; border: 1px solid #f87171; box-shadow: 0 0 8px #dc262660; }
    .t-last-t2 { background-color: #ea580c; color: white; border: 1px solid #fb923c; }
    .t-last-t3 { background-color: #d97706; color: white; border: 1px solid #fcd34d; }
    .t-last-t4 { background-color: #475569; color: #f1f5f9; border: 1px solid #94a3b8; }
    .t-last-t5 { background-color: #334155; color: #cbd5e1; border: 1px solid #64748b; }
    
    .pref-target { background-color: #10b98130; color: #34d399; padding: 2px 6px; border-radius: 4px; font-weight: 800; font-size: 0.75rem; border: 1px solid #10b981; margin-right: 4px; }
    .pref-fade { background-color: #64748b30; color: #94a3b8; padding: 2px 6px; border-radius: 4px; font-weight: 800; font-size: 0.75rem; border: 1px solid #64748b; margin-right: 4px; }

    .intel-tier-jumper { background-color: #10b98135; color: #34d399; padding: 2px 6px; border-radius: 4px; font-weight: 800; font-size: 0.75rem; border: 1px solid #10b981; }
    .intel-superflex { background-color: #8b5cf635; color: #c084fc; padding: 2px 6px; border-radius: 4px; font-weight: 800; font-size: 0.75rem; border: 1px solid #8b5cf6; }
    .intel-core-anchor { background-color: #f59e0b35; color: #fbbf24; padding: 2px 6px; border-radius: 4px; font-weight: 800; font-size: 0.75rem; border: 1px solid #f59e0b; }
    .intel-value-target { background-color: #06b6d435; color: #22d3ee; padding: 2px 6px; border-radius: 4px; font-weight: 800; font-size: 0.75rem; border: 1px solid #06b6d4; }
    .intel-role-pinch { background-color: #ea580c35; color: #fb923c; padding: 2px 6px; border-radius: 4px; font-weight: 800; font-size: 0.75rem; border: 1px solid #ea580c; }
    .intel-vet-rest { background-color: #3b82f635; color: #93c5fd; padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 0.75rem; border: 1px solid #3b82f6; }
    .intel-healthy { background-color: #10b98125; color: #34d399; padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 0.75rem; border: 1px solid #10b98160; }
    .intel-beat { background-color: #3b82f625; color: #93c5fd; padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 0.75rem; border: 1px solid #3b82f660; }
    .intel-bust { background-color: #ef444430; color: #f87171; padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 0.75rem; border: 1px solid #ef444460; }
    .intel-injury { background-color: #dc262640; color: #fca5a5; padding: 2px 6px; border-radius: 4px; font-weight: 800; font-size: 0.75rem; border: 1px solid #dc2626; }
    .intel-surge { background-color: #f59e0b30; color: #fbbf24; padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 0.75rem; border: 1px solid #f59e0b60; }
    .source-link { color: #60a5fa; text-decoration: none; font-weight: 700; font-size: 0.72rem; border: 1px solid #3b82f660; padding: 1px 6px; border-radius: 3px; background: #3b82f615; margin-left: 6px; display: inline-block; }
    .source-link:hover { background: #3b82f630; color: #93c5fd; }

    /* Crunched news insight text in the intel column */
    .intel-note { color: #e5e7eb; font-size: 0.82rem; line-height: 1.25; }
    .intel-note-hot { color: #fde68a; font-weight: 700; font-size: 0.82rem; line-height: 1.25; }
    /* 2026 coaching-change scheme-fit badges */
    .intel-scheme-fit { background-color: #7c3aed35; color: #c4b5fd; padding: 2px 6px; border-radius: 4px; font-weight: 800; font-size: 0.72rem; border: 1px solid #7c3aed; }
    .intel-scheme-risk { background-color: #b4530935; color: #fdba74; padding: 2px 6px; border-radius: 4px; font-weight: 800; font-size: 0.72rem; border: 1px solid #ea580c; }
    .intel-scheme-new { background-color: #37415535; color: #cbd5e1; padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 0.72rem; border: 1px solid #475569; }
    /* Defensive-coordinator scheme badges (IDP / D-ST) */
    .intel-def-fit { background-color: #0e766535; color: #5eead4; padding: 2px 6px; border-radius: 4px; font-weight: 800; font-size: 0.72rem; border: 1px solid #0d9488; }
    .intel-def-new { background-color: #1e3a5f35; color: #93c5fd; padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 0.72rem; border: 1px solid #1d4ed8; }
    /* D/ST opening-slate streamer badges (Wks 1-4 schedule + DC change) */
    .intel-dst-soft { background-color: #15803d35; color: #86efac; padding: 2px 6px; border-radius: 4px; font-weight: 800; font-size: 0.72rem; border: 1px solid #16a34a; }
    .intel-dst { background-color: #37415535; color: #cbd5e1; padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 0.72rem; border: 1px solid #475569; }

    .arch-badge { padding: 3px 8px; border-radius: 4px; font-weight: 700; font-size: 0.75rem; }
    .arch-stars { background: #dc262625; color: #f87171; border: 1px solid #ef444460; }
    .arch-hoard { background: #10b98125; color: #34d399; border: 1px solid #10b98160; }
    .arch-balanced { background: #3b82f625; color: #60a5fa; border: 1px solid #3b82f660; }
    .arch-idp { background: #8b5cf625; color: #c084fc; border: 1px solid #8b5cf660; }

    .badge-pos { font-weight: 700; padding: 2px 6px; border-radius: 4px; font-size: 0.75rem; }
    .pos-QB { background: #3b82f630; color: #60a5fa; border: 1px solid #3b82f660; }
    .pos-RB { background: #10b98130; color: #34d399; border: 1px solid #10b98160; }
    .pos-WR { background: #f59e0b30; color: #fbbf24; border: 1px solid #f59e0b60; }
    .pos-TE { background: #8b5cf630; color: #a78bfa; border: 1px solid #8b5cf660; }
    .pos-LB { background: #06b6d430; color: #22d3ee; border: 1px solid #06b6d460; }
    .pos-DL { background: #f43f5e30; color: #fb7185; border: 1px solid #f43f5e60; }
    .pos-DB { background: #a855f730; color: #c084fc; border: 1px solid #a855f760; }
    .pos-DEF { background: #ec489930; color: #f472b6; border: 1px solid #ec489960; }
</style>
""", unsafe_allow_html=True)

# 🌟 DEFAULT HISTORICAL LEAGUE CREW
SOULJA_SOULJA_DEFAULTS = {
    1: {"handle": "addyrao", "name": "Addy Rao", "archetype": "🐢 Patient Value Shark", "class": "arch-hoard", "bias": "$119 Top-3 Spend | Late Monopolist", "exploit": "Holds budget until mid-round deflation; surged to 2025 #3 finish with league-high 2,537 pts. Nominate his starting targets early to force spend."},
    2: {"handle": "skongara", "name": "Shantanu", "archetype": "👑 Stud Anchor + Value Weapons", "class": "arch-stars", "bias": "$107.5 Top-3 Spend | 2025 Champion", "exploit": "2025 champion (73.2% win rate, 2,443.4 avg pts). Secures 1 stud at ~$50, then dominates the $25-$33 tier. Push his secondary targets to full fair value."},
    3: {"handle": "bluewatermelon", "name": "Bluewatermelon", "archetype": "🛡️ Top-Heavy / Depth Starved", "class": "arch-idp", "bias": "$126.5 Top-3 Spend | Rebuild Floor", "exploit": "Spends $102-$136 on 3 stars, starving bench depth ($2,163.7 pts). Secure deflated Tier 1/2 players while he sits on empty cap."},
    4: {"handle": "DjBallz", "name": "Balaji (You)", "archetype": "👑 Disciplined Anchor (VORP Surplus)", "class": "arch-stars", "bias": "$122 Top-3 Spend | 2024 Final Four", "exploit": "1 Stud Anchor + disciplined surplus spread and IDP value snipes; avoids emotional bidding wars."},
    5: {"handle": "vnayini", "name": "Vivek", "archetype": "⚖️ Mid-Tier Value Optimizer", "class": "arch-balanced", "bias": "$112 Top-3 Spend | Playoff Lock", "exploit": "Constructs high-floor rosters in $32-$42 range with zero $50+ studs (2025 #4, 2024 #5). Nominate his key positions early to disrupt planned values."},
    6: {"handle": "Kopite", "name": "Kopite", "archetype": "🔥 Extreme Stud Triple-Dipper", "class": "arch-stars", "bias": "$155.5 Top-3 Spend (77.8% of Cap)", "exploit": "2025 runner-up (66.1% win rate, 2,428.2 avg pts). Spent $163 on Saquon ($56), Allen ($55), Chase ($52) in '25. Force him to pay full retail on his 2nd/3rd stud."},
    7: {"handle": "chaituat", "name": "Chaitu", "archetype": "💥 High-Spend Aggressor", "class": "arch-stars", "bias": "$133 Flat Top-3 Spend | High Volatility", "exploit": "Spends exactly $133 on 3 stars every year ($98 on dual QBs in '24). Nominate high-cost non-targets early to burn his capital quickly."},
    8: {"handle": "cardinalsin", "name": "Harsha", "archetype": "🛡️ Dual-RB Anchor + Elite IDP", "class": "arch-idp", "bias": "$125.5 Top-3 Spend | 2024 Runner-Up", "exploit": "Spent $106 on Bijan/Breece in '24 + heavy IDP/TE budget. Reached 2024 finals (#2). Nominate top LBs/TEs early to burn offensive cap."},
    9: {"handle": "rookieqbme", "name": "Siddanth", "archetype": "🥷 Post-Cliff Value Sniper", "class": "arch-hoard", "bias": "$104 Top-3 Spend | 2025 Top 5", "exploit": "Waits out the initial stud spike to grab post-cliff bargains ($24-$29 range). Trigger positional runs to force him into suboptimal reaches."},
    10: {"handle": "siddharthasagar", "name": "Siddu", "archetype": "👑 High-Ceiling Value Builder", "class": "arch-stars", "bias": "$89.5 Top-3 Spend | 2024 Champion", "exploit": "Won 2024 Championship on $74 top-3 spend + elite IDP depth ($2,439.5 avg pts). Bait with overvalued landmines; avoid bidding wars on his target anchors."}
}

def clean_name(name):
    if not isinstance(name, str):
        return ""
    name = name.lower().strip()
    name = re.sub(r"[^\w\s]", "", name)
    name = re.sub(r"\b(jr|sr|iii|ii|iv|v)\b", "", name)
    name = " ".join(name.split())
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

# 1. State Initialization
if "drafted_picks" not in st.session_state:
    st.session_state.drafted_picks = {}
if "my_targets" not in st.session_state:
    st.session_state.my_targets = set()
if "my_fades" not in st.session_state:
    st.session_state.my_fades = set()
if "last_ai_read" not in st.session_state:
    st.session_state.last_ai_read = ""
if "last_ai_nom" not in st.session_state:
    st.session_state.last_ai_nom = ""

# 2. Data Loading Engine
@st.cache_data(ttl=10)
def load_draft_board():
    board_file = "top_150_draft_board.csv"
    if not os.path.exists(board_file):
        st.error(f"Missing '{board_file}'. Run fantasy_engine.py first!")
        st.stop()
    df = pd.read_csv(board_file)
    df.columns = [c.lower() for c in df.columns]
    if 'player_name' not in df.columns and 'player' in df.columns:
        df['player_name'] = df['player']
    if 'custom_rank' not in df.columns and 'rank' in df.columns:
        df['custom_rank'] = df['rank']
    df['clean_name'] = df['player_name'].apply(clean_name)
    df['vorp'] = pd.to_numeric(df['vorp'], errors='coerce').fillna(0.0)
    df['custom_rank'] = pd.to_numeric(df['custom_rank'], errors='coerce').fillna(999)
    df['tier'] = df['tier'].astype(str)
    
    if 'adp' in df.columns:
        df['market_adp'] = pd.to_numeric(df['adp'], errors='coerce').fillna(df['custom_rank'])
    else:
        df['market_adp'] = df['custom_rank']
        
    return df

@st.cache_data(ttl=5)
def load_camp_overrides():
    if os.path.exists("camp_overrides.json"):
        try:
            with open("camp_overrides.json", "r") as f:
                raw_data = json.load(f)
                return {clean_name(k): v for k, v in raw_data.items()}
        except Exception:
            return {}
    return {}

df_board = load_draft_board()
clean_overrides = load_camp_overrides()

@st.cache_data(ttl=300)
def load_coaching_scheme():
    """Real 2026 coaching-change scheme data (sourced from DraftSharks). Maps a
    player's clean-name -> scheme fit note + tag when their team changed
    HC/OC/play-caller for 2026, so the board can show scheme-fit badges."""
    if not os.path.exists("coaching_scheme.json"):
        return {}, {}
    try:
        with open("coaching_scheme.json") as f:
            raw = json.load(f)
    except Exception:
        return {}, {}
    player_map = {}   # clean_name -> {"tag","note","team"}
    team_map = {}     # TEAM -> team-level scheme summary
    def_map = {}      # TEAM -> new-DC defensive scheme summary (for D/ST rows)
    for team, info in raw.items():
        if team.startswith("_"):
            continue
        caller = info.get("caller", info.get("oc", ""))
        scheme = info.get("scheme", "")
        # Only advertise a team-level "NEW SCHEME" badge when the play-caller
        # actually changed for 2026 (continuity teams still get player-level fits).
        if info.get("changed", True):
            team_map[team] = {
                "caller": caller, "scheme": scheme,
                "summary": f"New play-caller {caller} — {scheme}. {info.get('note','')}".strip()
            }
        for pname, why in (info.get("beneficiaries") or {}).items():
            player_map[clean_name(pname)] = {
                "tag": "SCHEME_FIT", "team": team,
                "note": f"🎬 SCHEME FIT ({caller}): {why}"
            }
        for pname, why in (info.get("risk") or {}).items():
            player_map[clean_name(pname)] = {
                "tag": "SCHEME_RISK", "team": team,
                "note": f"🎬 SCHEME RISK ({caller}): {why}"
            }

    # Defensive-coordinator changes: IDP beneficiaries + team D/ST scheme summary
    for team, dinfo in (raw.get("_defense") or {}).items():
        if team.startswith("_"):
            continue
        dc = dinfo.get("dc", "")
        dscheme = dinfo.get("scheme", "")
        # Only show a team-level "NEW DC" D/ST badge when the DC actually changed.
        if dinfo.get("changed", True):
            def_map[team] = {
                "dc": dc, "scheme": dscheme,
                "summary": f"New DC {dc} — {dscheme}. {dinfo.get('note','')}".strip()
            }
        for pname, why in (dinfo.get("idp") or {}).items():
            # don't overwrite an offensive fit if a name collides
            if clean_name(pname) not in player_map:
                player_map[clean_name(pname)] = {
                    "tag": "DEF_SCHEME_FIT", "team": team,
                    "note": f"🛡️ DEF SCHEME FIT ({dc}): {why}"
                }
    return player_map, team_map, def_map

scheme_players, scheme_teams, scheme_defense = load_coaching_scheme()

@st.cache_data(show_spinner=False)
def load_dst_streamers():
    """Opening-slate (Wks 1-4) streaming-DST reads fused with DC-change context.
    Maps TEAM -> {note, soft_open, avg_opp_ppg}. Static data, safe pre-draft."""
    if not os.path.exists("dst_streamers.json"):
        return {}
    try:
        raw = json.load(open("dst_streamers.json"))
    except Exception:
        return {}
    return {t: v for t, v in raw.items() if not t.startswith("_")}

dst_streamers = load_dst_streamers()

@st.cache_data(show_spinner=False)
def load_market_curves():
    """Per-position auction $ curves fitted to the league's own 2024-25 history
    (captures SF QB premium, TE cliff, RB depth). Maps pos -> {a,b,c,points}."""
    if not os.path.exists("market_curves.json"):
        return {}
    try:
        raw = json.load(open("market_curves.json"))
    except Exception:
        return {}
    return {p: v for p, v in raw.items() if not p.startswith("_")}

market_curves = load_market_curves()

def league_market_cost(position, pos_rank):
    """Predicted winning bid from league history for a player at positional rank.
    Falls back to None when no fitted curve exists for that position."""
    cv = market_curves.get(position)
    if not cv:
        return None
    a, b, c = cv.get("a", 0), cv.get("b", 0), cv.get("c", 0)
    # Prefer the empirical point for very top ranks (avoids exp overshoot at r1-2),
    # else use the fitted curve.
    pts = cv.get("points", {})
    key = str(int(pos_rank))
    if key in pts and pos_rank <= 2:
        return max(1, int(round(pts[key])))
    val = a * np.exp(-b * float(pos_rank)) + c
    return max(1, int(round(val)))

# 3. Sidebar Controls & League Customizer
st.sidebar.title("⚡ Soulja Soulja Radar")

if st.sidebar.button("🚀 Pull Latest News & Sync Wire", use_container_width=True, type="primary"):
    with st.spinner("Scraping live beat wires, Superflex mock drafts, and crunching news via LLM..."):
        # Pass the Groq key (and full env) into the child processes so the LLM
        # actually runs on Streamlit Cloud, where there is no secrets.toml file.
        child_env = os.environ.copy()
        groq_key = ""
        try:
            if hasattr(st, "secrets") and "GROQ_API_KEY" in st.secrets:
                groq_key = str(st.secrets["GROQ_API_KEY"]).strip()
        except Exception:
            pass
        if groq_key:
            child_env["GROQ_API_KEY"] = groq_key

        if not groq_key:
            st.sidebar.warning("No GROQ_API_KEY found in Streamlit secrets — news will sync but the "
                               "AI 'crunchy' insights will be skipped. Add GROQ_API_KEY in app Settings → Secrets.")

        news_res = subprocess.run([sys.executable, "sync_fantasy_news.py"],
                                  capture_output=True, text=True, env=child_env, timeout=600)
        eng_res = subprocess.run([sys.executable, "fantasy_engine.py"],
                                 capture_output=True, text=True, env=child_env, timeout=600)
        st.cache_data.clear()

        # Report what actually happened instead of swallowing it.
        try:
            with open("camp_overrides.json") as _f:
                _n = len(json.load(_f))
        except Exception:
            _n = 0
        llm_line = next((l for l in news_res.stdout.splitlines() if "Groq LLM enriched" in l), "")
        san_line = next((l for l in news_res.stdout.splitlines() if "Sanitized overrides" in l), "")

        if news_res.returncode != 0:
            st.sidebar.error("News sync hit an error:")
            st.sidebar.code((news_res.stderr or news_res.stdout)[-1500:])
        elif eng_res.returncode != 0:
            st.sidebar.error("Board rebuild hit an error:")
            st.sidebar.code((eng_res.stderr or eng_res.stdout)[-1500:])
        else:
            st.toast(f"✅ Synced — {_n} intel entries loaded.", icon="🔥")
            if llm_line:
                st.sidebar.success(llm_line.strip())
            if san_line:
                st.sidebar.caption(san_line.strip())
        st.rerun()

draft_mode = st.sidebar.radio("Draft Format:", ["🔨 Auction / Salary Cap", "🐍 Snake Draft"], horizontal=True)

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ League Format Controls")
qb_format = st.sidebar.radio("QB Roster Format:", ["⚡ Superflex / 2-QB", "🏈 Standard 1-QB"], horizontal=True)
idp_mode = st.sidebar.radio("Defensive Format:", ["🛡️ Offense + IDP (Soulja)", "⚔️ Offense Only (Standard)"], horizontal=True)
include_idp = (idp_mode == "🛡️ Offense + IDP (Soulja)")

league_size = st.sidebar.number_input("League Teams:", min_value=8, max_value=16, value=10)
total_roster_slots = 18 if include_idp else 16

if "custom_manager_names" not in st.session_state:
    st.session_state.custom_manager_names = {s: p["name"] for s, p in SOULJA_SOULJA_DEFAULTS.items()}

with st.sidebar.expander("👥 League Managers", expanded=False):
    for i in range(1, league_size + 1):
        def_name = st.session_state.custom_manager_names.get(i, SOULJA_SOULJA_DEFAULTS.get(i, {}).get("name", f"Team {i}"))
        new_n = st.text_input(f"Slot #{i} Manager:", value=def_name, key=f"mgr_slot_input_{i}")
        st.session_state.custom_manager_names[i] = new_n

my_slot = st.sidebar.number_input(
    "Your Draft Slot / Team #", 
    min_value=1, 
    max_value=league_size, 
    value=4 if league_size >= 4 else 1,
    format="%d"
)
my_manager_display = st.session_state.custom_manager_names.get(my_slot, f"Team {my_slot}")
st.sidebar.caption(f"Drafting as: **{my_manager_display}** (Slot {my_slot})")

room_mode = st.sidebar.radio("Connection Mode:", ["🎮 Mock Sim Sandbox", "🌐 Live Sleeper Room Sync"], horizontal=True)

# 4. Dynamic VORP & Multi-Source Override Binding
df_board['live_multiplier'] = 1.0
df_board['intel_note'] = ""
df_board['intel_tag'] = ""
df_board['source_url'] = ""
df_board['scheme_note'] = ""
df_board['scheme_tag'] = ""

if not include_idp:
    df_board = df_board[~df_board['position'].isin(['LB', 'DL', 'DB'])].copy().reset_index(drop=True)

for idx, row in df_board.iterrows():
    c_p = row['clean_name']
    matched_data = clean_overrides.get(c_p)
    if not matched_data:
        p_tokens = set(c_p.split())
        for o_name, o_data in clean_overrides.items():
            o_tokens = set(o_name.split())
            if len(p_tokens & o_tokens) >= 2 or (len(p_tokens) == 1 and p_tokens == o_tokens):
                matched_data = o_data
                break
                
    if matched_data:
        df_board.at[idx, 'live_multiplier'] = matched_data.get('multiplier', 1.0)
        df_board.at[idx, 'intel_note'] = matched_data.get('note', '')
        df_board.at[idx, 'intel_tag'] = matched_data.get('type', '')
        df_board.at[idx, 'source_url'] = matched_data.get('source_url', '')

    # 2026 coaching-change scheme fit (real, sourced data)
    sch = scheme_players.get(c_p)
    if sch:
        df_board.at[idx, 'scheme_note'] = sch['note']
        df_board.at[idx, 'scheme_tag'] = sch['tag']
    elif row.get('position') == 'DEF' and row.get('team') in dst_streamers:
        # Prefer the richer opening-slate streamer read (already folds in DC change).
        stn = dst_streamers[row['team']]['streamer_note']
        df_board.at[idx, 'scheme_note'] = stn
        df_board.at[idx, 'scheme_tag'] = (
            "DST_STREAM_SOFT" if dst_streamers[row['team']]['soft_open'] else "DST_STREAM"
        )
    elif row.get('position') == 'DEF' and row.get('team') in scheme_defense:
        df_board.at[idx, 'scheme_note'] = f"🛡️ NEW DC: {scheme_defense[row['team']]['summary']}"
        df_board.at[idx, 'scheme_tag'] = "DEF_SCHEME_NEW"
    elif row.get('position') in ('LB', 'DL', 'DB') and row.get('team') in scheme_defense:
        df_board.at[idx, 'scheme_note'] = f"🛡️ NEW DC: {scheme_defense[row['team']]['summary']}"
        df_board.at[idx, 'scheme_tag'] = "DEF_SCHEME_NEW"
    elif row.get('team') in scheme_teams:
        # offensive team changed coaches but this player isn't a named beneficiary/risk
        df_board.at[idx, 'scheme_note'] = f"🎬 NEW SCHEME: {scheme_teams[row['team']]['summary']}"
        df_board.at[idx, 'scheme_tag'] = "SCHEME_NEW"

# ── DYNAMIC REPLACEMENT-LEVEL VORP (live scarcity / supply-demand) ────────────
# Static VORP freezes replacement level at draft start (e.g. QB26). As players
# come off the board, the REAL replacement level shifts — after a positional run,
# the next startable player at that position is scarcer and worth more. We
# recompute each position's replacement point over the players still available,
# so live_vorp reflects current supply. Early in the draft (few picks in) this
# barely moves; after runs it re-prices scarcity correctly. Works for both
# auction and snake (it's a pure supply signal, format-agnostic).
_picked_now = set(st.session_state.get("drafted_picks", {}).keys())
df_board['dyn_vorp'] = df_board['vorp']
# Replacement level anchored to REALISTIC league-wide starter demand (the marginal
# startable player), not the deep hoarding baseline (QB26). In a 10-team Superflex
# league ~20 QBs start, so the 20th-best QB is replacement — this fixes the static
# config that under-priced QB scarcity. Computed over the full position pool
# (proper VORP); live run/scarcity signals are layered separately (run detector).
_qb_slots = 2 if qb_format == "⚡ Superflex / 2-QB" else 1
_per_team = {'QB': _qb_slots, 'RB': 4, 'WR': 4, 'TE': 2, 'LB': 2, 'DL': 1, 'DB': 2, 'DEF': 1}
for _pos, _slots in _per_team.items():
    _pm = df_board['position'] == _pos
    if not _pm.any():
        continue
    _demand = max(1, int(_slots * league_size))          # league-wide startable count
    _pool = df_board[_pm].sort_values('proj_fpts', ascending=False)
    _repl_idx = min(_demand - 1, len(_pool) - 1)
    _repl_val = float(_pool.iloc[_repl_idx]['proj_fpts'])
    df_board.loc[_pm, 'dyn_vorp'] = df_board.loc[_pm, 'proj_fpts'] - _repl_val

# Scalable VORP Adjuster  (now built on dynamic replacement level)
if qb_format == "🏈 Standard 1-QB":
    qb_mask = df_board['position'] == 'QB'
    df_board.loc[qb_mask, 'live_vorp'] = (df_board.loc[qb_mask, 'dyn_vorp'] * 0.40) * df_board.loc[qb_mask, 'live_multiplier']
    non_qb_mask = df_board['position'] != 'QB'
    df_board.loc[non_qb_mask, 'live_vorp'] = df_board.loc[non_qb_mask, 'dyn_vorp'] * df_board.loc[non_qb_mask, 'live_multiplier']
else:
    df_board['live_vorp'] = df_board['dyn_vorp'] * df_board['live_multiplier']

# Positional Valuation Math
df_board['fair_value'] = 0.0
df_board['market_cost'] = 1
off_mask = df_board['position'].isin(['QB', 'RB', 'WR', 'TE'])
pos_off_vorp = df_board.loc[off_mask, 'live_vorp'].clip(lower=0).sum()
df_board.loc[off_mask, 'fair_value'] = (df_board.loc[off_mask, 'live_vorp'].clip(lower=0) / max(1.0, pos_off_vorp)) * (180 * league_size * 0.75)
df_board.loc[off_mask, 'fair_value'] = df_board.loc[off_mask, 'fair_value'].apply(lambda x: max(1, int(round(float(x)))))
# market_cost: prefer league-history-calibrated per-position curve (captures SF QB
# premium + TE cliff), fall back to the generic exp curve where no fit exists.
for _p in ['QB', 'RB', 'WR', 'TE']:
    _pmask = df_board['position'] == _p
    if not _pmask.any():
        continue
    _ranked = df_board[_pmask].sort_values('proj_fpts', ascending=False)
    for _i, (_idx, _r) in enumerate(_ranked.iterrows(), start=1):
        _mc = league_market_cost(_p, _i)
        if _mc is None:
            _mc = max(1, int(round(64 * np.exp(-0.028 * float(_r['custom_rank'])))))
        df_board.at[_idx, 'market_cost'] = _mc

if include_idp:
    idp_mask = df_board['position'].isin(['LB', 'DL', 'DB'])
    pos_idp_vorp = df_board.loc[idp_mask, 'live_vorp'].clip(lower=0).sum()
    df_board.loc[idp_mask, 'fair_value'] = (df_board.loc[idp_mask, 'live_vorp'].clip(lower=0) / max(1.0, pos_idp_vorp)) * (16 * league_size * 0.70)
    df_board.loc[idp_mask, 'fair_value'] = df_board.loc[idp_mask, 'fair_value'].apply(lambda x: min(6, max(1, int(round(float(x))))))
    idp_ranks = df_board[idp_mask].sort_values(by='live_vorp', ascending=False).reset_index()
    idp_cost_map = {}
    for i, r in idp_ranks.iterrows():
        cost = 5 if i < 3 else (3 if i < 8 else (2 if i < 16 else 1))
        idp_cost_map[r['clean_name']] = cost
    df_board.loc[idp_mask, 'market_cost'] = df_board.loc[idp_mask, 'clean_name'].map(idp_cost_map).fillna(1).astype(int)

def_mask = df_board['position'] == 'DEF'
pos_def_vorp = df_board.loc[def_mask, 'live_vorp'].clip(lower=0).sum()
df_board.loc[def_mask, 'fair_value'] = (df_board.loc[def_mask, 'live_vorp'].clip(lower=0) / max(1.0, pos_def_vorp)) * (4 * league_size * 0.70)
df_board.loc[def_mask, 'fair_value'] = df_board.loc[def_mask, 'fair_value'].apply(lambda x: min(3, max(1, int(round(float(x))))))
def_ranks = df_board[def_mask].sort_values(by='live_vorp', ascending=False).reset_index()
def_cost_map = {}
for i, r in def_ranks.iterrows():
    cost = 3 if i < 2 else (2 if i < 6 else 1)
    def_cost_map[r['clean_name']] = cost
df_board.loc[def_mask, 'market_cost'] = df_board.loc[def_mask, 'clean_name'].map(def_cost_map).fillna(1).astype(int)

# ── LIVE AUCTION INFLATION (apply to fair_value) ──────────────────────────────
# Static fair_value above assumes the full budget is spent at par. As the room
# over/under-pays, real dollars-per-VORP shift. Inflation index = remaining
# leaguewide cash / remaining fair-value on UNPICKED players. >1 => money left
# chasing fewer players (bid up); <1 => bargains ahead. We scale each unpicked
# player's fair_value by it so the number you see is what they're worth RIGHT NOW.
# Auction-only: snake mode ignores dollars entirely.
df_board['fair_value_base'] = df_board['fair_value']   # keep par value for reference
if draft_mode == "🔨 Auction / Salary Cap":
    _picked = set(st.session_state.get("drafted_picks", {}).keys())
    _spent = sum(float(v.get("price", 0)) for v in st.session_state.get("drafted_picks", {}).values())
    _remaining_cash = max(1.0, (league_size * 200) - _spent)
    _unpicked_mask = ~df_board['clean_name'].isin(_picked)
    _remaining_fair = float(df_board.loc[_unpicked_mask, 'fair_value'].clip(lower=1).sum())
    # Normalize so the index reads ~1.0 at draft start (par), then drifts as the
    # room's actual spend deviates from fair value. We anchor to the FULL board's
    # par fair-value vs full cash, so the pool-size constant doesn't bias it.
    _total_par_fair = float(df_board['fair_value'].clip(lower=1).sum())
    _total_cash = float(league_size * 200)
    _par_ratio = _total_cash / max(1.0, _total_par_fair)     # dollars per fair-$ at par
    _live_ratio = _remaining_cash / max(1.0, _remaining_fair)
    _infl = _live_ratio / max(0.01, _par_ratio)              # 1.0 at start by construction
    _infl = float(min(1.6, max(0.6, _infl)))                 # clamp to sane band
    df_board['live_inflation'] = _infl
    df_board.loc[_unpicked_mask, 'fair_value'] = df_board.loc[_unpicked_mask, 'fair_value'] * _infl
else:
    df_board['live_inflation'] = 1.0

df_board['fair_value'] = df_board['fair_value'].fillna(1).astype(int)
df_board['market_cost'] = df_board['market_cost'].fillna(1).astype(int)
df_board = df_board.sort_values(by=['fair_value', 'live_vorp'], ascending=[False, False]).reset_index(drop=True)
df_board['board_rank'] = df_board.index + 1

player_pos_map = dict(zip(df_board['clean_name'], df_board['position']))
player_display_map = dict(zip(df_board['clean_name'], df_board['player_name']))

# Robust HTML Badge Formatter
def format_intel_cell(r):
    pref_badge = ""
    c_n = r['clean_name']
    if c_n in st.session_state.my_targets:
        pref_badge = '<span class="pref-target">⭐ TARGET</span> '
    elif c_n in st.session_state.my_fades:
        pref_badge = '<span class="pref-fade">🚫 FADE</span> '

    tag = str(r.get('intel_tag', '')).upper()
    note = str(r.get('intel_note', '')).strip()
    tag_badge = ""

    if "TIER_JUMPER" in tag:
        tag_badge = '<span class="intel-tier-jumper">🚀 TIER JUMPER</span> '
    elif "SUPERFLEX" in tag:
        tag_badge = '<span class="intel-superflex">⚡ SUPERFLEX</span> '
    elif "CORE_ANCHOR" in tag or "STUD" in tag:
        tag_badge = '<span class="intel-core-anchor">👑 CORE ANCHOR</span> '
    elif "VALUE_TARGET" in tag or "BREAKOUT" in tag:
        tag_badge = '<span class="intel-value-target">🎯 VALUE TARGET</span> '
    elif "ROLE_PINCH" in tag:
        tag_badge = '<span class="intel-role-pinch">📉 ROLE PINCH</span> '
    elif "VET_MAINTENANCE" in tag or "VET_REST" in tag:
        tag_badge = '<span class="intel-vet-rest">🩹 VET REST</span> '
    elif "INJURY" in tag or "IR" in note or "PUP" in note:
        tag_badge = '<span class="intel-injury">❌ INJURY ALERT</span> '
    elif "QUESTIONABLE" in tag or "Questionable" in note:
        tag_badge = '<span class="intel-bust">🩹 QUESTIONABLE</span> '
    elif "CLEARED" in tag or "CLEARED" in note:
        tag_badge = '<span class="intel-healthy">✅ CLEARED</span> '
    elif "WAIVER" in tag or "SURGE" in tag or "SURGE" in note:
        tag_badge = '<span class="intel-surge">🔥 WAIVER SPIKE</span> '
    elif tag:
        tag_badge = f'<span class="intel-beat">📰 {tag}</span> '

    url = str(r.get('source_url', '')).strip()
    link_html = f' <a href="{url}" target="_blank" class="source-link">🔗 Read Source</a>' if url and url.startswith("http") else ''

    # The crunched insight is the star of the intel column. Render it prominently
    # (bold, in its own span) so genuine reads like "caught 10/12, beat the DB"
    # read clearly instead of getting lost next to the badge.
    note_html = ""
    if note and note not in ("—", "-"):
        is_positive = any(k in tag for k in ("TIER_JUMPER", "SUPERFLEX", "CORE_ANCHOR", "STUD", "VALUE", "BREAKOUT", "CLEARED", "WAIVER", "SURGE"))
        note_class = "intel-note-hot" if is_positive else "intel-note"
        note_html = f'<span class="{note_class}">{note}</span>'

    # 2026 coaching-change scheme-fit badge + note (real sourced data)
    scheme_tag = str(r.get('scheme_tag', '')).upper()
    scheme_note = str(r.get('scheme_note', '')).strip()
    scheme_html = ""
    if scheme_tag == "SCHEME_FIT":
        scheme_html = f'<span class="intel-scheme-fit">🎬 SCHEME FIT</span> <span class="intel-note-hot">{scheme_note}</span>'
    elif scheme_tag == "SCHEME_RISK":
        scheme_html = f'<span class="intel-scheme-risk">🎬 SCHEME RISK</span> <span class="intel-note">{scheme_note}</span>'
    elif scheme_tag == "SCHEME_NEW":
        scheme_html = f'<span class="intel-scheme-new">🎬 NEW SCHEME</span> <span class="intel-note">{scheme_note}</span>'
    elif scheme_tag == "DEF_SCHEME_FIT":
        scheme_html = f'<span class="intel-def-fit">🛡️ DEF SCHEME FIT</span> <span class="intel-note-hot">{scheme_note}</span>'
    elif scheme_tag == "DEF_SCHEME_NEW":
        scheme_html = f'<span class="intel-def-new">🛡️ NEW DC</span> <span class="intel-note">{scheme_note}</span>'
    elif scheme_tag == "DST_STREAM_SOFT":
        scheme_html = f'<span class="intel-dst-soft">🟢 DST STREAMER</span> <span class="intel-note-hot">{scheme_note}</span>'
    elif scheme_tag == "DST_STREAM":
        scheme_html = f'<span class="intel-dst">📅 DST OUTLOOK</span> <span class="intel-note">{scheme_note}</span>'

    body = f"{pref_badge}{tag_badge}{note_html}{link_html}".strip()
    if scheme_html:
        body = f"{body}<br>{scheme_html}" if body and body != "—" else scheme_html
    return body if body else "—"

# Sidebar Wishlist & Fade Manager
st.sidebar.markdown("---")
st.sidebar.markdown("### 🎯 Wishlist & Fade Manager")
all_player_names = sorted(df_board['player_name'].tolist())

selected_targets = st.sidebar.multiselect(
    "⭐ My Targets (Prioritize Drafting)",
    options=all_player_names,
    default=[p for p in all_player_names if clean_name(p) in st.session_state.my_targets]
)
st.session_state.my_targets = {clean_name(p) for p in selected_targets}

selected_fades = st.sidebar.multiselect(
    "🚫 My Fades (Do Not Draft)",
    options=all_player_names,
    default=[p for p in all_player_names if clean_name(p) in st.session_state.my_fades]
)
st.session_state.my_fades = {clean_name(p) for p in selected_fades}

manager_wallets = {}
for i in range(1, league_size + 1):
    m_name = st.session_state.custom_manager_names.get(i, f"Team {i}")
    manager_wallets[i] = {
        "spent": 0, "picks": 0, "name": m_name,
        "roster": [], "pos_counts": {'QB': 0, 'RB': 0, 'WR': 0, 'TE': 0, 'IDP': 0, 'DEF': 0},
        "itemized_spent": {'QB': 0, 'RB': 0, 'WR': 0, 'TE': 0, 'IDP': 0, 'DEF': 0},
        "bid_history": []
    }

# Snake Slot Helper
def get_snake_team_on_clock(pick_idx, n_teams):
    round_num = (pick_idx - 1) // n_teams + 1
    pick_in_r = (pick_idx - 1) % n_teams + 1
    return pick_in_r if round_num % 2 == 1 else (n_teams - pick_in_r + 1)

def get_next_my_pick(curr_pick, my_slot_num, n_teams, total_picks):
    for p in range(curr_pick, total_picks + 1):
        if get_snake_team_on_clock(p, n_teams) == my_slot_num:
            return p
    return total_picks + 1

def get_teams_picking_between(curr_pick, next_pick, n_teams):
    teams = []
    for p in range(curr_pick, next_pick):
        t = get_snake_team_on_clock(p, n_teams)
        if t not in teams:
            teams.append(t)
    return teams

curr_overall_pick = len(st.session_state.drafted_picks) + 1
total_league_picks = league_size * total_roster_slots
snake_on_clock_team = get_snake_team_on_clock(curr_overall_pick, league_size)
next_my_pick_num = get_next_my_pick(curr_overall_pick, my_slot, league_size, total_league_picks)
picks_until_my_turn = max(0, next_my_pick_num - curr_overall_pick)
teams_between = get_teams_picking_between(curr_overall_pick, next_my_pick_num, league_size)

if room_mode == "🎮 Mock Sim Sandbox":
    st.sidebar.markdown("---")
    st.sidebar.markdown("#### 🎲 Sim Controls")
    col_s1, col_s2 = st.sidebar.columns(2)
    with col_s1:
        if st.button("⚡ Sim 1 Pick", use_container_width=True):
            unpicked_now = df_board[~df_board['clean_name'].isin(st.session_state.drafted_picks.keys())]
            if len(unpicked_now) > 0:
                target_p = unpicked_now.iloc[0]
                if draft_mode == "🔨 Auction / Salary Cap":
                    rand_team = random.choice([t for t in range(1, league_size + 1) if t != my_slot])
                    var_price = max(1, int(round(target_p['market_cost'] * random.uniform(0.92, 1.08))))
                else:
                    rand_team = snake_on_clock_team
                    var_price = curr_overall_pick
                st.session_state.drafted_picks[target_p['clean_name']] = {
                    "price": var_price, "team": rand_team,
                    "player_name": target_p['player_name'], "position": target_p['position']
                }
                st.rerun()
    with col_s2:
        if st.button("🎲 Sim 5 Picks", use_container_width=True):
            unpicked_now = df_board[~df_board['clean_name'].isin(st.session_state.drafted_picks.keys())]
            for i in range(min(5, len(unpicked_now))):
                target_p = unpicked_now.iloc[i]
                sim_pick_num = len(st.session_state.drafted_picks) + 1
                if draft_mode == "🔨 Auction / Salary Cap":
                    rand_team = random.choice([t for t in range(1, league_size + 1) if t != my_slot])
                    var_price = max(1, int(round(target_p['market_cost'] * random.uniform(0.90, 1.10))))
                else:
                    rand_team = get_snake_team_on_clock(sim_pick_num, league_size)
                    var_price = sim_pick_num
                st.session_state.drafted_picks[target_p['clean_name']] = {
                    "price": var_price, "team": rand_team,
                    "player_name": target_p['player_name'], "position": target_p['position']
                }
            st.rerun()
    if st.sidebar.button("🗑️ Reset Draft Board", use_container_width=True):
        st.session_state.drafted_picks = {}
        st.session_state.last_ai_read = ""
        st.session_state.last_ai_nom = ""
        st.rerun()
else:
    draft_id = st.sidebar.text_input("Sleeper Draft / League ID", value=LEAGUE_ID)
    if st.sidebar.button("🔄 Sync Live Sleeper API", use_container_width=True):
        st.rerun()
    if draft_id and draft_id.strip():
        try:
            u_res = requests.get(f"https://api.sleeper.app/v1/league/{draft_id.strip()}/users", timeout=4)
            if u_res.status_code == 200:
                user_map_raw = {u['user_id']: (u.get('display_name') or u.get('metadata', {}).get('team_name')) for u in u_res.json()}
                r_res = requests.get(f"https://api.sleeper.app/v1/league/{draft_id.strip()}/rosters", timeout=4)
                if r_res.status_code == 200:
                    for r in r_res.json():
                        r_id = r.get('roster_id')
                        owner_id = r.get('owner_id')
                        disp_name = user_map_raw.get(owner_id)
                        if disp_name and r_id and r_id <= league_size:
                            for def_info in SOULJA_SOULJA_DEFAULTS.values():
                                if def_info['handle'].lower() == disp_name.lower():
                                    disp_name = def_info['name']
                                    break
                            st.session_state.custom_manager_names[r_id] = disp_name
                        
            p_res = requests.get(f"https://api.sleeper.app/v1/draft/{draft_id.strip()}/picks", timeout=4)
            if p_res.status_code == 200:
                for p in p_res.json():
                    meta = p.get('metadata', {})
                    c_name = clean_name(f"{meta.get('first_name', '')} {meta.get('last_name', '')}")
                    amt = int(meta.get('amount') or p.get('amount') or p.get('pick_no') or 1)
                    slot = p.get('draft_slot', 1)
                    pos = player_pos_map.get(c_name, meta.get('position', 'FLEX'))
                    display_name = player_display_map.get(c_name, f"{meta.get('first_name', '')} {meta.get('last_name', '')}")
                    if c_name:
                        st.session_state.drafted_picks[c_name] = {
                            "price": amt, "team": slot,
                            "player_name": display_name, "position": pos
                        }
        except Exception as e:
            st.sidebar.error(f"Sync Notice: {e}")

# Wallet Accounting
for c_p, pdata in st.session_state.drafted_picks.items():
    s = pdata["team"]
    pos = pdata.get("position", player_pos_map.get(c_p, "FLEX"))
    amt = pdata["price"]
    if s in manager_wallets:
        manager_wallets[s]["spent"] += amt
        manager_wallets[s]["picks"] += 1
        manager_wallets[s]["bid_history"].append(amt)
        label_val = f"${amt}" if draft_mode == "🔨 Auction / Salary Cap" else f"Pick #{amt}"
        manager_wallets[s]["roster"].append(f"{pdata['player_name']} ({label_val})")
        if pos in ['LB', 'DL', 'DB']:
            manager_wallets[s]["pos_counts"]['IDP'] += 1
            manager_wallets[s]["itemized_spent"]['IDP'] += amt
        elif pos in manager_wallets[s]["pos_counts"]:
            manager_wallets[s]["pos_counts"][pos] += 1
            manager_wallets[s]["itemized_spent"][pos] += amt

total_cash_spent = sum(v["price"] for v in st.session_state.drafted_picks.values())
picked_clean_names = set(st.session_state.drafted_picks.keys())
df_unpicked = df_board[~df_board['clean_name'].isin(picked_clean_names)].copy()

remaining_league_cash = (league_size * 200) - total_cash_spent
unpicked_fair_sum = df_unpicked['fair_value_base'].sum() if 'fair_value_base' in df_unpicked else df_unpicked['fair_value'].sum()
# Use the single live inflation index computed at valuation time (fair_value is
# already inflated by it, so recomputing off inflated values would double-count).
inflation_index = round(float(df_board['live_inflation'].iloc[0]) if 'live_inflation' in df_board and len(df_board) else 1.0, 2)
my_wallet = manager_wallets.get(my_slot, {"spent": 0, "picks": 0})
my_cap_left = 200 - my_wallet['spent']
my_slots_left = total_roster_slots - my_wallet['picks']
my_max_bid = max(1, my_cap_left - (my_slots_left - 1))

# 💬 FEATURE 3: ASK THE AI STRATEGIST
st.sidebar.markdown("---")
st.sidebar.markdown("### 🤖 Ask the AI War Room")

def build_camp_intel_digest(board_df, only_available=True, max_players=40):
    """Collect every player carrying a REAL crunched intel note and rank them so
    the strategist can synthesize the genuine edge (tier jumpers, camp risers,
    role pinches) instead of only reacting to names typed in the query."""
    picked_clean = picked_clean_names if 'picked_clean_names' in globals() else set(st.session_state.get("drafted_picks", {}).keys())

    POS_TAGS = ("TIER_JUMPER", "SUPERFLEX", "BREAKOUT", "VALUE", "CLEARED", "WAIVER", "SURGE", "CORE_ANCHOR", "STUD")
    rows = []
    for _, pr in board_df.iterrows():
        note = str(pr.get("intel_note", "")).strip()
        sch_note = str(pr.get("scheme_note", "")).strip()
        # include a player if they have real news OR a coaching scheme-fit read
        if (not note or note in ("—", "-")) and not sch_note:
            continue
        if only_available and pr["clean_name"] in picked_clean:
            continue
        tag = str(pr.get("intel_tag", "")).upper()
        is_pos = any(t in tag for t in POS_TAGS)
        # fold in 2026 coaching scheme-fit note when present
        sch = str(pr.get("scheme_note", "")).strip()
        full_note = f"{note} {sch}".strip() if sch else note
        # sort key: positive-signal players first, then by VORP
        rows.append((is_pos, float(pr.get("live_vorp", 0.0)), pr["player_name"], pr["position"], tag, full_note))
    rows.sort(key=lambda x: (x[0], x[1]), reverse=True)
    lines = [
        f"• {name} ({pos}) [{tag or 'BEAT'} | VORP +{vorp:.0f}]: {note}"
        for (_, vorp, name, pos, tag, note) in rows[:max_players]
    ]
    return "\n".join(lines) if lines else "No crunched camp intel available — run 'Pull Latest News & Sync Wire' first."

# One-click: synthesize the edge from ALL crunched news (no need to name players)
if st.sidebar.button("📈 Give Me the Edge (Tier Jumpers & Camp Risers)", use_container_width=True):
    digest = build_camp_intel_digest(df_board, only_available=True, max_players=40)
    live_snapshot = (
        f"Draft Format: {draft_mode} ({qb_format})\n"
        f"Your Current Roster: {', '.join(my_wallet['roster']) if my_wallet['roster'] else 'None yet'}"
    )
    edge_query = (
        "Using ONLY the crunched camp intel below, give me my edge for this draft. "
        "Identify the 3-5 biggest TIER JUMPERS / camp risers I should target, and 2-3 players "
        "whose camp news is a red flag to fade. Cite the specific detail from each player's note "
        "(the actual catch totals, coverage wins, role changes, or injuries) so I know it is real."
    )
    with st.spinner("AI crunching all collected camp news for your edge..."):
        ans = ask_ai_strategist(edge_query, live_snapshot, digest)
        with st.chat_message("assistant", avatar="📈"):
            st.markdown(ans)

ai_query = st.sidebar.text_input("Ask situational draft question:", placeholder="e.g. Should I take Gibbs or Bijan?")
if st.sidebar.button("Ask AI Strategist", use_container_width=True):
    if ai_query.strip():
        grounded_player_cards = []
        q_tokens = clean_name(ai_query).split()
        
        for _, p_row in df_board.iterrows():
            p_clean = p_row['clean_name']
            p_parts = p_clean.split()
            last_n = p_parts[-1] if p_parts else ""
            
            if p_clean in ai_query.lower() or (len(last_n) >= 4 and last_n in q_tokens):
                grounded_player_cards.append(
                    f"• {p_row['player_name']} ({p_row['position']}): Tier: {p_row['tier']} | "
                    f"Model Fair Value: ${int(p_row['fair_value'])} | Market ADP: #{int(p_row['market_adp'])} | "
                    f"True VORP: +{round(p_row['live_vorp'], 1)} pts | Intel: {p_row['intel_note'] if p_row['intel_note'] else 'Healthy & Active'}"
                )

        # If the question is open-ended (no specific player named), still ground the
        # model on the full crunched-news digest so it never answers from thin air.
        if not grounded_player_cards:
            telemetry_str = build_camp_intel_digest(df_board, only_available=True, max_players=40)
        else:
            telemetry_str = "\n".join(grounded_player_cards)
        
        live_snapshot = (
            f"Draft Format: {draft_mode} ({qb_format})\n"
            f"Your Remaining Budget: ${my_cap_left} (Max Single Bid: ${my_max_bid}, Open Slots: {my_slots_left})\n"
            f"Room Inflation Index: {inflation_index}x\n"
            f"Your Current Roster: {', '.join(my_wallet['roster']) if my_wallet['roster'] else 'None'}"
        )
        
        with st.spinner("AI evaluating exact player values, VORPs, and draft room state..."):
            ans = ask_ai_strategist(ai_query, live_snapshot, telemetry_str)
            with st.chat_message("assistant", avatar="⚡"):
                st.markdown(ans)

if draft_mode == "🔨 Auction / Salary Cap":
    st.markdown(f"### 🏈 SALARY CAP AUCTION RADAR • `{my_manager_display}` • `{qb_format}`")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("League Capital Remaining", f"${remaining_league_cash}", f"-${total_cash_spent} Spent")
    c2.metric("Room Inflation Index", f"{inflation_index}x", "Deflation (Bargains)" if inflation_index < 1.0 else "Inflation (Overpay)")
    c3.metric("Players Drafted", f"{len(picked_clean_names)} / {league_size * total_roster_slots}", f"{(league_size * total_roster_slots) - len(picked_clean_names)} Left")
    c4.metric("Your Max Single Bid", f"${my_max_bid}", f"${my_cap_left} Budget Left")
else:
    st.markdown(f"### 🐍 SNAKE DRAFT WAR ROOM • `{my_manager_display}` • `{qb_format}`")
    c1, c2, c3, c4 = st.columns(4)
    curr_round = (curr_overall_pick - 1) // league_size + 1
    curr_round_pick = (curr_overall_pick - 1) % league_size + 1
    c1.metric("Current Draft Pick", f"Round {curr_round}, Pick {curr_round_pick}", f"Overall Pick #{curr_overall_pick}")
    
    clock_name = st.session_state.custom_manager_names.get(snake_on_clock_team, f"Team {snake_on_clock_team}")
    clock_label = f"⭐ YOU ({clock_name})" if snake_on_clock_team == my_slot else clock_name
    c2.metric("On The Clock", clock_label, f"Draft Slot #{snake_on_clock_team}")
    
    turn_str = "NOW DRAFTING" if picks_until_my_turn == 0 else f"{picks_until_my_turn} Picks Away"
    c3.metric("Distance to Your Turn", turn_str, f"Your Pick: #{next_my_pick_num}")
    c4.metric("Roster Completed", f"{my_wallet['picks']} / {total_roster_slots}", f"{my_slots_left} Slots Needed")

st.markdown("---")

# 5. Positional Cliff Tracker
st.markdown("#### 🚨 POSITIONAL ACTIVE TIER CLIFF TRACKER")
cliff_cols = st.columns(4)
tier_order = ['Tier 1', 'Tier 2', 'Tier 3', 'Tier 4', 'Tier 5']

for idx, pos in enumerate(['RB', 'WR', 'TE', 'QB']):
    pos_pool = df_unpicked[df_unpicked['position'] == pos].sort_values(by='live_vorp', ascending=False)
    active_tier = None
    next_tier = None
    for t_idx, t_name in enumerate(tier_order):
        count_in_t = len(pos_pool[pos_pool['tier'] == t_name])
        if count_in_t > 0:
            active_tier = t_name
            if t_idx + 1 < len(tier_order): next_tier = tier_order[t_idx + 1]
            break
            
    with cliff_cols[idx]:
        if active_tier:
            curr_pool = pos_pool[pos_pool['tier'] == active_tier]
            sub_pool = pos_pool[pos_pool['tier'] == next_tier] if next_tier else pd.DataFrame()
            t_count = len(curr_pool)
            drop_pts = int(round(curr_pool['live_vorp'].iloc[-1] - sub_pool['live_vorp'].iloc[0])) if (len(curr_pool) > 0 and len(sub_pool) > 0) else 0
            is_danger = t_count <= 2
            alert_class = "cliff-card cliff-alert" if is_danger else "cliff-card"
            badge = "🔥 URGENT" if is_danger else ("⚠️ CLIFF" if drop_pts >= 10 else "STABLE")
            tier_label = active_tier.upper()
            drop_html = f'<span style="font-size:0.85rem; color:#ef4444;">(-{drop_pts} pts)</span>' if drop_pts > 0 else ''
            
            card_html = (
                f'<div class="{alert_class}">'
                f'<div style="font-size:0.8rem; color:#94a3b8; display:flex; justify-content:space-between;">'
                f'<b>{pos} {tier_label}</b> <span>{badge}</span>'
                f'</div>'
                f'<div style="font-size:1.4rem; font-weight:700; color:white; margin-top:4px;">'
                f'{t_count} Left {drop_html}'
                f'</div>'
                f'</div>'
            )
            st.markdown(card_html, unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="cliff-card"><div style="font-size:0.8rem; color:#94a3b8;"><b>{pos} TIERS</b></div><div style="font-size:1.1rem; font-weight:700; color:#64748b; margin-top:6px;">All Tiers Depleted</div></div>', unsafe_allow_html=True)

st.markdown("---")

# 5.5 Dynamic Targeting & Playbook
my_counts = my_wallet['pos_counts']
pos_targets = {'QB': 2 if qb_format == '⚡ Superflex / 2-QB' else 1, 'RB': 4, 'WR': 4, 'TE': 2, 'IDP': 4 if include_idp else 0, 'DEF': 1}
pos_gaps = {pos: max(0, target - my_counts.get(pos, 0)) for pos, target in pos_targets.items()}

non_faded_unpicked = df_unpicked[~df_unpicked['clean_name'].isin(st.session_state.my_fades)].copy()
offense_needed = [p for p in ['QB', 'RB', 'WR', 'TE'] if pos_gaps.get(p, 0) > 0]
display_positions = ['QB', 'RB', 'WR', 'TE'] if offense_needed else (['LB', 'DL', 'DB', 'DEF'] if include_idp else ['DEF'])

if draft_mode == "🔨 Auction / Salary Cap":
    st.markdown("#### 🧠 REAL-TIME DYNAMIC TARGETING & NOMINATION ADVISOR")
    affordable_df = non_faded_unpicked[non_faded_unpicked['fair_value'] <= my_max_bid].copy()
    primary_candidate_pool = affordable_df[affordable_df['position'].isin(display_positions)].copy()

    top_stud_name = ""
    user_priority_pool = primary_candidate_pool[primary_candidate_pool['clean_name'].isin(st.session_state.my_targets)]

    if not user_priority_pool.empty:
        top_stud = user_priority_pool.sort_values(by='fair_value', ascending=False).iloc[0]
        top_stud_name = top_stud['clean_name']
        rec_bid = min(my_max_bid, int(round(top_stud['fair_value'])))  # fair_value already live-inflated
        stud_card_html = (
            '<div style="background:#131b2e; border-top:4px solid #10b981; padding:12px; border-radius:6px; height:100%;">'
            '<div style="font-size:0.75rem; color:#10b981; font-weight:700;">⭐ YOUR PRIORITY TARGET</div>'
            f'<div style="font-size:1.15rem; font-weight:700; color:white; margin:4px 0;">{top_stud["player_name"]} <span class="badge-pos pos-{top_stud["position"]}">{top_stud["position"]}</span></div>'
            f'<div style="font-size:0.85rem; color:#94a3b8;">Max Bid-To: <b style="color:#10b981;">${rec_bid}</b> | Market ADP: ${top_stud["market_cost"]}</div>'
            f'<div style="font-size:0.75rem; color:#cbd5e1; margin-top:6px;"><b>Strategy:</b> Starred priority target. Secure before positional runs exhaust budget.</div>'
            '</div>'
        )
    elif not primary_candidate_pool.empty:
        top_stud = primary_candidate_pool.sort_values(by='fair_value', ascending=False).iloc[0]
        top_stud_name = top_stud['clean_name']
        rec_bid = min(my_max_bid, int(round(top_stud['fair_value'])))  # fair_value already live-inflated
        stud_card_html = (
            '<div style="background:#131b2e; border-top:4px solid #10b981; padding:12px; border-radius:6px; height:100%;">'
            '<div style="font-size:0.75rem; color:#10b981; font-weight:700;">👑 RECOMMENDED ANCHOR / STUD</div>'
            f'<div style="font-size:1.15rem; font-weight:700; color:white; margin:4px 0;">{top_stud["player_name"]} <span class="badge-pos pos-{top_stud["position"]}">{top_stud["position"]}</span></div>'
            f'<div style="font-size:0.85rem; color:#94a3b8;">Max Bid-To: <b style="color:#10b981;">${rec_bid}</b> | Market ADP: ${top_stud["market_cost"]}</div>'
            f'<div style="font-size:0.75rem; color:#cbd5e1; margin-top:6px;"><b>Strategy:</b> Highest available VORP ({round(top_stud["live_vorp"], 1)}) to fill your open {top_stud["position"]} slot.</div>'
            '</div>'
        )
    else:
        stud_card_html = '<div style="background:#131b2e; border-top:4px solid #10b981; padding:12px; border-radius:6px;"><div style="font-size:0.75rem; color:#10b981; font-weight:700;">👑 RECOMMENDED ANCHOR / STUD</div><div style="font-size:0.9rem; color:#94a3b8; margin-top:8px;">Positions filled or budget constrained.</div></div>'

    pos_arb_rows = []
    for target_pos in display_positions:
        pos_pool = primary_candidate_pool[(primary_candidate_pool['position'] == target_pos) & (primary_candidate_pool['clean_name'] != top_stud_name)].copy()
        if not pos_pool.empty:
            pos_pool['surplus_val'] = pos_pool['fair_value'] - pos_pool['market_cost']
            pos_pool['ppd'] = pos_pool['live_vorp'] / pos_pool['market_cost'].clip(lower=1)
            pos_pool['target_boost'] = pos_pool['clean_name'].apply(lambda x: 1.6 if x in st.session_state.my_targets else 1.0)
            
            pos_surplus = pos_pool[pos_pool['surplus_val'] > 0].copy()
            if not pos_surplus.empty:
                pos_surplus['score'] = pos_surplus['surplus_val'] * pos_surplus['ppd'] * pos_surplus['target_boost']
                best_p = pos_surplus.sort_values(by=['score', 'live_vorp'], ascending=[False, False]).iloc[0]
                val_text = f"+${int(best_p['surplus_val'])} Surplus"
                val_color = "#10b981"
            else:
                pos_pool['eff_score'] = pos_pool['ppd'] * pos_pool['target_boost']
                best_p = pos_pool.sort_values(by=['eff_score', 'live_vorp'], ascending=[False, False]).iloc[0]
                ppd_val = round(float(best_p['live_vorp']) / max(1, float(best_p['market_cost'])), 1)
                val_text = f"{ppd_val} VORP/$"
                val_color = "#60a5fa"
                
            is_p_starred = "⭐ " if best_p['clean_name'] in st.session_state.my_targets else ""
            exec_price = max(1, min(int(best_p['fair_value']), int(round(best_p['market_cost'] * 0.95))))
            
            row_html = (
                '<div style="display:flex; justify-content:space-between; align-items:center; background:#0b0f19; padding:5px 8px; margin-bottom:4px; border-radius:4px; border-left:3px solid #3b82f6;">'
                '<div>'
                f'<span class="badge-pos pos-{best_p["position"]}">{best_p["position"]}</span> <b>{is_p_starred}{best_p["player_name"]}</b> <span style="font-size:0.75rem; color:#94a3b8;">({best_p["tier"]})</span><br>'
                f'<span style="font-size:0.72rem; color:#94a3b8;">Fair: <b>${int(best_p["fair_value"])}</b> | Mkt: <b>${int(best_p["market_cost"])}</b> | Bid-To: <b>${exec_price}</b></span>'
                '</div>'
                f'<div style="font-size:0.8rem; font-weight:700; color:{val_color}; text-align:right;">{val_text}</div>'
                '</div>'
            )
            pos_arb_rows.append(row_html)

    rendered_rows = "".join(pos_arb_rows) if pos_arb_rows else '<div style="font-size:0.85rem; color:#94a3b8;">No arbitrage available.</div>'
    bargain_card_html = f'<div style="background:#131b2e; border-top:4px solid #3b82f6; padding:10px 12px; border-radius:6px; height:100%;"><div style="font-size:0.75rem; color:#3b82f6; font-weight:700; margin-bottom:6px;">💎 POSITIONAL ARBITRAGE (BEST PER POSITION)</div>{rendered_rows}</div>'

    # Nomination Playbook & AI Generator
    nom_strategy = st.radio("Select Your Tactical Nomination Intent:", ["💸 Bleed Rival Wallets (High-Cost Bait)", "💣 Landmine Trap (Overvalued Decoy)", "🥷 Stealth Sneak ($1-$3 Value Snipe)", "👑 Set the Market (Target Price Discovery)"], horizontal=True)
    
    if st.button("🤖 Generate AI Nomination Trap Suggestion", use_container_width=True):
        with st.spinner("AI analyzing opponent budgets, positional voids, and traps..."):
            unpicked_top = ", ".join([f"{r['player_name']} (${r['market_cost']})" for _, r in df_unpicked.head(8).iterrows()])
            rivals_sum = ", ".join([f"{d['name']} (Cap: ${200-d['spent']})" for s, d in manager_wallets.items() if s != my_slot][:5])
            needs_sum = ", ".join([f"{pos}: {cnt}" for pos, cnt in pos_gaps.items() if cnt > 0])
            
            st.session_state.last_ai_nom = generate_ai_nomination(nom_strategy, unpicked_top, rivals_sum, needs_sum)

    if st.session_state.last_ai_nom:
        with st.chat_message("assistant", avatar="🎯"):
            st.markdown(st.session_state.last_ai_nom)

    pos_nom_rows = []
    for target_pos in display_positions:
        pos_pool = df_unpicked[df_unpicked['position'] == target_pos].copy()
        if pos_pool.empty: continue
        if nom_strategy == "💸 Bleed Rival Wallets (High-Cost Bait)":
            safe_pool = pos_pool[~pos_pool['clean_name'].isin(st.session_state.my_targets)].copy()
            fade_pool = safe_pool[safe_pool['clean_name'].isin(st.session_state.my_fades)].sort_values(by='market_cost', ascending=False)
            nom_p = fade_pool.iloc[0] if not fade_pool.empty else safe_pool.sort_values(by='market_cost', ascending=False).iloc[0]
            val_text = f"${int(nom_p['market_cost'])} Fade" if not fade_pool.empty else f"${int(nom_p['market_cost'])} Drain"
            val_color = "#ef4444" if not fade_pool.empty else "#f59e0b"
            is_p_starred = "🚫 " if nom_p['clean_name'] in st.session_state.my_fades else ""
            sub_desc = f"Fair: ${int(nom_p['fair_value'])} | Drain rival cap on non-target"
        elif nom_strategy == "💣 Landmine Trap (Overvalued Decoy)":
            safe_pool = pos_pool[~pos_pool['clean_name'].isin(st.session_state.my_targets)].copy()
            safe_pool['landmine_gap'] = safe_pool['market_cost'] - safe_pool['fair_value']
            nom_p = safe_pool.sort_values(by='landmine_gap', ascending=False).iloc[0]
            gap = int(nom_p['market_cost'] - nom_p['fair_value'])
            val_text = f"+${gap} Trap" if gap > 0 else f"${gap} Fair"
            val_color = "#ef4444" if gap > 0 else "#94a3b8"
            is_p_starred = "🚫 " if nom_p['clean_name'] in st.session_state.my_fades else ""
            sub_desc = f"Bait: ${int(nom_p['market_cost'])} vs True Value ${int(nom_p['fair_value'])}"
        elif nom_strategy == "🥷 Stealth Sneak ($1-$3 Value Snipe)":
            cheap_pool = pos_pool[(pos_pool['market_cost'] <= 3) & (~pos_pool['clean_name'].isin(st.session_state.my_fades))].sort_values(by='live_vorp', ascending=False)
            nom_p = cheap_pool.iloc[0] if not cheap_pool.empty else pos_pool.sort_values(by='market_cost', ascending=True).iloc[0]
            val_text = f"${int(nom_p['market_cost'])} Snipe"
            val_color = "#10b981"
            is_p_starred = "⭐ " if nom_p['clean_name'] in st.session_state.my_targets else ""
            sub_desc = f"Sneak {round(nom_p['live_vorp'], 1)} VORP while room is sleeping"
        else:
            user_targets = pos_pool[pos_pool['clean_name'].isin(st.session_state.my_targets)].sort_values(by='fair_value', ascending=False)
            nom_p = user_targets.iloc[0] if not user_targets.empty else pos_pool.sort_values(by='fair_value', ascending=False).iloc[0]
            val_text = f"${int(nom_p['fair_value'])} Floor"
            val_color = "#10b981" if not user_targets.empty else "#60a5fa"
            is_p_starred = "⭐ " if not user_targets.empty else ""
            sub_desc = f"Establish floor price on your wishlist target"

        row_html = (
            '<div style="display:flex; justify-content:space-between; align-items:center; background:#0b0f19; padding:5px 8px; margin-bottom:4px; border-radius:4px; border-left:3px solid #f59e0b;">'
            '<div>'
            f'<span class="badge-pos pos-{nom_p["position"]}">{nom_p["position"]}</span> <b>{is_p_starred}{nom_p["player_name"]}</b> <span style="font-size:0.75rem; color:#94a3b8;">({nom_p["tier"]})</span><br>'
            f'<span style="font-size:0.72rem; color:#94a3b8;">{sub_desc}</span>'
            '</div>'
            f'<div style="font-size:0.8rem; font-weight:700; color:{val_color}; text-align:right;">{val_text}</div>'
            '</div>'
        )
        pos_nom_rows.append(row_html)

    rendered_nom_rows = "".join(pos_nom_rows) if pos_nom_rows else '<div style="font-size:0.85rem; color:#94a3b8;">No nominations available.</div>'
    nom_card_html = f'<div style="background:#131b2e; border-top:4px solid #f59e0b; padding:10px 12px; border-radius:6px; height:100%;"><div style="font-size:0.75rem; color:#f59e0b; font-weight:700; margin-bottom:6px;">🎯 POSITIONAL NOMINATIONS (BEST BAIT / SNIPES)</div>{rendered_nom_rows}</div>'

    rec_col1, rec_col2, rec_col3 = st.columns(3)
    with rec_col1: st.markdown(stud_card_html, unsafe_allow_html=True)
    with rec_col2: st.markdown(bargain_card_html, unsafe_allow_html=True)
    with rec_col3: st.markdown(nom_card_html, unsafe_allow_html=True)

else:
    st.markdown(f"#### 🐍 SNAKE DRAFT TURN PREDICTOR & VALUE ENGINE ({qb_format})")
    snake_col1, snake_col2, snake_col3 = st.columns(3)
    
    primary_candidate_pool = non_faded_unpicked[non_faded_unpicked['position'].isin(display_positions)].copy()
    user_targets_pool = primary_candidate_pool[primary_candidate_pool['clean_name'].isin(st.session_state.my_targets)]
    
    if not user_targets_pool.empty:
        best_p = user_targets_pool.sort_values(by='live_vorp', ascending=False).iloc[0]
        s_title = "⭐ YOUR PRIORITY TARGET"
    elif not primary_candidate_pool.empty:
        best_p = primary_candidate_pool.sort_values(by='live_vorp', ascending=False).iloc[0]
        s_title = "👑 BEST AVAILABLE (VORP ANCHOR)"
    else:
        best_p = None

    with snake_col1:
        if best_p is not None:
            st.markdown(
                '<div style="background:#131b2e; border-top:4px solid #10b981; padding:12px; border-radius:6px; height:100%;">'
                f'<div style="font-size:0.75rem; color:#10b981; font-weight:700;">{s_title}</div>'
                f'<div style="font-size:1.15rem; font-weight:700; color:white; margin:4px 0;">{best_p["player_name"]} <span class="badge-pos pos-{best_p["position"]}">{best_p["position"]}</span></div>'
                f'<div style="font-size:0.85rem; color:#94a3b8;">Consensus ADP: <b>#{int(best_p["market_adp"])}</b> | True VORP: <b style="color:#10b981;">+{round(best_p["live_vorp"], 1)}</b> ({best_p["tier"]})</div>'
                f'<div style="font-size:0.75rem; color:#cbd5e1; margin-top:6px;"><b>Recommendation:</b> Premier VORP target to fill your starting {best_p["position"]} slot.</div>'
                '</div>', unsafe_allow_html=True
            )

    with snake_col2:
        non_faded_unpicked['adp_surplus'] = non_faded_unpicked['market_adp'] - non_faded_unpicked['board_rank']
        fallers = non_faded_unpicked[non_faded_unpicked['adp_surplus'] >= 2].sort_values(by=['adp_surplus', 'live_vorp'], ascending=[False, False]).head(4)
        
        faller_rows = []
        for _, f_row in fallers.iterrows():
            f_starred = "⭐ " if f_row['clean_name'] in st.session_state.my_targets else ""
            val_spots = int(f_row['adp_surplus'])
            row_html = (
                '<div style="display:flex; justify-content:space-between; align-items:center; background:#0b0f19; padding:5px 8px; margin-bottom:4px; border-radius:4px; border-left:3px solid #3b82f6;">'
                '<div>'
                f'<span class="badge-pos pos-{f_row["position"]}">{f_row["position"]}</span> <b>{f_row["player_name"]}</b> {f_starred}<br>'
                f'<span style="font-size:0.72rem; color:#94a3b8;">Market ADP: #{int(f_row["market_adp"])} | Board Rank: #{int(f_row["board_rank"])}</span>'
                '</div>'
                f'<div style="font-size:0.8rem; font-weight:700; color:#38bdf8;">+{val_spots} Spots Value</div>'
                '</div>'
            )
            faller_rows.append(row_html)
        
        rendered_fallers = "".join(faller_rows) if faller_rows else '<div style="font-size:0.85rem; color:#94a3b8;">Draft proceeding precisely on consensus ADP.</div>'
        st.markdown(
            f'<div style="background:#131b2e; border-top:4px solid #3b82f6; padding:10px 12px; border-radius:6px; height:100%;">'
            f'<div style="font-size:0.75rem; color:#3b82f6; font-weight:700; margin-bottom:6px;">💎 TOP MARKET VALUE TARGETS (STEALS AT ADP)</div>'
            f'{rendered_fallers}'
            f'</div>', unsafe_allow_html=True
        )

    with snake_col3:
        dead_zone_targets = non_faded_unpicked[
            (non_faded_unpicked['market_adp'] > curr_overall_pick) &
            (non_faded_unpicked['market_adp'] <= next_my_pick_num)
        ].sort_values(by='live_vorp', ascending=False).head(4)
        
        turn_rows = []
        for _, t_row in dead_zone_targets.iterrows():
            t_starred = "⭐ " if t_row['clean_name'] in st.session_state.my_targets else ""
            row_html = (
                '<div style="display:flex; justify-content:space-between; align-items:center; background:#0b0f19; padding:5px 8px; margin-bottom:4px; border-radius:4px; border-left:3px solid #ef4444;">'
                '<div>'
                f'<span class="badge-pos pos-{t_row["position"]}">{t_row["position"]}</span> <b>{t_row["player_name"]}</b> {t_starred}<br>'
                f'<span style="font-size:0.72rem; color:#94a3b8;">Market ADP #{int(t_row["market_adp"])} (Won\'t make pick #{next_my_pick_num})</span>'
                '</div>'
                f'<div style="font-size:0.75rem; font-weight:700; color:#f87171;">REACH TARGET</div>'
                '</div>'
            )
            turn_rows.append(row_html)
            
        rendered_turns = "".join(turn_rows) if turn_rows else '<div style="font-size:0.85rem; color:#94a3b8;">Next pick is close or all top targets safely spaced.</div>'
        st.markdown(
            f'<div style="background:#131b2e; border-top:4px solid #ef4444; padding:10px 12px; border-radius:6px; height:100%;">'
            f'<div style="font-size:0.75rem; color:#ef4444; font-weight:700; margin-bottom:6px;">🚨 TURN SURVIVAL WATCH (WON\'T MAKE IT BACK)</div>'
            f'{rendered_turns}'
            f'</div>', unsafe_allow_html=True
        )

st.markdown("---")

# 6. Draft Console
col_left, col_right = st.columns([1.2, 1])

with col_left:
    st.markdown("#### 🎯 PLAYER DRAFT CONSOLE")
    player_options = df_unpicked['player_name'].tolist()
    if player_options:
        selected_player = st.selectbox("Search or Select Player:", player_options)
        p_data = df_unpicked[df_unpicked['player_name'] == selected_player].iloc[0]
        fair_val = int(round(float(p_data['fair_value'])))
        mkt_val = int(round(float(p_data['market_cost'])))
        bid_to = int(round(fair_val * max(0.90, inflation_index)))
        plan_cap = int(round(fair_val * 0.95))
        delta_vs_mkt = int(bid_to - mkt_val)
        adp_rank = int(p_data['market_adp'])
        my_board_rank = int(p_data['board_rank'])
        
        p_card_col1, p_card_col2, p_card_col3, p_card_col4 = st.columns(4)
        if draft_mode == "🔨 Auction / Salary Cap":
            p_card_col1.metric("Fair Value", f"${fair_val}")
            p_card_col2.metric("Market ADP", f"${mkt_val}")
            p_card_col3.metric("Plan Budget", f"${plan_cap}")
            p_card_col4.metric("MAX BID-TO", f"${bid_to}", f"{delta_vs_mkt:+d} vs Mkt")
        else:
            p_card_col1.metric("Consensus ADP", f"#{adp_rank}")
            val_delta = adp_rank - my_board_rank
            p_card_col2.metric("Market Value Delta", f"{val_delta:+d} Spots", "Value Steal" if val_delta > 0 else "Overpriced")
            p_card_col3.metric("Tier Rating", f"{p_data['tier']}")
            p_card_col4.metric("True VORP", f"+{round(p_data['live_vorp'], 1)} pts")
        
        intel_formatted = format_intel_cell(p_data)
        st.markdown(f"**Position:** <span class='badge-pos pos-{p_data['position']}'>{p_data['position']}</span> | **Team:** `{p_data['team']}` | {intel_formatted}", unsafe_allow_html=True)

        ai_btn_label = "🤖 Generate Real-Time AI Tactical Read" if draft_mode == "🔨 Auction / Salary Cap" else "🤖 Generate Snake Turn & Reach Analysis"
        if st.button(ai_btn_label, use_container_width=True):
            with st.spinner("AI analyzing live room telemetry, rosters, and draft board..."):
                my_roster_str = ", ".join(manager_wallets[my_slot]['roster']) if manager_wallets[my_slot]['roster'] else "No players drafted yet"
                
                if draft_mode == "🔨 Auction / Salary Cap":
                    recent_picks = [f"{v['player_name']} (${v['price']})" for v in list(st.session_state.drafted_picks.values())[-5:]]
                    recent_str = ", ".join(recent_picks)
                    
                    rivals_telemetry = "; ".join([
                        f"{d['name']} (Cap: ${200 - d['spent']}, Needs: {', '.join([pos for pos, cnt in d['pos_counts'].items() if cnt < (3 if pos in ['RB','WR'] else 1)])})"
                        for s, d in manager_wallets.items() if s != my_slot
                    ][:5])
                    
                    st.session_state.last_ai_read = generate_live_auction_advice(
                        player_name=p_data['player_name'],
                        pos=p_data['position'],
                        fair_val=fair_val,
                        mkt_val=mkt_val,
                        max_bid_to=bid_to,
                        inflation_index=inflation_index,
                        news_note=p_data.get('intel_note', ''),
                        my_budget=my_cap_left,
                        my_roster_summary=my_roster_str,
                        live_rivals_telemetry=rivals_telemetry,
                        recent_picks_ledger=recent_str
                    )
                else:
                    between_summary = "; ".join([
                        f"{st.session_state.custom_manager_names.get(t, f'Slot {t}')} (Has: {manager_wallets[t]['pos_counts']['RB']} RBs, {manager_wallets[t]['pos_counts']['WR']} WRs, {manager_wallets[t]['pos_counts']['QB']} QBs)"
                        for t in teams_between if t != my_slot
                    ])
                    
                    st.session_state.last_ai_read = generate_snake_turn_advice(
                        player_name=p_data['player_name'],
                        pos=p_data['position'],
                        adp_rank=adp_rank,
                        vorp_val=round(p_data['live_vorp'], 1),
                        tier_name=p_data['tier'],
                        curr_pick=curr_overall_pick,
                        next_my_pick=next_my_pick_num,
                        my_roster_summary=my_roster_str,
                        teams_between_needs=between_summary if between_summary else "You are on the clock or picking next",
                        news_note=p_data.get('intel_note', '')
                    )

        if st.session_state.last_ai_read:
            with st.chat_message("assistant", avatar="⚡"):
                st.markdown(st.session_state.last_ai_read)

        bcol1, bcol2, _ = st.columns([1, 1, 2])
        with bcol1:
            c_name_curr = p_data['clean_name']
            is_target = c_name_curr in st.session_state.my_targets
            if st.button("⭐ Target (Want)" if not is_target else "★ Remove Target", use_container_width=True):
                if is_target:
                    st.session_state.my_targets.remove(c_name_curr)
                else:
                    st.session_state.my_targets.add(c_name_curr)
                    st.session_state.my_fades.discard(c_name_curr)
                st.rerun()
        with bcol2:
            is_fade = c_name_curr in st.session_state.my_fades
            if st.button("🚫 Fade (Do Not Want)" if not is_fade else "✕ Un-Fade", use_container_width=True):
                if is_fade:
                    st.session_state.my_fades.remove(c_name_curr)
                else:
                    st.session_state.my_fades.add(c_name_curr)
                    st.session_state.my_targets.discard(c_name_curr)
                st.rerun()

        st.markdown("##### 🔨 Draft Selection Confirmation")
        mcol1, mcol2, mcol3 = st.columns([1, 1.2, 1])
        if draft_mode == "🔨 Auction / Salary Cap":
            with mcol1: won_price = st.number_input("Winning Bid ($)", min_value=1, max_value=200, value=mkt_val)
            with mcol2:
                mgr_choices = [i for i in range(1, league_size + 1)]
                won_team = st.selectbox(
                    "Winning Manager:", 
                    mgr_choices, 
                    index=my_slot - 1 if my_slot <= league_size else 0, 
                    format_func=lambda x: f"Slot {x}: {st.session_state.custom_manager_names.get(x, f'Team {x}')}"
                )
        else:
            with mcol1: won_price = st.number_input("Overall Pick #", min_value=1, max_value=total_league_picks, value=curr_overall_pick)
            with mcol2:
                mgr_choices = [i for i in range(1, league_size + 1)]
                won_team = st.selectbox(
                    "Drafting Manager:", 
                    mgr_choices, 
                    index=snake_on_clock_team - 1 if snake_on_clock_team <= league_size else 0, 
                    format_func=lambda x: f"Slot {x}: {st.session_state.custom_manager_names.get(x, f'Team {x}')}"
                )
            
        with mcol3:
            st.write("")
            st.write("")
            if st.button("Mark as Drafted", use_container_width=True):
                st.session_state.drafted_picks[p_data['clean_name']] = {
                    "price": int(won_price), "team": int(won_team),
                    "player_name": p_data['player_name'], "position": p_data['position']
                }
                st.session_state.last_ai_read = ""
                st.rerun()

with col_right:
    if draft_mode == "🔨 Auction / Salary Cap":
        st.markdown("#### 💣 TOP LANDMINE NOMINATIONS (DECOYS)")
        df_unpicked['landmine_delta'] = (df_unpicked['market_cost'] - df_unpicked['fair_value']).astype(int)
        safe_landmines_box = df_unpicked[~df_unpicked['clean_name'].isin(st.session_state.my_targets)]
        landmines = safe_landmines_box[safe_landmines_box['landmine_delta'] > 5].sort_values(by='landmine_delta', ascending=False).head(4)
        for _, lm in landmines.iterrows():
            p_name = lm['player_name']
            pos = lm['position']
            mkt = lm['market_cost']
            fv = lm['fair_value']
            delta = int(lm['landmine_delta'])
            card_html = (
                '<div style="background:#131b2e; border-left:3px solid #ef4444; padding:8px 12px; margin-bottom:6px; border-radius:4px; display:flex; justify-content:space-between; align-items:center;">'
                f'<div><b>{p_name}</b> <span class="badge-pos pos-{pos}">{pos}</span><br>'
                f'<span style="font-size:0.75rem; color:#94a3b8;">Bait Market: <b>${mkt}</b> | True Value: <b>${fv}</b></span></div>'
                f'<span class="landmine-tag">+${delta} TRAP</span></div>'
            )
            st.markdown(card_html, unsafe_allow_html=True)
    else:
        st.markdown("#### 🎯 QUICK REACH CANDIDATES")
        high_vorp_unpicked = df_unpicked.sort_values(by='live_vorp', ascending=False).head(4)
        for _, hr in high_vorp_unpicked.iterrows():
            card_html = (
                '<div style="background:#131b2e; border-left:3px solid #3b82f6; padding:8px 12px; margin-bottom:6px; border-radius:4px; display:flex; justify-content:space-between; align-items:center;">'
                f'<div><b>{hr["player_name"]}</b> <span class="badge-pos pos-{hr["position"]}">{hr["position"]}</span><br>'
                f'<span style="font-size:0.75rem; color:#94a3b8;">Market ADP: #{int(hr["market_adp"])} | True VORP: <b>+{round(hr["live_vorp"], 1)}</b> ({hr["tier"]})</span></div>'
                f'<span class="landmine-tag" style="background:#3b82f620; color:#60a5fa; border:1px solid #3b82f640;">ELITE VORP</span></div>'
            )
            st.markdown(card_html, unsafe_allow_html=True)

st.markdown("---")

# 7. Multi-Tab War Rooms
tab_off, tab_def, tab_intel, tab_matrix, tab_log = st.tabs([
    "⚔️ Offense War Room", 
    "🛡️ IDP & D/ST War Room", 
    "🚀 Live News & Active Intel Board", 
    "🧠 Rival Intelligence & Visual Analytics", 
    "📜 Drafted Log"
])

def render_board_table(df_subset):
    table_rows = []
    tier_counts = df_unpicked.groupby(['position', 'tier']).size().to_dict()
    
    for _, r in df_subset.iterrows():
        pos_curr = r['position']
        tier_curr = str(r['tier'])
        is_last_in_tier = (tier_counts.get((pos_curr, tier_curr), 0) == 1)
        
        if is_last_in_tier:
            tier_num = tier_curr.replace("Tier ", "T").strip().lower()
            tier_badge = f'<span class="t-last t-last-{tier_num}">{tier_num.upper()}-LAST</span>'
        else:
            tier_badge = tier_curr
        
        intel_text = format_intel_cell(r)

        row_dict = {
            "Priority": int(r['board_rank']),
            "Player": r['player_name'],
            "Pos": f'<span class="badge-pos pos-{r["position"]}">{r["position"]}</span>',
            "Team": r['team'],
            "Tier": tier_badge,
            "VORP": round(float(r['live_vorp']), 1)
        }
        
        if draft_mode == "🔨 Auction / Salary Cap":
            row_dict["Fair Value"] = f"${int(r['fair_value'])}"
            row_dict["Market ADP"] = f"${int(r['market_cost'])}"
        else:
            row_dict["Consensus ADP"] = f"#{int(r['market_adp'])}"
            val_delta = int(r['market_adp']) - int(r['board_rank'])
            if val_delta > 0:
                row_dict["Market Value Delta"] = f'<span style="color:#34d399; font-weight:700;">+{val_delta} (Steal at ADP)</span>'
            elif val_delta < 0:
                row_dict["Market Value Delta"] = f'<span style="color:#f87171; font-weight:700;">{val_delta} (Market Overpay)</span>'
            else:
                row_dict["Market Value Delta"] = '<span style="color:#94a3b8; font-weight:700;">Market Fair</span>'

        row_dict["Intel / Real-Time Wire"] = intel_text
        table_rows.append(row_dict)
        
    st.write(pd.DataFrame(table_rows).to_html(escape=False, index=False), unsafe_allow_html=True)

with tab_off:
    pos_sub = st.radio("Offense Filter:", ["ALL OFFENSE", "RB", "WR", "TE", "QB"], horizontal=True)
    df_o = df_unpicked[df_unpicked['position'].isin(['QB', 'RB', 'WR', 'TE'])]
    if pos_sub != "ALL OFFENSE": df_o = df_o[df_o['position'] == pos_sub]
    render_board_table(df_o)

with tab_def:
    if include_idp:
        def_sub = st.radio("Defense Filter:", ["ALL DEFENSE & IDP", "LB", "DL", "DB", "DEF"], horizontal=True)
        df_d = df_unpicked[df_unpicked['position'].isin(['LB', 'DL', 'DB', 'DEF'])]
        if def_sub != "ALL DEFENSE & IDP": df_d = df_d[df_d['position'] == def_sub]
    else:
        df_d = df_unpicked[df_unpicked['position'] == 'DEF']
    render_board_table(df_d)

with tab_intel:
    df_i = df_unpicked[df_unpicked['intel_note'] != ""]
    st.markdown(f"**Showing {len(df_i)} active players with verified live news, beat insights, or injury alerts:**")
    render_board_table(df_i)

with tab_matrix:
    st.markdown("#### 🧠 RIVAL DRAFTER INTELLIGENCE & TACTICAL EXPLOITS")
    
    def classify_manager_archetype(data, slot_num):
        spent = data['spent']
        picks = data['picks']
        bids = sorted(data['bid_history'], reverse=True)
        idp_spent = data['itemized_spent']['IDP']
        total_picks_in_room = len(st.session_state.drafted_picks)
        mgr_display = data['name']
        
        def_p = SOULJA_SOULJA_DEFAULTS.get(slot_num, {
            "name": mgr_display, "archetype": "⚖️ Balanced Accumulator",
            "class": "arch-balanced", "bias": "Standard Spread", "exploit": "Monitor early nominations."
        })
        hist_title = def_p['archetype']
        hist_class = def_p['class']
        hist_exploit = f"<b>{def_p['bias']}:</b> {def_p['exploit']}"

        if spent >= 100 or (len(bids) >= 1 and bids[0] >= 55) or (len(bids) >= 2 and (bids[0] + bids[1]) >= 85):
            return "👑 Stars & Scrubs (Live)", "arch-stars", f"<b>{mgr_display}:</b> Blew budget on top anchors (${spent} spent). Let him exhaust capital; push next wants to full fair value."
        elif idp_spent >= 10 or (data['pos_counts']['IDP'] >= 2 and idp_spent >= 6):
            return "🛡️ IDP Spender (Live)", "arch-idp", f"<b>{mgr_display}:</b> Overpaying on defensive assets. Nominate top LBs/DLs early to drain offensive budget."
        elif total_picks_in_room >= 6 and picks == 0:
            return "🐢 Active Hoarder (Live)", "arch-hoard", f"<b>{mgr_display}:</b> Sitting completely cold (${spent} spent). Nominate his primary starting positional needs to force spending."
        elif picks >= 3 and spent <= 45:
            return "🥷 Value Hunter (Live)", "arch-hoard", f"<b>{mgr_display}:</b> Accumulating cheap mid-tier assets. Contest his Tier 3 nominations directly."
        elif picks >= 3:
            return "⚖️ Balanced Spender (Live)", "arch-balanced", f"<b>{mgr_display}:</b> Spreading capital evenly across tiers. Avoid bidding wars on non-target positions."
        else:
            return f"📜 {hist_title} (Historical)", hist_class, hist_exploit

    matrix_rows = []
    for s, data in manager_wallets.items():
        c_left = 200 - data['spent']
        s_left = total_roster_slots - data['picks']
        m_bid = max(1, c_left - (s_left - 1))
        counts = data['pos_counts']
        needs = []
        if counts['QB'] < (2 if qb_format == '⚡ Superflex / 2-QB' else 1): needs.append(f"QB ({counts['QB']})")
        if counts['RB'] < 3: needs.append(f"RB ({counts['RB']}/3)")
        if counts['WR'] < 3: needs.append(f"WR ({counts['WR']}/3)")
        if counts['TE'] < 1: needs.append(f"TE ({counts['TE']}/1)")
        if include_idp and counts['IDP'] < 3: needs.append(f"IDP ({counts['IDP']}/3)")
        if counts['DEF'] < 1: needs.append(f"DEF ({counts['DEF']}/1)")
        needs_str = ", ".join(needs) if needs else "✅ Lineup Filled"
        
        arch_title, arch_class, exploit_text = classify_manager_archetype(data, s)
        mgr_name = data['name']
        
        if draft_mode == "🔨 Auction / Salary Cap":
            threat_level = "🟢 LOW"
            if m_bid >= 35 and any(pos in needs_str for pos in ['QB', 'RB', 'WR']): threat_level = "🔴 EXTREME"
            elif m_bid >= 20: threat_level = "🟡 MEDIUM"
            metric_col_name = "Max Bid"
            metric_val = f"${m_bid}"
        else:
            next_turn_diff = abs(s - snake_on_clock_team)
            threat_level = "🔴 ON CLOCK" if s == snake_on_clock_team else ("🟡 UP NEXT" if next_turn_diff <= 2 else "🟢 WAITING")
            metric_col_name = "Draft Slot"
            metric_val = f"Slot #{s}"
            
        roster_str = ", ".join(data['roster'][-3:]) if data['roster'] else "None"
        
        matrix_rows.append({
            "Slot": s,
            "Manager": f"⭐ YOU ({mgr_name})" if s == my_slot else f"<b>{mgr_name}</b> (Slot {s})",
            "Cash Left": f"${c_left}",
            metric_col_name: metric_val,
            "Picks": data['picks'],
            "Draft Archetype": f'<span class="arch-badge {arch_class}">{arch_title}</span>',
            "Threat": threat_level,
            "Urgent Needs": needs_str,
            "Tactical Counter-Exploit": exploit_text,
            "Recent Picks": roster_str
        })
    
    st.write(pd.DataFrame(matrix_rows).to_html(escape=False, index=False), unsafe_allow_html=True)
    
    # Visual Analytics Section
    st.markdown("---")
    st.markdown("##### 📊 Visual League Analytics: Purchasing Power & Spending Distributions")
    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        top3_hist_df = pd.DataFrame([
            {"Manager": "Kopite", "Top-3 Spend ($)": 155.5},
            {"Manager": "Chaitu", "Top-3 Spend ($)": 133.0},
            {"Manager": "Bluewatermelon", "Top-3 Spend ($)": 126.5},
            {"Manager": "Harsha", "Top-3 Spend ($)": 125.5},
            {"Manager": "Balaji", "Top-3 Spend ($)": 122.0},
            {"Manager": "Addy Rao", "Top-3 Spend ($)": 119.0},
            {"Manager": "Vivek", "Top-3 Spend ($)": 112.0},
            {"Manager": "Shantanu", "Top-3 Spend ($)": 107.5},
            {"Manager": "Siddanth", "Top-3 Spend ($)": 104.0},
            {"Manager": "Siddu", "Top-3 Spend ($)": 89.5}
        ]).set_index("Manager")
        st.bar_chart(top3_hist_df)
            
    with chart_col2:
        live_spend_df = pd.DataFrame([{
            "Manager": data['name'],
            "Cash Left": 200 - data['spent'],
            "Max Single Bid": max(1, (200 - data['spent']) - ((total_roster_slots - data['picks']) - 1))
        } for data in manager_wallets.values()]).set_index("Manager")
        st.bar_chart(live_spend_df)

with tab_log:
    if st.session_state.drafted_picks:
        log_rows = [{
            "Player": v["player_name"], 
            "Pos": v.get("position", "-"), 
            "Price / Pick": f"${v['price']}" if draft_mode == "🔨 Auction / Salary Cap" else f"Pick #{v['price']}", 
            "Manager": st.session_state.custom_manager_names.get(v['team'], f"Team {v['team']}")
        } for v in st.session_state.drafted_picks.values()]
        st.table(pd.DataFrame(log_rows))
    else:
        st.info("No players drafted yet.")