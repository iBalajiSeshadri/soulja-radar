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
import draft_sim as ds
import sleeper_live as sl
try:
    from streamlit_autorefresh import st_autorefresh
    HAS_AUTOREFRESH = True
except Exception:
    HAS_AUTOREFRESH = False
try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except Exception:
    HAS_PLOTLY = False
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
    .intel-scarce { background-color: #dc262635; color: #fca5a5; padding: 2px 6px; border-radius: 4px; font-weight: 800; font-size: 0.72rem; border: 1px solid #dc2626; }

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
# ── LEAGUE PRESETS ────────────────────────────────────────────────────────────
# Bala plays 3 leagues with different rules. A preset auto-sets the format controls
# (draft mode, QB format, IDP, teams, your slot) so switching leagues is one click
# instead of re-toggling everything. Soulja is the default and unchanged. Manual
# controls remain as overrides; a live Sleeper League-ID overrides the preset.
LEAGUE_PRESETS = {
    "⭐ Soulja Soulja (main)": {
        "draft_mode": "🔨 Auction / Salary Cap",
        "qb_format": "⚡ Superflex / 2-QB",
        "idp_mode": "🛡️ Offense + IDP (Soulja)",
        "league_size": 10,
        "my_slot": 4,
        "league_id": "",
        "use_soulja_names": True,
    },
    "🐍 12-Man Snake": {
        "draft_mode": "🐍 Snake Draft",
        "qb_format": "🏈 Standard 1-QB",
        "idp_mode": "⚔️ Offense Only (Standard)",
        "league_size": 12,
        "my_slot": 1,
        "league_id": "",
        "use_soulja_names": False,
    },
    "🔗 Dynasty Superflex": {
        "draft_mode": "🔨 Auction / Salary Cap",
        "qb_format": "⚡ Superflex / 2-QB",
        "idp_mode": "⚔️ Offense Only (Standard)",
        "league_size": 12,
        "my_slot": 1,
        "league_id": "",
        "use_soulja_names": False,
    },
    "⚙️ Custom (manual)": None,   # no auto-set — use the controls below as-is
}

SOULJA_SOULJA_DEFAULTS = {
    1: {"handle": "addyrao", "name": "Addy Rao", "archetype": "🐢 Patient Value Shark", "class": "arch-hoard", "bias": "See fitted 3yr behavior", "exploit": "Holds budget until mid-round deflation; surged to 2025 #3 finish with league-high 2,537 pts. Nominate his starting targets early to force spend."},
    2: {"handle": "skongara", "name": "Shantanu", "archetype": "👑 Stud Anchor + Value Weapons", "class": "arch-stars", "bias": "See fitted 3yr behavior", "exploit": "2025 champion (73.2% win rate, 2,443.4 avg pts). Secures 1 stud at ~$50, then dominates the $25-$33 tier. Push his secondary targets to full fair value."},
    3: {"handle": "bluewatermelon", "name": "Bluewatermelon", "archetype": "🛡️ Top-Heavy / Depth Starved", "class": "arch-idp", "bias": "See fitted 3yr behavior", "exploit": "Spends $102-$136 on 3 stars, starving bench depth ($2,163.7 pts). Secure deflated Tier 1/2 players while he sits on empty cap."},
    4: {"handle": "DjBallz", "name": "Balaji (You)", "archetype": "👑 Disciplined Anchor (VORP Surplus)", "class": "arch-stars", "bias": "See fitted 3yr behavior", "exploit": "1 Stud Anchor + disciplined surplus spread and IDP value snipes; avoids emotional bidding wars."},
    5: {"handle": "vnayini", "name": "Vivek", "archetype": "⚖️ Mid-Tier Value Optimizer", "class": "arch-balanced", "bias": "See fitted 3yr behavior", "exploit": "Constructs high-floor rosters in $32-$42 range with zero $50+ studs (2025 #4, 2024 #5). Nominate his key positions early to disrupt planned values."},
    6: {"handle": "Kopite", "name": "Kopite", "archetype": "🔥 Extreme Stud Triple-Dipper", "class": "arch-stars", "bias": "See fitted 3yr behavior", "exploit": "2025 runner-up (66.1% win rate, 2,428.2 avg pts). Spent $163 on Saquon ($56), Allen ($55), Chase ($52) in '25. Force him to pay full retail on his 2nd/3rd stud."},
    7: {"handle": "chaituat", "name": "Chaitu", "archetype": "💥 High-Spend Aggressor", "class": "arch-stars", "bias": "$133 Flat Top-3 Spend | High Volatility", "exploit": "Spends exactly $133 on 3 stars every year ($98 on dual QBs in '24). Nominate high-cost non-targets early to burn his capital quickly."},
    8: {"handle": "cardinalsin", "name": "Harsha", "archetype": "🛡️ Dual-RB Anchor + Elite IDP", "class": "arch-idp", "bias": "See fitted 3yr behavior", "exploit": "Spent $106 on Bijan/Breece in '24 + heavy IDP/TE budget. Reached 2024 finals (#2). Nominate top LBs/TEs early to burn offensive cap."},
    9: {"handle": "rookieqbme", "name": "Siddanth", "archetype": "🥷 Post-Cliff Value Sniper", "class": "arch-hoard", "bias": "See fitted 3yr behavior", "exploit": "Waits out the initial stud spike to grab post-cliff bargains ($24-$29 range). Trigger positional runs to force him into suboptimal reaches."},
    10: {"handle": "siddharthasagar", "name": "Siddu", "archetype": "👑 High-Ceiling Value Builder", "class": "arch-stars", "bias": "See fitted 3yr behavior", "exploit": "Won 2024 Championship on $74 top-3 spend + elite IDP depth ($2,439.5 avg pts). Bait with overvalued landmines; avoid bidding wars on his target anchors."}
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
# Live-draft state
if "live_connected" not in st.session_state:
    st.session_state.live_connected = False
if "live_draft_id" not in st.session_state:
    st.session_state.live_draft_id = ""
if "live_info" not in st.session_state:
    st.session_state.live_info = {}
if "live_pick_count" not in st.session_state:
    st.session_state.live_pick_count = -1
if "live_slot_map" not in st.session_state:
    st.session_state.live_slot_map = {}

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
    # SANITIZE: custom_rank/search_rank use a 9999999 sentinel for unranked players
    # (deep IDP, backups with no real ADP). That sentinel leaks into ADP-surplus math
    # (board_rank - adp) and produces absurd "+9999884 spots value" steals. Mark any
    # player at/above a sane ADP ceiling as HAVING NO ADP (NaN) so ADP-based cards
    # (snake "steals at ADP", spots-value) can exclude them instead of ranking garbage.
    _ADP_SENTINEL = 900  # anything >= this is not a real ADP
    df['has_adp'] = df['market_adp'] < _ADP_SENTINEL
    df.loc[~df['has_adp'], 'market_adp'] = _ADP_SENTINEL  # clamp for display, but has_adp=False

    # NOTE: market_adp is derived from the CURRENT board's custom_rank (live
    # Sleeper search_rank + FFToday consensus, refreshed each sync) — i.e. present
    # 2026 projections/tiers, NOT last year's prices. We deliberately do NOT
    # overlay historical ADP here: stale prices would wrongly outrank players whose
    # value moved (rookies, breakouts, injuries). The 3yr history is used only for
    # MANAGER behavior (aggression/depth/premium), which is stable year-over-year.

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

@st.cache_data(show_spinner=False)
def load_auction_fit():
    """League auction behavior fitted from 3yr history: per-handle aggression +
    stud price premium. Replaces hardcoded archetype-class aggression guesses."""
    if not os.path.exists("auction_fit.json"):
        return {}
    try:
        return json.load(open("auction_fit.json"))
    except Exception:
        return {}

auction_fit = load_auction_fit()

@st.cache_data(show_spinner=False)
def load_vacated_roles():
    """Deterministic vacated targets/carries (2025 usage vs 2026 rosters) — the
    grounded tier-jumper signal. Maps clean_name -> inherited volume + who left."""
    if not os.path.exists("vacated_roles.json"):
        return {}
    try:
        return json.load(open("vacated_roles.json")).get("players", {})
    except Exception:
        return {}

vacated_roles = load_vacated_roles()

def stud_premium_for_rank(overall_rank):
    """Market premium over engine-fair for a top overall player (decays to ~1.0
    by ~rank 25), fitted from real winning bids. Used to reflect that the market
    pays up for elites the VORP-share fair value under-prices."""
    pbr = auction_fit.get("premium_by_rank", {})
    key = str(int(overall_rank))
    if key in pbr:
        return float(pbr[key])
    base = float(auction_fit.get("stud_premium", 1.0))
    if overall_rank <= 3:
        return base
    if overall_rank >= 25:
        return 1.0
    # linear decay from base (rank 3) to 1.0 (rank 25)
    return round(1.0 + (base - 1.0) * (25 - overall_rank) / 22.0, 3)

def league_market_cost(position, pos_rank):
    """Predicted winning bid from league history for a player at positional rank.
    Falls back to None when no fitted curve exists for that position."""
    cv = market_curves.get(position)
    if not cv:
        return None
    a, b, c = cv.get("a", 0), cv.get("b", 0), cv.get("c", 0)
    pts = cv.get("points", {})
    key = str(int(pos_rank))
    # Prefer the ACTUAL empirical sale price for the top ranks (1-3) where precision
    # matters most and the smooth exp curve slightly under-fits the real top prices
    # (esp. premium SF QBs). Use the fitted curve deeper where it tracks well.
    if key in pts and pos_rank <= 3:
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

# ═══════════════════════ 🔴 LIVE DRAFT CONNECTION ═══════════════════════════
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔴 Live Draft")
_live_id_input = st.sidebar.text_input(
    "Sleeper League ID", value=st.session_state.live_draft_id or LEAGUE_ID,
    help="Paste your Sleeper LEAGUE id (from the league URL). The app finds the draft automatically.")

_lc1, _lc2 = st.sidebar.columns(2)
with _lc1:
    if st.button("🔴 Connect", use_container_width=True, type="primary"):
        info = sl.resolve_draft(_live_id_input)
        if info.get("ok") and info.get("draft_id"):
            st.session_state.live_connected = True
            st.session_state.live_draft_id = _live_id_input.strip()
            st.session_state.live_info = info
            st.session_state.live_slot_map = sl.slot_manager_map(info.get("league_id") or _live_id_input.strip())
            st.session_state.live_pick_count = -1  # force first reconcile
            st.toast(f"🟢 Connected — {info['type']} draft, {info.get('status')}", icon="🔴")
        else:
            st.sidebar.error(f"Couldn't resolve draft: {info.get('error') or 'check the League ID'}")
        st.rerun()
with _lc2:
    if st.button("⏹️ Disconnect", use_container_width=True):
        st.session_state.live_connected = False
        st.rerun()

live_mode = st.session_state.live_connected
live_info = st.session_state.live_info if live_mode else {}

# Auto-detect format from the connected draft (auction vs snake).
_detected_mode = None
if live_mode and live_info.get("type"):
    _detected_mode = "🔨 Auction / Salary Cap" if live_info["type"] == "auction" else "🐍 Snake Draft"

if live_mode:
    _stt = live_info.get("status", "?")
    _dot = "🟢" if _stt == "drafting" else ("🟡" if _stt == "pre_draft" else "⚪")
    st.sidebar.caption(f"{_dot} Live: **{live_info.get('type','?')}** · {_stt} · "
                       f"{live_info.get('teams','?')} teams · draft `{str(live_info.get('draft_id',''))[-6:]}`")
    # Adaptive poll: refresh every 2s, but the heavy redraw is gated on pick-count
    # change below, so idle polls are cheap and bursts are caught in one reconcile.
    if HAS_AUTOREFRESH and _stt != "complete":
        st_autorefresh(interval=2000, key="live_poll")
    elif not HAS_AUTOREFRESH:
        st.sidebar.warning("Auto-refresh unavailable — tap 🔄 after each pick.")
        if st.sidebar.button("🔄 Refresh picks", use_container_width=True):
            st.session_state.live_pick_count = -1
            st.rerun()

# LEAGUE PRESET selector — pick a league and its rules auto-fill the controls below
# (Soulja is default). Manual controls remain as overrides. A live Sleeper draft
# still overrides draft mode. Placed before Draft Format so it can drive its default.
_preset_names = list(LEAGUE_PRESETS.keys())
if "active_preset" not in st.session_state:
    st.session_state.active_preset = _preset_names[0]
_chosen_preset = st.sidebar.selectbox(
    "🏟️ League:", _preset_names,
    index=_preset_names.index(st.session_state.active_preset),
    disabled=live_mode,
    help="Switch leagues — auto-sets draft mode, teams, QB format, IDP, and your "
         "slot. Choose 'Custom' to set everything manually. Live draft overrides.")
_preset = LEAGUE_PRESETS.get(_chosen_preset)
if _chosen_preset != st.session_state.active_preset:
    # reset the format widgets so they re-init to the new league's defaults
    for _k in ("qb_format_ctl", "idp_mode_ctl", "league_size_ctl", "my_slot_ctl", "draft_mode_ctl"):
        st.session_state.pop(_k, None)
    st.session_state.active_preset = _chosen_preset
    if _preset and _preset.get("use_soulja_names"):
        st.session_state.custom_manager_names = {s: p["name"] for s, p in SOULJA_SOULJA_DEFAULTS.items()}
    elif _preset is not None:
        st.session_state.custom_manager_names = {i: f"Team {i}" for i in range(1, _preset["league_size"] + 1)}
    st.rerun()

_dm_opts = ["🔨 Auction / Salary Cap", "🐍 Snake Draft"]
_preset_dm = (_preset or {}).get("draft_mode", "🔨 Auction / Salary Cap")
# live detection wins; else preset default
_dm_default = (_detected_mode if (live_mode and _detected_mode) else _preset_dm)
draft_mode = st.sidebar.radio(
    "Draft Format:", _dm_opts, horizontal=True,
    index=_dm_opts.index(_dm_default) if _dm_default in _dm_opts else 0,
    disabled=live_mode,
    help="Auto-detected from your live draft when connected." if live_mode else "Set by your League preset — change it here to override.")
if live_mode and _detected_mode:
    draft_mode = _detected_mode

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ League Format Controls")

# defaults from preset (fall back to Soulja values when Custom)
_pd_qb = (_preset or {}).get("qb_format", "⚡ Superflex / 2-QB")
_pd_idp = (_preset or {}).get("idp_mode", "🛡️ Offense + IDP (Soulja)")
_pd_size = (_preset or {}).get("league_size", 10)
_pd_slot = (_preset or {}).get("my_slot", 4)

_qb_opts = ["⚡ Superflex / 2-QB", "🏈 Standard 1-QB"]
_idp_opts = ["🛡️ Offense + IDP (Soulja)", "⚔️ Offense Only (Standard)"]
qb_format = st.sidebar.radio("QB Roster Format:", _qb_opts,
    index=_qb_opts.index(_pd_qb), horizontal=True, key="qb_format_ctl")
idp_mode = st.sidebar.radio("Defensive Format:", _idp_opts,
    index=_idp_opts.index(_pd_idp), horizontal=True, key="idp_mode_ctl")
include_idp = (idp_mode == "🛡️ Offense + IDP (Soulja)")

league_size = st.sidebar.number_input("League Teams:", min_value=8, max_value=16,
    value=_pd_size, key="league_size_ctl")
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
    value=min(_pd_slot, league_size),
    format="%d",
    key="my_slot_ctl",
)
my_manager_display = st.session_state.custom_manager_names.get(my_slot, f"Team {my_slot}")
st.sidebar.caption(f"Drafting as: **{my_manager_display}** (Slot {my_slot})")

# (Legacy "Connection Mode" radio removed — the 🔴 Live Draft panel now handles
# live connection, and mock/manual tools live in the Practice expander.)

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
# SUPERFLEX QB reconciliation: pure VORP underweights elite QBs in 2-QB formats
# because the replacement bar (QB20) is itself a high-scoring starter — so Allen's
# dyn_vorp (~94) trails an elite RB's (~147) even though the LEAGUE pays MORE for
# the QB. That's a real, data-backed superflex scarcity premium that VORP misses,
# and it made Fair ($~37) contradict the correct market/Likely ($~57). Blend QB
# fair toward the empirical league market so the two stop fighting. Format-gated:
# only in superflex; standard 1-QB keeps pure VORP fair.
if qb_format != "🏈 Standard 1-QB":
    _qbm = df_board['position'] == 'QB'
    for _qi, _qr in df_board[_qbm].iterrows():
        _qrank = int((df_board[_qbm]['proj_fpts'] > _qr['proj_fpts']).sum()) + 1
        _qmkt = league_market_cost('QB', _qrank)
        if _qmkt:
            # 55% market / 45% VORP-fair — respects scarcity premium without fully
            # abandoning value discipline (so Fair still flags true overpays).
            _blended = 0.55 * float(_qmkt) + 0.45 * float(_qr['fair_value'])
            df_board.at[_qi, 'fair_value'] = max(1, int(round(_blended)))
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

# ── SNAKE VONA (Value Over Next Available at MY next pick) ─────────────────────
# Snake has no dollars: value = whether a comparable player at this position will
# still be there when the serpentine wheel returns to me. VONA = this player's
# dyn_vorp minus the dyn_vorp of the best same-position player expected to survive
# until my NEXT pick. High VONA = real positional cliff (draft now); low VONA =
# depth remains, so wait. Picks-until-next-pick uses the snake round-trip gap.
df_board['vona'] = 0.0
df_board['picks_to_next'] = 0
if draft_mode == "🐍 Snake Draft":
    _picked_ct = len(st.session_state.get("drafted_picks", {}))
    _cur_pick = _picked_ct + 1                       # overall pick number on the clock
    _rnd = (_cur_pick - 1) // league_size            # 0-based round
    _slot_in_rnd = (_cur_pick - 1) % league_size + 1 # 1-based position in this round
    # snake: even rounds (0-based) go 1..N, odd rounds go N..1
    # compute overall number of MY next pick after the current clock position.
    def _my_overall_picks(n_rounds):
        picks = []
        for r in range(n_rounds):
            if r % 2 == 0:                            # L->R
                picks.append(r * league_size + my_slot)
            else:                                     # R->L
                picks.append(r * league_size + (league_size - my_slot + 1))
        return picks
    _my_picks = _my_overall_picks(40)
    _my_next = next((p for p in _my_picks if p >= _cur_pick), _cur_pick)
    _my_after = next((p for p in _my_picks if p > _my_next), _my_next + 2 * league_size)
    _gap = max(1, _my_after - _my_next)              # picks between my next and the one after
    df_board['picks_to_next'] = _gap
    # Expected # of players at each position taken in that gap ~ position's recent
    # share of picks (fallback to a flat share). Then best available after the gap.
    _picked_names = set(st.session_state.get("drafted_picks", {}).keys())
    _avail = df_board[~df_board['clean_name'].isin(_picked_names)]
    for _p in df_board['position'].unique():
        _pm = df_board['position'] == _p
        _pool = _avail[_avail['position'] == _p].sort_values('dyn_vorp', ascending=False)
        if len(_pool) == 0:
            continue
        # crude survival: assume ~ (position share of a typical board) of the gap
        # picks hit this position. Share by pool size relative to all available.
        _share = len(_pool) / max(1, len(_avail))
        _expected_gone = int(round(_gap * _share))
        _next_idx = min(_expected_gone, len(_pool) - 1)
        _next_best_vorp = float(_pool.iloc[_next_idx]['dyn_vorp'])
        df_board.loc[_pm, 'vona'] = df_board.loc[_pm, 'dyn_vorp'] - _next_best_vorp
df_board = df_board.sort_values(by=['fair_value', 'live_vorp'], ascending=[False, False]).reset_index(drop=True)
df_board['board_rank'] = df_board.index + 1

# --- FFA multi-source second-opinion (optional, additive) ---
# If ffa_second_opinion.csv is present (generated offline by _ffa_flag.py from Isaac
# Petersen's ffanalytics multi-source robust projections, compared on a scoring-agnostic,
# same-pool z-score basis), attach a grounded consensus flag. Purely a second opinion —
# never overrides our fair_value/VORP. Absent file = feature silently off.
df_board['ffa_flag'] = ""
try:
    import os as _os
    if _os.path.exists("ffa_second_opinion.csv"):
        _fo = pd.read_csv("ffa_second_opinion.csv")
        _fo_map = dict(zip(_fo['clean'], _fo['ffa_flag']))
        df_board['ffa_flag'] = df_board['clean_name'].map(_fo_map).fillna("")
except Exception:
    df_board['ffa_flag'] = ""

# --- LIVE Sleeper depth-chart refresh (team + depth) so ALL cards use accurate
# roster data, + grounded RB handcuffs. Cached 6h; on any failure we keep the
# board exactly as-is (feature silently off, never crashes the app). ---
@st.cache_data(ttl=21600, show_spinner=False)
def load_sleeper_depth():
    return sl.fetch_players_nfl(clean_name)

_players_nfl = load_sleeper_depth()
df_board['handcuff'] = ""
df_board['handcuff_on_board'] = False
if _players_nfl:
    _bset = set(df_board['clean_name'])
    _by = _players_nfl.get('by_clean', {})
    for _idx, _r in df_board.iterrows():
        _lv = _by.get(_r['clean_name'])
        # refresh team + depth from live Sleeper (keep board value if missing)
        if _lv:
            if _lv.get('team'):
                df_board.at[_idx, 'team'] = _lv['team']
            if _lv.get('depth') is not None:
                df_board.at[_idx, 'depth_chart_order'] = _lv['depth']
        # grounded handcuff for lead-back RBs (confidence-guarded)
        if _r['position'] == 'RB':
            _hc = sl.handcuff_for(_r['clean_name'], df_board.at[_idx, 'team'],
                                  _players_nfl, _bset, clean_name)
            if _hc and _hc.get('confident'):
                df_board.at[_idx, 'handcuff'] = _hc['name']
                df_board.at[_idx, 'handcuff_on_board'] = bool(_hc['on_board'])

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
    # 🔥 tier-ender scarcity flag (shared df_board['tier_ender']) — shows on every
    # tab/card, not just the bid verdict, so scarce players are flagged everywhere.
    if bool(r.get('tier_ender', False)):
        _cliff = int(r.get('tier_cliff', 0))
        te_html = (f'<span class="intel-scarce">🔥 LAST IN TIER</span> '
                   f'<span class="intel-note">${_cliff} cliff after — bidding-war risk</span>')
        body = f"{body}<br>{te_html}" if body and body != "—" else te_html
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

if live_mode:
    # ── LIVE RECONCILE (burst-safe, change-gated) ─────────────────────────────
    _did = live_info.get("draft_id")
    _is_auction = (live_info.get("type") == "auction")
    _raw = sl.fetch_picks(_did)
    _recs, _cnt = sl.reconcile_picks(_raw, clean_name, pos_map=player_pos_map,
                                     display_map=player_display_map, is_auction=_is_auction)
    # Rebuild the FULL pick set every poll so a burst of picks between polls can't
    # desync us. Cheap when nothing changed; the UI only "reacts" on count change.
    _new_picks = {}
    for r in _recs:
        _new_picks[r["clean_name"]] = {"price": r["price"], "team": r["team"],
                                       "player_name": r["player_name"], "position": r["position"],
                                       "pick_no": r["pick_no"]}
    st.session_state.drafted_picks = _new_picks
    # map draft slots -> named managers (populates once draft order is set)
    if st.session_state.live_slot_map:
        for _slot, _nm in st.session_state.live_slot_map.items():
            disp = _nm
            for _di in SOULJA_SOULJA_DEFAULTS.values():
                if _di.get("handle", "").lower() == str(_nm).lower():
                    disp = _di["name"]; break
            st.session_state.custom_manager_names[_slot] = disp
    if _cnt != st.session_state.live_pick_count:
        st.session_state.live_pick_count = _cnt   # note the change; render reflects it
    st.sidebar.caption(f"📥 {_cnt} picks synced from Sleeper.")
else:
    # ── PRACTICE / MOCK tools (tucked away so live UI stays clean) ─────────────
    with st.sidebar.expander("⚙️ Practice / Mock (not live)", expanded=False):
        st.caption("Simulate picks to rehearse. Connect a live draft above for the real thing.")
        col_s1, col_s2 = st.columns(2)
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
                        "player_name": target_p['player_name'], "position": target_p['position']}
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
                        "player_name": target_p['player_name'], "position": target_p['position']}
                st.rerun()
        if st.button("🗑️ Reset Board", use_container_width=True):
            st.session_state.drafted_picks = {}
            st.session_state.last_ai_read = ""
            st.session_state.last_ai_nom = ""
            st.rerun()

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

# ══ CONSISTENCY LAYER — single source of truth for rank & price ═══════════════
# Recompute positional rank + market_cost over AVAILABLE players so EVERY card
# (board table, verdict, arbitrage, build plan) reads the same number. Previously
# market_cost was frozen at build (full-board rank incl. drafted) while the verdict
# used available-pool rank — they drifted mid-draft. Now they can't.
_avail_pos_rank = {}   # clean_name -> positional rank among available players
for _cp in ['QB', 'RB', 'WR', 'TE', 'LB', 'DL', 'DB', 'DEF']:
    _cpool = df_unpicked[df_unpicked['position'] == _cp].sort_values('proj_fpts', ascending=False)
    for _ri, _cn in enumerate(_cpool['clean_name'].tolist(), start=1):
        _avail_pos_rank[_cn] = _ri
# refresh market_cost on the FULL board from available-pool rank (offense via the
# fitted league curve; IDP/DEF keep their tier-based cost set at build).
for _idx2, _row2 in df_board.iterrows():
    _cn2 = _row2['clean_name']
    if _row2['position'] in ('QB', 'RB', 'WR', 'TE') and _cn2 in _avail_pos_rank:
        _mc2 = league_market_cost(_row2['position'], _avail_pos_rank[_cn2])
        if _mc2:
            df_board.at[_idx2, 'market_cost'] = int(_mc2)
df_board['pos_rank_avail'] = df_board['clean_name'].map(_avail_pos_rank).fillna(99).astype(int)

def get_market_price(clean_or_row):
    """SINGLE source for a player's league market price. Accepts a clean_name or a
    board row. Uses available-pool positional rank so every card agrees."""
    if isinstance(clean_or_row, str):
        _r = df_board[df_board['clean_name'] == clean_or_row]
        if _r.empty:
            return None
        _r = _r.iloc[0]
    else:
        _r = clean_or_row
    _rk = _avail_pos_rank.get(_r['clean_name'], 99)
    if _r['position'] in ('QB', 'RB', 'WR', 'TE'):
        return league_market_cost(_r['position'], _rk) or int(_r.get('market_cost', 1))
    return int(_r.get('market_cost', 1))

def player_price(clean_or_row):
    """CANONICAL price for a player — the SINGLE source used by the verdict AND
    every advisor card AND board tables, so the same player shows the same price
    everywhere. Returns {fair, market, likely, ceiling}:
      fair    = engine VORP-share fair value (inflation-adjusted)
      market  = league historical price for this player's available-pos rank
      likely  = what it'll realistically sell for (league-anchored, premium-aware)
      ceiling = your walk-away bid (likely + tier-ender premium, capped)
    Cheap (no Monte-Carlo) so it's safe to call per-row across tables."""
    if isinstance(clean_or_row, str):
        _q = df_board[df_board['clean_name'] == clean_or_row]
        if _q.empty:
            return {"fair": 1, "market": 1, "likely": 1, "ceiling": 1}
        _r = _q.iloc[0]
    else:
        _r = clean_or_row
    _fairv = int(_r.get('fair_value', 1))
    _mkt = int(get_market_price(_r) or _fairv)
    # likely = league market is the ground truth for the tier; nudge toward fair
    # only when fair is higher (e.g. a stud the market hasn't caught up to).
    _lik = int(round(0.75 * _mkt + 0.25 * max(_fairv, _mkt)))
    _prem = 5 if bool(_r.get('tier_ender', False)) else 0   # TIER_END_PREMIUM
    _ceil = _lik + _prem
    return {"fair": _fairv, "market": _mkt, "likely": _lik, "ceiling": _ceil}

df_unpicked = df_board[~df_board['clean_name'].isin(picked_clean_names)].copy()  # refresh w/ updated cols

# ── SHARED tier-ender flag (single source of truth for every card) ────────────
# A player is a "tier-ender" if the league-market price gap to the next-cheaper
# AVAILABLE player at their position is a real cliff (>=$8) — the scarcity point
# where the room panics and overpays. Computed once here so the verdict, board
# table, and cliff tracker all read the SAME value (no duplicated/inconsistent logic).
df_board['tier_ender'] = False
df_board['tier_cliff'] = 0
_TIER_CLIFF = 8
for _tpos in ['QB', 'RB', 'WR', 'TE']:
    _tp = df_unpicked[df_unpicked['position'] == _tpos].sort_values('proj_fpts', ascending=False)
    for _i, (_idx, _r) in enumerate(_tp.iterrows(), start=1):
        _this = league_market_cost(_tpos, _i) or int(_r['fair_value'])
        _nxt = league_market_cost(_tpos, _i + 1) or 0
        _cliff = int((_this or 0) - (_nxt or 0))
        if _cliff >= _TIER_CLIFF:
            df_board.at[_idx, 'tier_ender'] = True
            df_board.at[_idx, 'tier_cliff'] = _cliff
df_unpicked = df_board[~df_board['clean_name'].isin(picked_clean_names)].copy()  # refresh with flag

remaining_league_cash = (league_size * 200) - total_cash_spent
unpicked_fair_sum = df_unpicked['fair_value_base'].sum() if 'fair_value_base' in df_unpicked else df_unpicked['fair_value'].sum()
# Use the single live inflation index computed at valuation time (fair_value is
# already inflated by it, so recomputing off inflated values would double-count).
inflation_index = round(float(df_board['live_inflation'].iloc[0]) if 'live_inflation' in df_board and len(df_board) else 1.0, 2)
my_wallet = manager_wallets.get(my_slot, {"spent": 0, "picks": 0})
my_cap_left = 200 - my_wallet['spent']
my_slots_left = total_roster_slots - my_wallet['picks']
my_max_bid = max(1, my_cap_left - (my_slots_left - 1))

# ── RUN DETECTOR + RIVAL DEMAND + ROSTER-NEED (shared: auction & snake) ────────
# 1) Run velocity: share of the LAST ~league_size picks that hit each position —
#    a spike means a positional run is underway (pay up / act before the cliff).
# 2) Rival demand: how many OTHER teams still haven't filled their starting slots
#    at each position (more unmet demand => more competition => value holds/ rises).
# 3) My roster need: my own open starting slots by position (boost value for spots
#    I still must fill; decay once filled).
_start_req = {'QB': (2 if qb_format == "⚡ Superflex / 2-QB" else 1),
              'RB': 2, 'WR': 3, 'TE': 1, 'IDP': 4 if include_idp else 0, 'DEF': 1}

def _bucket(pos):
    return 'IDP' if pos in ('LB', 'DL', 'DB') else pos

# recent picks (preserve insertion order of drafted_picks; last N)
_all_picks = list(st.session_state.get("drafted_picks", {}).items())
_recent = _all_picks[-league_size:] if len(_all_picks) >= 1 else []
_run_counts = {}
for _cn, _pd in _recent:
    _bp = _bucket(_pd.get("position", player_pos_map.get(_cn, "")))
    _run_counts[_bp] = _run_counts.get(_bp, 0) + 1
_run_share = {p: round(c / max(1, len(_recent)), 2) for p, c in _run_counts.items()}

# rival demand: for each position, how many teams (excluding me) are still below
# their starting requirement; my own need tracked separately.
pos_pressure = {}    # bucket -> {"run": share, "rivals_needing": int}
my_pos_need = {}     # bucket -> open starting slots for ME
for _b, _req in _start_req.items():
    if _req <= 0:
        continue
    _rivals_needing = 0
    for _tid, _w in manager_wallets.items():
        _have = _w["pos_counts"].get(_b, 0)
        if _tid == my_slot:
            my_pos_need[_b] = max(0, _req - _have)
        elif _have < _req:
            _rivals_needing += 1
    pos_pressure[_b] = {"run": _run_share.get(_b, 0.0), "rivals_needing": _rivals_needing}

# Roster-need multiplier applied to MY view of value: boost positions I still need
# to start, gently fade positions I've already filled. Kept mild (0.85–1.20) so it
# nudges rather than distorts. Feeds a "my_value" column used by the recs.
def _need_mult(pos):
    b = _bucket(pos)
    req = _start_req.get(b, 0)
    if req <= 0:
        return 1.0
    open_slots = my_pos_need.get(b, req)
    if open_slots <= 0:
        return 0.85                     # already have my starters here
    frac_open = open_slots / req
    return round(1.0 + 0.20 * frac_open, 3)   # up to +20% when fully unfilled

df_board['need_mult'] = df_board['position'].map(_need_mult).fillna(1.0)
# my_value = the format-appropriate base value, tilted by my roster need.
if draft_mode == "🐍 Snake Draft":
    df_board['my_value'] = df_board['vona'] * df_board['need_mult']
else:
    df_board['my_value'] = df_board['fair_value'] * df_board['need_mult']

# ── FORWARD EDGE SCORE: who is best-POSITIONED for THIS year (tier-jumpers) ────
# The real signal = MATCH data (vacated opportunity) WITH news (reality). Vacated
# volume shows the opportunity but over-credits (assumes 100% inheritance). The
# beat news CONFIRMS (clear lead) or DISCOUNTS (committee/split) it. So news
# MODULATES the vacated bonus rather than stacking on top of it.
import re as _re_edge
_SPLIT_KW = _re_edge.compile(r"\bsplit|committee|timeshare|time-share|share|rotation|"
                            r"1a|1b|tandem|competition|competing|rookie|signed|"
                            r"backfield by committee|two-back|duo\b", _re_edge.I)

def _edge_components(r):
    base = float(r.get('live_vorp', 0))
    tag = str(r.get('scheme_tag', '')).upper()
    itag = str(r.get('intel_tag', '')).upper()
    note = str(r.get('intel_note', '')).strip()
    mult = float(r.get('live_multiplier', 1.0))
    bonus = 0.0
    reasons = []
    if 'FIT' in tag:
        bonus += 12; reasons.append('scheme fit')
    if 'RISK' in tag:
        bonus -= 15; reasons.append('scheme RISK')

    _vac = vacated_roles.get(r['clean_name'])
    _vac_inh = (_vac.get('inherits_carries', 0) + _vac.get('inherits_targets', 0)) if _vac else 0
    _has_vac = bool(_vac) and _vac_inh >= 40
    _pos_news = mult > 1.03 and ('JUMPER' in itag or 'SURGE' in itag or 'BREAKOUT' in itag or note)
    _split_risk = ('PINCH' in itag) or (bool(note) and bool(_SPLIT_KW.search(note)))

    if _has_vac:
        _src = _vac.get('from', [])
        _from = _src[0].split(' (')[0] if _src else 'departure'
        _vac_desc = f"{_vac.get('inherits_carries',0)}c/{_vac.get('inherits_targets',0)}tgt from {_from}"
        _base_vac = min(25, _vac_inh / 12.0)   # opportunity size
        # MATCH with news: confirm (clear lead), discount (split), or unconfirmed
        if _pos_news and not _split_risk:
            bonus += _base_vac * 1.15            # confirmed — full/boosted
            reasons.append(f"✅ CONFIRMED lead: inherits {_vac_desc}; camp buzz backs clear role")
        elif _split_risk:
            bonus += _base_vac * 0.5             # discount — pool gets split
            reasons.append(f"⚠️ SPLIT RISK: inherits {_vac_desc} but news signals committee")
        else:
            bonus += _base_vac * 0.85            # unconfirmed opportunity
            reasons.append(f"inherits {_vac_desc} (unconfirmed — watch camp)")
    else:
        # no vacated pool → news stands on its own (camp riser / scheme buzz)
        if mult > 1.03:
            bonus += (mult - 1.0) * 120
            if 'JUMPER' in itag or 'SURGE' in itag or 'BREAKOUT' in itag:
                reasons.append('tier-jumper (cited)')
            elif note:
                reasons.append('camp riser')
        elif mult < 0.97:
            bonus -= (1.0 - mult) * 80
    # WORKHORSE SHARE (user: 'solo RB1 with low shared carries is gold'). A proven
    # bell-cow role carries over; a committee is a discount. From 2025 team share.
    _sh = vacated_roles.get(r['clean_name'], {})
    _whs = _sh.get('workhorse_share')
    if _whs is not None:
        if _whs >= 0.70:
            bonus += 10 + (_whs - 0.70) * 40      # +10 at 70%, up to ~+17 at 87%
            reasons.append(f"🐴 workhorse: {int(_whs*100)}% of team carries (bell-cow)")
        elif _whs < 0.50:
            bonus -= 6
            reasons.append(f"committee back ({int(_whs*100)}% share) — capped upside")
    _tgs = _sh.get('target_share')
    if _tgs is not None and _tgs >= 0.28:
        bonus += 8 + (_tgs - 0.28) * 40
        reasons.append(f"🎯 target hog: {int(_tgs*100)}% of team targets")
    return base + bonus, reasons

_edge_vals = df_board.apply(lambda r: _edge_components(r), axis=1)
df_board['edge_score'] = [e[0] for e in _edge_vals]
df_board['edge_reasons'] = ["; ".join(e[1]) for e in _edge_vals]
# refresh df_unpicked so downstream tabs (Edge Board, plan) see edge_score/reasons
df_unpicked = df_board[~df_board['clean_name'].isin(picked_clean_names)].copy()

def pos_run_flag(pos):
    """Return a short run/demand badge string for a position, or ''."""
    b = _bucket(pos)
    pp = pos_pressure.get(b)
    if not pp:
        return ""
    bits = []
    if pp["run"] >= 0.4:
        bits.append(f"🏃 RUN ({int(pp['run']*100)}% of last {len(_recent)} picks)")
    if pp["rivals_needing"] >= max(3, league_size // 2):
        bits.append(f"🎯 {pp['rivals_needing']} rivals still need {b}")
    return " · ".join(bits)

# Archetype spend aggression — prefer per-manager values FITTED from 3yr auction
# history (auction_fit.json), fall back to archetype-class estimates if missing.
_ARCH_AGGR = {"arch-stars": 1.45, "arch-idp": 1.15, "arch-hoard": 0.85, "arch-balanced": 1.05}

def _rival_profile(tid):
    """Full fitted profile for a rival by stable handle (aggression, pos lean,
    stud-vs-depth), falling back to archetype-class aggression if missing."""
    info = SOULJA_SOULJA_DEFAULTS.get(tid, {})
    handle = str(info.get("handle", "")).lower()
    fit = auction_fit.get("by_manager", {}).get(handle, {})
    aggr = float(fit.get("aggression", _ARCH_AGGR.get(info.get("class", "arch-balanced"), 1.05)))
    return {
        "aggression": aggr,
        "pos_lean": fit.get("pos_lean", {}),
        "top_positions": fit.get("top_positions", []),
        "nominates_early": fit.get("nominates_early", ""),
        "stud_vs_depth": fit.get("stud_vs_depth", None),
        "handle": handle,
        "name": info.get("name", handle),
    }

def _rival_aggression(tid):
    return _rival_profile(tid)["aggression"]

def build_rivals_for_sim(target_position=None):
    """Assemble the rival list draft_sim needs: each opponent's remaining cap,
    whether they still need the target position, and their FITTED aggression.
    need_at_pos now blends roster gap WITH each rival's real positional $ lean
    (a rival who historically pours money into RB will contest RB harder)."""
    rivals = []
    for _tid, _w in manager_wallets.items():
        if _tid == my_slot:
            continue
        _cap = max(0, 200 - _w["spent"])
        _needs = set()
        for _b, _req in _start_req.items():
            if _req > 0 and _w["pos_counts"].get(_b, 0) < _req:
                _needs.add(_b)
        _prof = _rival_profile(_tid)
        _aggr = _prof["aggression"]
        # need_at_pos: roster gap (0.4/1.0) nudged up by historical $ lean at pos
        _gap_need = 1.0 if (target_position and _bucket(target_position) in _needs) else 0.4
        _lean = float(_prof["pos_lean"].get(target_position, 0.0)) if target_position else 0.0
        _need_at = min(1.0, _gap_need + 0.6 * _lean)   # lean of 0.30 => +0.18
        rivals.append({"cap_left": _cap, "needs": _needs,
                       "aggression": _aggr, "need_at_pos": _need_at})
    return rivals

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
        
        # format-aware strategic context so the AI reasons correctly per mode
        _pressure_bits = []
        for _b, _pp in pos_pressure.items():
            _tags = []
            if _pp["run"] >= 0.4:
                _tags.append(f"RUN {int(_pp['run']*100)}%")
            if _pp["rivals_needing"] >= 3:
                _tags.append(f"{_pp['rivals_needing']} rivals need")
            if _tags:
                _pressure_bits.append(f"{_b}: {', '.join(_tags)}")
        _pressure_line = ("Positional pressure: " + " | ".join(_pressure_bits)) if _pressure_bits else "No active positional runs."
        _open_slots = [f"{_b}×{_n}" for _b, _n in my_pos_need.items() if _n > 0]
        _my_need_line = ("My open starting slots: " + ", ".join(_open_slots)) if _open_slots else "My starters: filled."

        if draft_mode == "🐍 Snake Draft":
            _vona_top = df_unpicked.sort_values('vona', ascending=False).head(6)
            _vona_line = "Top VONA (draft-now cliffs, value lost if you wait to your next pick): " + \
                "; ".join(f"{r['player_name']}({r['position']} VONA{r['vona']:.0f})" for _, r in _vona_top.iterrows())
            live_snapshot = (
                f"Draft Format: {draft_mode} ({qb_format})\n"
                f"You are at snake slot {my_slot}; ~{int(df_board['picks_to_next'].iloc[0]) if 'picks_to_next' in df_board and len(df_board) else '?'} picks until your wheel returns.\n"
                f"{_vona_line}\n{_pressure_line}\n{_my_need_line}\n"
                f"Your Current Roster: {', '.join(my_wallet['roster']) if my_wallet['roster'] else 'None'}\n"
                f"Rank snake advice by VONA + positional scarcity (NOT dollars). Wait on deep positions, grab cliff positions now."
            )
        else:
            live_snapshot = (
                f"Draft Format: {draft_mode} ({qb_format})\n"
                f"Your Remaining Budget: ${my_cap_left} (Max Single Bid: ${my_max_bid}, Open Slots: {my_slots_left})\n"
                f"Room Inflation Index: {inflation_index}x (>1 pay up, <1 bargains ahead)\n"
                f"{_pressure_line}\n{_my_need_line}\n"
                f"Your Current Roster: {', '.join(my_wallet['roster']) if my_wallet['roster'] else 'None'}"
            )
        
        with st.spinner("AI evaluating exact player values, VORPs, and draft room state..."):
            ans = ask_ai_strategist(ai_query, live_snapshot, telemetry_str)
            with st.chat_message("assistant", avatar="⚡"):
                st.markdown(ans)

# roster-need targets (needed by the live QoL banner + advisor below)
my_counts = my_wallet['pos_counts']
pos_targets = {'QB': 2 if qb_format == '⚡ Superflex / 2-QB' else 1, 'RB': 4, 'WR': 4, 'TE': 2, 'IDP': 4 if include_idp else 0, 'DEF': 1}
pos_gaps = {pos: max(0, target - my_counts.get(pos, 0)) for pos, target in pos_targets.items()}

if draft_mode == "🔨 Auction / Salary Cap":
    st.markdown(f"### 🏈 SALARY CAP AUCTION RADAR • `{my_manager_display}` • `{qb_format}`")

    # ══ "SHOULD I BID?" — top of console, always visible (connected or not) ════
    st.markdown("#### 🔨 SHOULD I BID?")
    _avail_names = df_unpicked.sort_values('fair_value', ascending=False)
    # Auto-default to your #1 recommended pickup so a live verdict is ALWAYS shown
    # without tapping. (Sleeper's API can't tell us who the room nominated, so you
    # only change this when a rival puts up a different player.)
    _affordable = _avail_names[_avail_names['fair_value'] <= max(1, my_max_bid)]
    _rec_pool = _affordable[_affordable['clean_name'].isin(st.session_state.my_targets)]
    if _rec_pool.empty:
        _rank_col = 'my_value' if 'my_value' in _affordable else 'fair_value'
        _rec_pool = _affordable.sort_values(_rank_col, ascending=False)
    _auto_row = _rec_pool.iloc[0] if not _rec_pool.empty else None
    _auto_label = (f"⭐ Auto: {_auto_row['player_name']} ({_auto_row['position']})"
                   if _auto_row is not None else "— no affordable target —")
    # Position filter so the picker is short & findable (a 250-long list buries
    # players like a QB in Superflex). Tap a position, then type-to-search.
    _pos_choices = ["ALL", "QB", "RB", "WR", "TE"] + (["IDP", "DEF"] if include_idp else [])
    _bid_pos = st.radio("Filter by position:", _pos_choices, horizontal=True,
                        key="bid_pos_filter", label_visibility="collapsed")
    if _bid_pos == "ALL":
        _pool_df = _avail_names
    elif _bid_pos == "IDP":
        _pool_df = _avail_names[_avail_names['position'].isin(['LB', 'DL', 'DB'])]
    else:
        _pool_df = _avail_names[_avail_names['position'] == _bid_pos]
    _player_opts = [f"{r['player_name']} ({r['position']})" for _, r in _pool_df.head(300).iterrows()]
    _opts = [_auto_label] + _player_opts
    _sel = st.selectbox("Player on the block (type to search):", _opts, index=0, key="bid_verdict_sel",
                        help="⭐ Auto = your top pickup. Filter by position + type a name to jump to the nominated player.")
    # resolve selection -> player row (auto option maps to the recommended player)
    if _sel.startswith("⭐ Auto:"):
        _prow = _rec_pool.head(1) if _auto_row is not None else _avail_names.head(0)
    else:
        _pname = _sel.rsplit(" (", 1)[0]
        _prow = _avail_names[_avail_names['player_name'] == _pname]
    if not _prow.empty:
        if True:  # (guard kept for indentation; body renders the verdict)
            _pr = _prow.iloc[0]
            _fair = int(_pr['fair_value'])
            _rv = build_rivals_for_sim(_pr['position'])
            _mc = ds.mc_auction_price({'fair_value': float(_fair), 'position': _pr['position']},
                                      _rv, my_max_bid=my_max_bid, n_sims=250, seed=int(_pr['board_rank']))
            _walk = min(my_max_bid, int(_mc['p80']))
            _likely = int(_mc['median'])
            _want = _pr['clean_name'] in st.session_state.my_targets
            _need_pos = pos_gaps.get('IDP' if _pr['position'] in ('LB','DL','DB') else _pr['position'], 0) > 0
            # MARKET-AWARE fair bar: scarce/premium players (SF QB, elite RB) cost a
            # real market premium — the fitted premium IS their fair price. So we do
            # NOT flag paying market as an "overpay". The engine's job is to tell you
            # what the market cost is and whether you can still build after paying it.
            _prem = stud_premium_for_rank(int(_pr['board_rank']))
            # Use the SHARED available-pool positional rank (pos_rank_avail) computed
            # in the consistency layer, so the verdict, board table, and arbitrage all
            # agree on rank + price. _pos_pool_avail rebuilt here only for "next player".
            _pos_pool_avail = df_unpicked[
                df_unpicked['position'].isin(['LB','DL','DB']) if _pr['position'] in ('LB','DL','DB')
                else (df_unpicked['position'] == _pr['position'])
            ].sort_values('proj_fpts', ascending=False).reset_index(drop=True)
            _pos_rank = int(_pr.get('pos_rank_avail', 99))
            _league_price = league_market_cost(_pr['position'], _pos_rank)
            # CANONICAL price — identical to what the advisor cards + board show, so
            # the verdict never disagrees with the other cards. MC only tightens the
            # walk-away upper bound for a contested stud.
            _cp = player_price(_pr)
            _likely = _cp['likely']
            _mkt_fair = max(_cp['market'], int(round(_fair * _prem)))
            _walk = min(my_max_bid, max(int(_mc['p80']), _cp['ceiling']))
            # TIER-DROP / cost-of-waiting: the NEXT player is the one immediately
            # BELOW the selected player among AVAILABLE players (not the top of the
            # pool) — so it's always a lower-ranked fallback, never a better player.
            _next_p = _pos_pool_avail.iloc[_pos_rank] if _pos_rank < len(_pos_pool_avail) else None
            TIER_END_PREMIUM = 5
            _is_tier_ender = bool(_pr.get('tier_ender', False))
            _next_price = None
            _tier_drop_txt = ""
            if _next_p is not None:
                _next_price = league_market_cost(_pr['position'], _pos_rank + 1) or int(_next_p['fair_value'])
                # Compare LIKE FOR LIKE: this player's league-market price vs the next
                # player's league-market price (both from the same curve).
                _this_mktprice = league_market_cost(_pr['position'], _pos_rank) or _fair
                _drop = max(0, int(_this_mktprice) - int(_next_price))
                if _is_tier_ender:
                    _tier_drop_txt = (f" ⚠️ You're bidding the LAST elite {_pr['position']} before a ${_drop} "
                                      f"cliff (next: {_next_p['player_name']} ~${int(_next_price)}). Expect a "
                                      f"bidding war — tier-enders historically go ~${TIER_END_PREMIUM} over. "
                                      f"Win it now or pay the panic later.")
                elif _drop >= 5:
                    _tier_drop_txt = (f" Next {_pr['position']} ({_next_p['player_name']}) ~${int(_next_price)} "
                                      f"(${_drop} cheaper — modest drop).")
                else:
                    # TOSS-UP (similar price): don't just name the next guy — say WHO'S
                    # BETTER using forward signals (edge_score fuses VORP + scheme fit/
                    # risk + vacated + workhorse). Helps pick between similar options.
                    _sel_edge = float(_pr.get('edge_score', _pr.get('live_vorp', 0)))
                    _nxt_edge = float(_next_p.get('edge_score', _next_p.get('live_vorp', 0)))
                    def _why1(rr):
                        t = str(rr.get('scheme_tag','')).upper()
                        if 'FIT' in t: return 'scheme fit'
                        if 'RISK' in t: return 'scheme risk'
                        er = str(rr.get('edge_reasons','')).split(';')[0].strip()
                        return er or str(rr.get('tier',''))
                    if _sel_edge >= _nxt_edge + 3:
                        _tier_drop_txt = (f" ✅ <b>{_pr['player_name']} is the better pick</b> vs "
                                          f"{_next_p['player_name']} (~${int(_next_price)}) — better outlook "
                                          f"({_why1(_pr)} vs {_why1(_next_p)}).")
                    elif _nxt_edge >= _sel_edge + 3:
                        _tier_drop_txt = (f" 🔀 <b>Consider {_next_p['player_name']} instead</b> (~${int(_next_price)}, "
                                          f"same price) — better outlook ({_why1(_next_p)} vs {_why1(_pr)}).")
                    else:
                        _tier_drop_txt = (f" Next {_pr['position']} ({_next_p['player_name']}) ~${int(_next_price)} "
                                          f"— basically a coin-flip ({_why1(_pr)} vs {_why1(_next_p)}); take either or wait.")
            # Bid ceiling = canonical ceiling (already includes the tier-ender
            # premium), bounded by the MC walk-away and your max bid. No double-add.
            _bid_ceiling = min(my_max_bid, max(_cp['ceiling'], int(_mc['p80']) if _is_tier_ender else _cp['ceiling']))
            # #3 YOUR EDGE (user-confirmed anecdote): user reliably lands the QB
            # second wave (QB4-6, e.g. Lamar goes ~4th, Burrow) cheap. When a
            # second-wave QB is up and QB is a need, nudge to pounce over top-3.
            _qb_edge = (_pr['position'] == 'QB' and 4 <= _pos_rank <= 7 and _need_pos)
            _edge_txt = (" 🎯 <b>YOUR EDGE:</b> you land this QB tier cheap most years "
                         "(Lamar/Burrow pattern) — pounce here, don't chase the top-3." if _qb_edge else "")
            # #WR value zone (user-confirmed): WR1-2 go high, then WR3->4 drop opens a
            # long value tier (~WR4+) where camp-riser tier-jumpers (JSN) become steals.
            # #WR value zone (user-confirmed): after the top studs, a mid-tier WR
            # becomes a JSN-type steal ONLY if it's a genuine flier — a real riser
            # signal (camp intel or vacated targets) AND not an elite established
            # stud (high tier / high VORP). Don't fire on ARSB-caliber WRs.
            import re as _re_tier
            def _tnum2(t):
                m = _re_tier.search(r'(\d+)', str(t)); return int(m.group(1)) if m else 9
            _has_intel = bool(str(_pr.get('intel_note','')).strip())
            _has_vac = bool(vacated_roles.get(_pr['clean_name'], {}).get('inherits_targets'))
            _is_elite = (_tnum2(_pr.get('tier','Tier 9')) <= 2) or (_pos_rank <= 4)
            _wr_value = (_pr['position'] == 'WR' and _pos_rank >= 5 and _need_pos
                         and not _is_elite and (_has_intel or _has_vac))
            if _wr_value and not _edge_txt:
                _edge_txt = (" 💎 <b>WR VALUE ZONE:</b> mid-tier WR where tier-jumpers hide (JSN-type). "
                             + ("Live camp buzz — prime breakout target." if _has_intel
                                else f"Inherits vacated targets — breakout upside."))
            # FFA multi-source second opinion (grounded, scoring-agnostic z-score consensus).
            # Additive note only — never changes the price. Surfaces genuine cross-source
            # disagreements ("consensus is higher/lower on him than your board").
            _ffa_txt = ""
            _ffa_f = str(_pr.get('ffa_flag', '')).strip()
            if _ffa_f:
                _ffa_txt = f" {_ffa_f}"
            # HANDCUFF (grounded, live Sleeper depth): for a workhorse RB worth
            # protecting, name his backup. Only fires when we confidently know the
            # RB2 (confidence guard in sleeper_live). Value: late-round insurance.
            _hc_txt = ""
            _hc = str(_pr.get('handcuff', '')).strip()
            if _pr['position'] == 'RB' and _hc and float(_pr.get('live_vorp', _pr.get('vorp', 0))) >= 40:
                _where = "grab him late as insurance" if _pr.get('handcuff_on_board') else "stash off waivers"
                _hc_txt = (f" 🔗 <b>Handcuff:</b> {_hc} — if you win {_pr['player_name']}, "
                           f"{_where} (protects a workhorse pick).")
            if _fair > my_max_bid and _mkt_fair > my_max_bid:
                _verdict, _color, _msg = "CAN'T AFFORD", "#ef4444", f"Market ~${max(_likely,_mkt_fair)} exceeds your max ${my_max_bid}. Would strand your roster."
            elif not _need_pos and not _want:
                _verdict, _color, _msg = "SKIP", "#f59e0b", f"You don't need {_pr['position']} — let a rival spend ~${_likely}. Nominate to bleed them.{_tier_drop_txt}{_ffa_txt}"
            else:
                _verdict, _color = f"BID to ${_bid_ceiling}", "#10b981"
                _msg = (f"League market for {_pr['position']}{_pos_rank if _pos_rank<99 else ''} ~${_likely}. "
                        f"Ceiling ${_bid_ceiling} (real tier price).{_tier_drop_txt}{_edge_txt}{_ffa_txt}{_hc_txt}")
            _star = "⭐ TARGET · " if _want else ""
            st.markdown(
                f'<div style="background:{_color};border-radius:8px;padding:14px 18px;margin:4px 0 8px 0;">'
                f'<span style="font-size:1.5rem;font-weight:800;color:white;">{_star}{_verdict}</span>'
                f'<span style="font-size:0.95rem;color:#f8fafc;margin-left:12px;">{_pr["player_name"]} ({_pr["position"]}) — {_msg}</span>'
                f'</div>', unsafe_allow_html=True)

            # ── FORWARD-LOOKING COMPARATIVE REC: steer to the better bet ──────────
            # If the selected player carries a scheme RISK (or negative intel) AND a
            # similar-value AVAILABLE alternative at the same position has a better
            # outlook (scheme FIT / no risk / positive intel) for close/less money,
            # surface "Consider [alt] instead". This is the real edge — the model
            # recommending who will likely do BETTER this year, not just grading.
            _sel_tag = str(_pr.get('scheme_tag', '')).upper()
            _sel_risk = ('RISK' in _sel_tag) or ('CONCERN' in str(_pr.get('intel_tag', '')).upper())
            if _sel_risk:
                _sel_vorp = float(_pr.get('live_vorp', _pr.get('vorp', 0)))
                _sel_tier = str(_pr.get('tier', 'Tier 9'))
                _alt_pool = _pos_pool_avail.copy()
                _alt_pool = _alt_pool[_alt_pool['clean_name'] != _pr['clean_name']]
                # A genuine sidegrade only: VORP within a TIGHT band around the
                # selected player (0.80x–1.20x — not a much better higher-tier guy,
                # which would be obvious/unavailable) AND same tier or one adjacent.
                _lo, _hi = _sel_vorp * 0.80, _sel_vorp * 1.20
                _alt_pool = _alt_pool[(_alt_pool['live_vorp'] >= _lo) & (_alt_pool['live_vorp'] <= _hi)]
                # keep same-tier or one-tier neighbours only
                def _tier_num(t):
                    m = re.search(r'(\d+)', str(t)); return int(m.group(1)) if m else 9
                _st_n = _tier_num(_sel_tier)
                _alt_pool = _alt_pool[_alt_pool['tier'].apply(lambda t: abs(_tier_num(t) - _st_n) <= 1)]
                def _outlook_score(rr):
                    t = str(rr.get('scheme_tag', '')).upper()
                    s = 0
                    if 'FIT' in t: s += 2
                    if 'RISK' in t: s -= 3
                    if str(rr.get('intel_note', '')).strip(): s += 1
                    return s
                if not _alt_pool.empty:
                    _sel_ol = _outlook_score(_pr)   # selected player's own outlook (negative, has risk)
                    _alt_pool = _alt_pool.assign(_ol=_alt_pool.apply(_outlook_score, axis=1))
                    # only a MEANINGFULLY better outlook qualifies (beat the risky
                    # selected player by >=2), and the alt must be net-positive.
                    _alt_pool = _alt_pool[(_alt_pool['_ol'] >= _sel_ol + 2) & (_alt_pool['_ol'] >= 1)].sort_values(
                        ['_ol', 'live_vorp'], ascending=[False, False])
                    if not _alt_pool.empty:
                        _alt = _alt_pool.iloc[0]
                        _alt_rank = _pos_pool_avail['clean_name'].tolist().index(_alt['clean_name']) + 1
                        _alt_price = league_market_cost(_pr['position'], _alt_rank) or int(_alt['fair_value'])
                        _alt_why = "scheme FIT" if 'FIT' in str(_alt.get('scheme_tag','')).upper() else \
                                   ("live camp buzz" if str(_alt.get('intel_note','')).strip() else "no scheme risk")
                        _risk_note = str(_pr.get('scheme_note','')).replace('🎬 SCHEME RISK','').strip()[:90]
                        st.markdown(
                            f'<div style="background:#1e293b;border-left:4px solid #a78bfa;padding:10px 14px;'
                            f'border-radius:6px;margin-bottom:10px;font-size:0.9rem;">'
                            f'🔮 <b>MODEL EDGE — consider {_alt["player_name"]} instead:</b> '
                            f'{_pr["player_name"]} carries a risk ({_risk_note}). '
                            f'{_alt["player_name"]} is close value (VORP +{round(float(_alt["live_vorp"]),0)} vs '
                            f'+{round(_sel_vorp,0)}) at ~${int(_alt_price)} with a better {_pr["position"]} outlook '
                            f'({_alt_why}) — likely the better bet this year.</div>',
                            unsafe_allow_html=True)

            # ── BUILD PLAN: "if you win at ~$X, here's how you fill the rest" ──────
            _spend = min(my_max_bid, _likely)
            _cap_after = my_cap_left - _spend
            _slots_after = max(0, my_slots_left - 1)
            if _slots_after > 0 and _verdict.startswith("BID"):
                _per_slot = _cap_after / _slots_after
                # need list after this hypothetical win (this player fills one slot)
                _sim_gaps = dict(pos_gaps)
                _bkt = 'IDP' if _pr['position'] in ('LB','DL','DB') else _pr['position']
                if _sim_gaps.get(_bkt, 0) > 0:
                    _sim_gaps[_bkt] -= 1
                # User rules: IDP starters ~2 (not 4) and IDP/DEF are $1 streamers
                # (abundant on waivers — never spend real money). Cap IDP need at 2.
                if _sim_gaps.get('IDP', 0) > 2:
                    _sim_gaps['IDP'] = 2
                _still = [p for p in ['QB','RB','WR','TE','IDP','DEF'] if _sim_gaps.get(p,0) > 0]

                # ── SMART ALLOCATION ──────────────────────────────────────────
                # 1) Reserve ~$5 for the endgame ($1 nominations you control).
                # 2) IDP/DEF are FIXED $1 each (streamers) — they never draw from the
                #    skill-player budget. 3) The REAL money goes to skill positions
                #    (RB/WR primary, QB/TE next), weighted.
                _RESERVE = 5
                _skill = [p for p in _still if p in ('QB', 'RB', 'WR', 'TE')]
                _cheap = [p for p in _still if p in ('IDP', 'DEF')]
                _cheap_cost = sum(_sim_gaps[p] * 1 for p in _cheap)   # $1 per streamer slot
                _skill_budget = max(0, _cap_after - _RESERVE - _cheap_cost)
                _POS_W = {'RB': 3.0, 'WR': 3.0, 'QB': 1.6, 'TE': 1.0}
                _wsum = sum(_POS_W.get(p, 1.0) * _sim_gaps[p] for p in _skill) or 1.0
                _plan_bits = []
                for _p in _still:
                    _is_idp = _p == 'IDP'
                    if _p in ('IDP', 'DEF'):
                        _pos_budget = _sim_gaps[_p] * 1     # $1 streamers, no real spend
                        _per_pos_slot = 1.0
                    else:
                        _pos_budget = _skill_budget * (_POS_W.get(_p, 1.0) * _sim_gaps[_p]) / _wsum
                        _per_pos_slot = max(1.0, _pos_budget / max(1, _sim_gaps[_p]))
                    _ppool_all = df_unpicked[df_unpicked['position'].isin(['LB','DL','DB'])] if _is_idp \
                                 else df_unpicked[df_unpicked['position'] == _p]
                    _ppool_all = _ppool_all[_ppool_all['clean_name'] != _pr['clean_name']].sort_values(
                        'live_vorp', ascending=False)   # BEST players first, not cheapest
                    # DEF: prefer the SOFT-opening-slate streamers (your Wks1-4 work),
                    # not random $1 defenses — order by soft_open then avg opp PPG.
                    if _p == 'DEF' and dst_streamers:
                        _ppool_all = _ppool_all.copy()
                        _ppool_all['_soft'] = _ppool_all['team'].map(
                            lambda t: 0 if dst_streamers.get(t, {}).get('soft_open') else 1)
                        _ppool_all['_oppppg'] = _ppool_all['team'].map(
                            lambda t: dst_streamers.get(t, {}).get('avg_opp_ppg', 99))
                        _ppool_all = _ppool_all.sort_values(['_soft', '_oppppg'])
                    # Suggest the BEST available players at this position, each shown
                    # with its own tier + realistic price + a short reason — so the
                    # list is the top targets (not random cheap scrubs). For IDP/DEF
                    # these are the best $1 streamers.
                    _cands = []
                    for _i2, (_, _rr) in enumerate(_ppool_all.head(30).iterrows(), start=1):
                        _rk_pos = int(_rr.get('pos_rank_avail', _i2))
                        _lp = league_market_cost(_p if not _is_idp else 'LB', _rk_pos) or int(_rr['fair_value'])
                        if _p in ('IDP', 'DEF'):
                            _lp = 1
                        # reason: scheme fit / vacated / workhorse / tier / just value
                        _rsn = str(_rr.get('edge_reasons', '')).split(';')[0].strip()
                        if _p == 'DEF':
                            _dst = dst_streamers.get(_rr['team'], {})
                            _rsn = ("🟢 soft Wk1-4 slate" if _dst.get('soft_open')
                                    else f"opp {int(_dst.get('avg_opp_ppg',0))} PPG" if _dst else "streamer")
                        elif not _rsn:
                            _rsn = str(_rr.get('tier', ''))
                        _cands.append((_rr['player_name'], int(_lp), str(_rr.get('tier','')), _rsn[:40]))
                        # skill: keep to players roughly within this position's budget,
                        # but always show at least the top 3 regardless so you see the
                        # best options even if they cost a bit more.
                        if len(_cands) >= 3:
                            break
                    _pp2 = pos_pressure.get(_p, {})
                    _rivals_need = _pp2.get('rivals_needing', 0)
                    _startable_left = int((_ppool_all['fair_value'] >= 5).sum())
                    _flag = ""
                    # scarcity flag ONLY for skill positions — IDP/DEF are streamer
                    # pools (32 defenses, deep IDP), never a bidding war.
                    if _p in ('QB', 'RB', 'WR', 'TE') and _rivals_need >= 3 and _startable_left <= _rivals_need + 1:
                        _flag = (f' <span style="color:#f59e0b;font-weight:700;">⚠️ {_rivals_need} rivals need '
                                 f'{_p}, only {_startable_left} left — inflating</span>')
                    # TIER-SCARCITY: how many left in the CURRENT tier at this position,
                    # TIER-SCARCITY based on the SUGGESTED players' tier (the ones
                    # actually listed), so the note matches the names shown — not an
                    # abstract pool-top tier that contradicts the list.
                    _tier_note = ""
                    if _p in ('QB', 'RB', 'WR', 'TE') and _cands:
                        _top_sugg_tier = _cands[0][2]   # tier of the best suggested player
                        _tier_left = int((_ppool_all['tier'] == _top_sugg_tier).sum())
                        if _tier_left <= 3:
                            _tier_note = (f' <span style="color:#fca5a5;">⛰️ only {_tier_left} left in '
                                          f'{_top_sugg_tier} — grab before the cliff</span>')
                        else:
                            _tier_note = f' <span style="color:#64748b;">({_tier_left} in {_top_sugg_tier})</span>'
                    # each candidate shown WITH its tier + price + short reason, so the
                    # list is self-explaining ("why is this suggested?").
                    def _fmt_cand(c):
                        _n, _c, _t, _r = c
                        _tshort = _t.replace('Tier ', 'T')
                        _rtxt = f" · {_r}" if _r and _r != _t else ""
                        return f"{_n} <span style='color:#64748b'>({_tshort}, ~${_c}{_rtxt})</span>"
                    _names = ", ".join(_fmt_cand(c) for c in _cands)
                    if _p in ('IDP', 'DEF'):
                        _lbl = "best $1 streamers" if _p == 'DEF' else "best $1 IDP"
                        _plan_bits.append(f"<b>{_p}×{_sim_gaps[_p]} ({_lbl}):</b> {_names}")
                    else:
                        _plan_bits.append(f"<b>{_p}×{_sim_gaps[_p]} (~${int(_pos_budget)}):</b> {_names}{_flag}{_tier_note}")
                _viable = _cap_after >= _slots_after  # at least $1/slot
                _vcolor = "#10b981" if _viable else "#ef4444"
                _plan_html = "<br>".join(_plan_bits) if _plan_bits else "Tight — lean on $1-3 value at your remaining slots."
                st.markdown(
                    f'<div style="background:#131b2e;border-left:4px solid {_vcolor};padding:10px 14px;'
                    f'border-radius:6px;margin-bottom:12px;font-size:0.85rem;">'
                    f'📐 <b>If you win at ~${_spend}:</b> ${_cap_after} left. Plan: '
                    f'<b>${_skill_budget}</b> on skill players, <b>${_cheap_cost}</b> on IDP/DEF ($1 streamers), '
                    f'<b>${_RESERVE}</b> reserved for endgame $1-nominations. '
                    f'{"✅ Viable." if _viable else "⚠️ Thin — only for a true anchor."}<br>'
                    f'<span style="color:#94a3b8;">Spend your real money here:</span><br>{_plan_html}</div>',
                    unsafe_allow_html=True)

    # ── LIVE QoL BANNER: recent picks ticker + roster + guardrails ────────────
    if live_mode:
        _recent = sorted(st.session_state.drafted_picks.items(),
                         key=lambda kv: kv[1].get("pick_no", 0), reverse=True)[:6]
        if _recent:
            _chips = " ".join(
                f'<span style="background:#0b0f19;border:1px solid #334155;border-radius:4px;'
                f'padding:2px 7px;margin-right:4px;font-size:0.78rem;">'
                f'{v["player_name"]} <b style="color:#f59e0b;">${v["price"]}</b> '
                f'<span style="color:#64748b;">→ {st.session_state.custom_manager_names.get(v["team"], "T"+str(v["team"]))}</span></span>'
                for _, v in _recent)
            st.markdown(f'<div style="margin-bottom:8px;">🔴 <b>LIVE</b> · Recent: {_chips}</div>',
                        unsafe_allow_html=True)
        # my roster tracker + guardrail line
        _need_txt = ", ".join(f"{p}×{pos_gaps[p]}" for p in ['QB','RB','WR','TE'] if pos_gaps.get(p,0)>0) or "starters full"
        _reserve = max(0, my_slots_left - 1)  # $1 min for each other open slot
        st.markdown(
            f'<div style="background:#131b2e;border-left:4px solid #10b981;padding:8px 12px;'
            f'border-radius:6px;margin-bottom:10px;font-size:0.9rem;">'
            f'💰 <b>Max bid ${my_max_bid}</b> · ${my_cap_left} left · {my_slots_left} slots open '
            f'(reserve ≥${_reserve}) · <b>Still need:</b> {_need_txt}</div>',
            unsafe_allow_html=True)
        # #4 ENDGAME $1-NOMINATION (user-confirmed): at $1 everyone's tied, so the
        # NOMINATOR gets the player. Holding 2+ slots & $2+ into the endgame lets you
        # control 2 nominations = 2 players you choose, vs being at others' mercy.
        _endgame = (my_slots_left <= 3) or (my_cap_left <= my_slots_left + 2)
        if _endgame and my_slots_left > 0:
            # best $1 survivor to nominate for yourself = highest live_vorp among
            # cheap unpicked players (market_cost <= 2) that will reach the $1 zone
            _dollar_pool = df_unpicked[(df_unpicked['market_cost'] <= 2) &
                                       (~df_unpicked['clean_name'].isin(st.session_state.my_fades))]
            _dollar_pool = _dollar_pool.sort_values('live_vorp', ascending=False)
            _best1 = _dollar_pool.iloc[0] if not _dollar_pool.empty else None
            _best1_txt = (f" Best $1 nomination target: <b>{_best1['player_name']} "
                          f"({_best1['position']}, {round(float(_best1['live_vorp']),1)} VORP)</b> — "
                          f"nominate to claim him yourself." if _best1 is not None else "")
            _ctrl = "✅ You control 2 endgame nominations." if (my_slots_left >= 2 and my_cap_left >= 2) \
                    else "⚠️ Keep 2 slots + $2 so you control 2 nominations (nominator wins $1 ties)."
            st.markdown(
                f'<div style="background:#131b2e;border-left:4px solid #f59e0b;padding:8px 12px;'
                f'border-radius:6px;margin-bottom:10px;font-size:0.85rem;">'
                f'🏁 <b>Endgame:</b> {_ctrl}{_best1_txt}</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("League Capital Remaining", f"${remaining_league_cash}", f"-${total_cash_spent} Spent")
    c2.metric("Room Inflation Index", f"{inflation_index}x", "Deflation (Bargains)" if inflation_index < 1.0 else "Inflation (Overpay)")
    c3.metric("Players Drafted", f"{len(picked_clean_names)} / {league_size * total_roster_slots}", f"{(league_size * total_roster_slots) - len(picked_clean_names)} Left")
    c4.metric("Your Max Single Bid", f"${my_max_bid}", f"${my_cap_left} Budget Left")
else:
    st.markdown(f"### 🐍 SNAKE DRAFT WAR ROOM • `{my_manager_display}` • `{qb_format}`")

    # ══ "SHOULD I DRAFT?" — VONA + Monte-Carlo survival (no dollars) ═══════════
    st.markdown("#### 🐍 SHOULD I DRAFT?")
    _savail = df_unpicked.sort_values('live_vorp', ascending=False)
    # Auto-default to your best available pickup (need-adjusted), so a verdict is
    # always shown without selecting. On snake this is the best-available at your
    # slot; change it only to compare a specific player.
    _srec = _savail[_savail['clean_name'].isin(st.session_state.my_targets)]
    if _srec.empty:
        _srank = 'my_value' if 'my_value' in _savail else 'live_vorp'
        _srec = _savail.sort_values(_srank, ascending=False)
    _sauto = _srec.iloc[0] if not _srec.empty else None
    _sauto_label = (f"⭐ Auto: {_sauto['player_name']} ({_sauto['position']})"
                    if _sauto is not None else "— no players available —")
    _spos_choices = ["ALL", "QB", "RB", "WR", "TE"] + (["IDP", "DEF"] if include_idp else [])
    _draft_pos = st.radio("Filter by position:", _spos_choices, horizontal=True,
                          key="draft_pos_filter", label_visibility="collapsed")
    if _draft_pos == "ALL":
        _spool_df = _savail
    elif _draft_pos == "IDP":
        _spool_df = _savail[_savail['position'].isin(['LB', 'DL', 'DB'])]
    else:
        _spool_df = _savail[_savail['position'] == _draft_pos]
    _sopts = [_sauto_label] + [f"{r['player_name']} ({r['position']})" for _, r in _spool_df.head(300).iterrows()]
    _ssel = st.selectbox("Player you're considering (type to search):", _sopts, index=0, key="draft_verdict_sel",
                         help="⭐ Auto = your best available. Filter by position + type a name to compare a specific player.")
    if _ssel.startswith("⭐ Auto:"):
        _sprow = _srec.head(1) if _sauto is not None else _savail.head(0)
    else:
        _spname = _ssel.rsplit(" (", 1)[0]
        _sprow = _savail[_savail['player_name'] == _spname]
    if not _sprow.empty:
        if not _sprow.empty:
            _sp = _sprow.iloc[0]
            _gap = max(0, next_my_pick_num - curr_overall_pick)
            # survival prob before my next pick
            _pool = [{'clean_name': r['clean_name'], 'market_adp': float(r['market_adp']),
                      'position': r['position']} for _, r in _savail.head(60).iterrows()]
            _surv = ds.mc_snake_survival(_pool, picks_until_next=_gap, n_sims=250, seed=int(_sp['board_rank']))
            _pgone = int(round(_surv.get(_sp['clean_name'], 0.0) * 100))
            _vona = round(float(_sp.get('vona', 0)), 1)
            _need_pos = pos_gaps.get('IDP' if _sp['position'] in ('LB','DL','DB') else _sp['position'], 0) > 0
            _want = _sp['clean_name'] in st.session_state.my_targets
            if _pgone >= 55 and (_need_pos or _want):
                _sv, _sc, _sm = "DRAFT NOW", "#10b981", f"{_pgone}% gone before your next pick (#{next_my_pick_num}) · VONA +{_vona} cliff."
            elif _vona >= 15 and (_need_pos or _want):
                _sv, _sc, _sm = "DRAFT NOW", "#10b981", f"VONA +{_vona} — steep positional cliff, little comparable value returns."
            elif _pgone < 30:
                _sv, _sc, _sm = "CAN WAIT", "#f59e0b", f"Only {_pgone}% gone before your turn — likely still there, take best value now."
            elif not _need_pos and not _want:
                _sv, _sc, _sm = "SKIP", "#ef4444", f"You don't need {_sp['position']}; VONA +{_vona} is low. Address a need."
            else:
                _sv, _sc, _sm = "TOSS-UP", "#64748b", f"{_pgone}% gone · VONA +{_vona}. Fine either way; weigh your other needs."
            _sstar = "⭐ TARGET · " if _want else ""
            st.markdown(
                f'<div style="background:{_sc};border-radius:8px;padding:14px 18px;margin:4px 0 12px 0;">'
                f'<span style="font-size:1.5rem;font-weight:800;color:white;">{_sstar}{_sv}</span>'
                f'<span style="font-size:0.95rem;color:#f8fafc;margin-left:12px;">{_sp["player_name"]} ({_sp["position"]}) — {_sm}</span>'
                f'</div>', unsafe_allow_html=True)

    # ── LIVE QoL BANNER: on-the-clock alert + recent picks ticker ─────────────
    if live_mode:
        if picks_until_my_turn == 0:
            st.markdown('<div style="background:#15803d;border-radius:6px;padding:10px 14px;'
                        'margin-bottom:10px;font-size:1.05rem;font-weight:700;color:white;">'
                        '🟢 YOU ARE ON THE CLOCK — make your pick!</div>', unsafe_allow_html=True)
        elif picks_until_my_turn <= 2:
            st.markdown(f'<div style="background:#b45309;border-radius:6px;padding:8px 14px;'
                        f'margin-bottom:10px;font-weight:700;color:white;">⏰ Get ready — '
                        f'{picks_until_my_turn} pick(s) until your turn (#{next_my_pick_num}).</div>',
                        unsafe_allow_html=True)
        _recent = sorted(st.session_state.drafted_picks.items(),
                         key=lambda kv: kv[1].get("pick_no", 0), reverse=True)[:6]
        if _recent:
            _chips = " ".join(
                f'<span style="background:#0b0f19;border:1px solid #334155;border-radius:4px;'
                f'padding:2px 7px;margin-right:4px;font-size:0.78rem;">#{v.get("pick_no","?")} '
                f'{v["player_name"]} <span style="color:#64748b;">→ '
                f'{st.session_state.custom_manager_names.get(v["team"], "T"+str(v["team"]))}</span></span>'
                for _, v in _recent)
            st.markdown(f'<div style="margin-bottom:8px;">🔴 <b>LIVE</b> · Recent: {_chips}</div>',
                        unsafe_allow_html=True)
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
st.markdown("---")
st.markdown("##### 🚨 Positional tier cliffs")
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
            run_txt = pos_run_flag(pos)
            run_html = f'<div style="font-size:0.72rem; color:#fbbf24; margin-top:3px;">{run_txt}</div>' if run_txt else ''

            card_html = (
                f'<div class="{alert_class}">'
                f'<div style="font-size:0.8rem; color:#94a3b8; display:flex; justify-content:space-between;">'
                f'<b>{pos} {tier_label}</b> <span>{badge}</span>'
                f'</div>'
                f'<div style="font-size:1.4rem; font-weight:700; color:white; margin-top:4px;">'
                f'{t_count} Left {drop_html}'
                f'</div>'
                f'{run_html}'
                f'</div>'
            )
            st.markdown(card_html, unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="cliff-card"><div style="font-size:0.8rem; color:#94a3b8;"><b>{pos} TIERS</b></div><div style="font-size:1.1rem; font-weight:700; color:#64748b; margin-top:6px;">All Tiers Depleted</div></div>', unsafe_allow_html=True)

st.markdown("---")

# 5.5 Dynamic Targeting & Playbook
my_counts = my_wallet['pos_counts']
my_counts = my_wallet['pos_counts']
pos_targets = {'QB': 2 if qb_format == '⚡ Superflex / 2-QB' else 1, 'RB': 4, 'WR': 4, 'TE': 2, 'IDP': 4 if include_idp else 0, 'DEF': 1}
pos_gaps = {pos: max(0, target - my_counts.get(pos, 0)) for pos, target in pos_targets.items()}
# (pos_gaps/targets also computed above for the live banner; recomputed here is harmless)

non_faded_unpicked = df_unpicked[~df_unpicked['clean_name'].isin(st.session_state.my_fades)].copy()
offense_needed = [p for p in ['QB', 'RB', 'WR', 'TE'] if pos_gaps.get(p, 0) > 0]
display_positions = ['QB', 'RB', 'WR', 'TE'] if offense_needed else (['LB', 'DL', 'DB', 'DEF'] if include_idp else ['DEF'])

if draft_mode == "🔨 Auction / Salary Cap":
    st.markdown("---")
    st.markdown("##### 🎯 Targets — best value per position + smart nominations")
    affordable_df = non_faded_unpicked[non_faded_unpicked['fair_value'] <= my_max_bid].copy()
    primary_candidate_pool = affordable_df[affordable_df['position'].isin(display_positions)].copy()

    top_stud_name = ""
    user_priority_pool = primary_candidate_pool[primary_candidate_pool['clean_name'].isin(st.session_state.my_targets)]

    if not user_priority_pool.empty:
        top_stud = user_priority_pool.sort_values(by=('my_value' if 'my_value' in user_priority_pool else 'fair_value'), ascending=False).iloc[0]
        top_stud_name = top_stud['clean_name']
        _pp = player_price(top_stud)  # CANONICAL price (same as verdict + all cards)
        rec_bid = min(my_max_bid, _pp['ceiling'])
        stud_card_html = (
            '<div style="background:#131b2e; border-top:4px solid #10b981; padding:12px; border-radius:6px; height:100%;">'
            '<div style="font-size:0.75rem; color:#10b981; font-weight:700;">⭐ YOUR PRIORITY TARGET</div>'
            f'<div style="font-size:1.15rem; font-weight:700; color:white; margin:4px 0;">{top_stud["player_name"]} <span class="badge-pos pos-{top_stud["position"]}">{top_stud["position"]}</span></div>'
            f'<div style="font-size:0.85rem; color:#94a3b8;">Bid-To: <b style="color:#10b981;">${rec_bid}</b> | Likely: ${_pp["likely"]} | Fair: ${_pp["fair"]}</div>'
            f'<div style="font-size:0.75rem; color:#cbd5e1; margin-top:6px;"><b>Strategy:</b> Starred priority target. Secure before positional runs exhaust budget.</div>'
            '</div>'
        )
    elif not primary_candidate_pool.empty:
        # rank by NEED-ADJUSTED value (my_value), not raw fair_value
        _sort_col = 'my_value' if 'my_value' in primary_candidate_pool else 'fair_value'
        top_stud = primary_candidate_pool.sort_values(by=_sort_col, ascending=False).iloc[0]
        top_stud_name = top_stud['clean_name']
        _pp = player_price(top_stud)  # CANONICAL price (same everywhere)
        rec_bid = min(my_max_bid, _pp['ceiling'])
        _run_flag = pos_run_flag(top_stud['position'])
        _run_line = f'<div style="font-size:0.72rem; color:#fbbf24; margin-top:4px;">{_run_flag}</div>' if _run_flag else ''
        stud_card_html = (
            '<div style="background:#131b2e; border-top:4px solid #10b981; padding:12px; border-radius:6px; height:100%;">'
            '<div style="font-size:0.75rem; color:#10b981; font-weight:700;">👑 RECOMMENDED ANCHOR / STUD</div>'
            f'<div style="font-size:1.15rem; font-weight:700; color:white; margin:4px 0;">{top_stud["player_name"]} <span class="badge-pos pos-{top_stud["position"]}">{top_stud["position"]}</span></div>'
            f'<div style="font-size:0.85rem; color:#94a3b8;">Bid-To: <b style="color:#10b981;">${rec_bid}</b> | Likely sells: <b>${_pp["likely"]}</b> | Fair: <b>${_pp["fair"]}</b></div>'
            f'<div style="font-size:0.75rem; color:#cbd5e1; margin-top:6px;"><b>Strategy:</b> Need-adjusted top value ({round(top_stud.get("my_value", top_stud["live_vorp"]), 1)}) for your open {top_stud["position"]}. Market ${_pp["market"]}.</div>'
            f'{_run_line}'
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
            # need-adjusted tilt: weight by my_value so open-slot positions rank up
            _mv = pos_pool['my_value'] if 'my_value' in pos_pool else pos_pool['fair_value']
            pos_pool['need_w'] = (_mv / _mv.clip(lower=1).max()).clip(lower=0.5)

            pos_surplus = pos_pool[pos_pool['surplus_val'] > 0].copy()
            if not pos_surplus.empty:
                pos_surplus['score'] = pos_surplus['surplus_val'] * pos_surplus['ppd'] * pos_surplus['target_boost'] * pos_surplus['need_w']
                best_p = pos_surplus.sort_values(by=['score', 'my_value' if 'my_value' in pos_surplus else 'live_vorp'], ascending=[False, False]).iloc[0]
                val_text = f"+${int(best_p['surplus_val'])} Surplus"
                val_color = "#10b981"
            else:
                pos_pool['eff_score'] = pos_pool['ppd'] * pos_pool['target_boost'] * pos_pool['need_w']
                best_p = pos_pool.sort_values(by=['eff_score', 'live_vorp'], ascending=[False, False]).iloc[0]
                ppd_val = round(float(best_p['live_vorp']) / max(1, float(best_p['market_cost'])), 1)
                val_text = f"{ppd_val} VORP/$"
                val_color = "#60a5fa"

            is_p_starred = "⭐ " if best_p['clean_name'] in st.session_state.my_targets else ""
            _pp = player_price(best_p)   # CANONICAL price (same as verdict + stud card)
            exec_price = min(my_max_bid, _pp['ceiling'])

            row_html = (
                '<div style="display:flex; justify-content:space-between; align-items:center; background:#0b0f19; padding:5px 8px; margin-bottom:4px; border-radius:4px; border-left:3px solid #3b82f6;">'
                '<div>'
                f'<span class="badge-pos pos-{best_p["position"]}">{best_p["position"]}</span> <b>{is_p_starred}{best_p["player_name"]}</b> <span style="font-size:0.75rem; color:#94a3b8;">({best_p["tier"]})</span><br>'
                f'<span style="font-size:0.72rem; color:#94a3b8;">Fair: <b>${_pp["fair"]}</b> | Likely: <b>${_pp["likely"]}</b> | Bid-To: <b>${exec_price}</b></span>'
                '</div>'
                f'<div style="font-size:0.8rem; font-weight:700; color:{val_color}; text-align:right;">{val_text}</div>'
                '</div>'
            )
            pos_arb_rows.append(row_html)

    rendered_rows = "".join(pos_arb_rows) if pos_arb_rows else '<div style="font-size:0.85rem; color:#94a3b8;">No arbitrage available.</div>'
    bargain_card_html = f'<div style="background:#131b2e; border-top:4px solid #3b82f6; padding:10px 12px; border-radius:6px; height:100%;"><div style="font-size:0.75rem; color:#3b82f6; font-weight:700; margin-bottom:6px;">💎 POSITIONAL ARBITRAGE (BEST PER POSITION)</div>{rendered_rows}</div>'

    # ── SMART NOMINATION (one optimizer-driven default + optional advanced) ────
    # Default: the game-theory optimizer picks the single best player to nominate
    # to bleed rival cap on someone you DON'T want. Advanced users can still pick a
    # manual intent, but they no longer have to.
    _nom_cands_full = [{'clean_name': r['clean_name'], 'player_name': r['player_name'],
                        'position': r['position'], 'fair_value': float(r['fair_value']),
                        'market_cost': float(r['market_cost'])}
                       for _, r in df_unpicked.head(50).iterrows()]
    _gt_rivals = build_rivals_for_sim()
    _pos_depth = auction_fit.get("position_depth", {})
    if _pos_depth:
        _best_bleeds = ds.nomination_by_depth(_nom_cands_full, _gt_rivals, _pos_depth,
                                              my_interest_names=set(st.session_state.my_targets),
                                              n_top=6, protect_top_n=3)
    else:
        _best_bleeds = ds.nomination_scores(_nom_cands_full, _gt_rivals, set(st.session_state.my_targets), n_top=5)

    bleed_rows = []
    for _n in _best_bleeds:
        if _n.get('i_want'):
            continue
        _price = _n.get('expected_price', _n.get('drain', 0))
        _sub = (f"{_n['interested_rivals']} rivals need {_n['position']} · pays ~${_price}"
                + (f" · ${_n['wasted_cap']} wasted" if 'wasted_cap' in _n else ""))
        bleed_rows.append(
            '<div style="display:flex; justify-content:space-between; align-items:center; background:#0b0f19; padding:5px 8px; margin-bottom:4px; border-radius:4px; border-left:3px solid #f59e0b;">'
            '<div>'
            f'<span class="badge-pos pos-{_n["position"]}">{_n["position"]}</span> <b>{_n["player_name"]}</b><br>'
            f'<span style="font-size:0.72rem; color:#94a3b8;">{_sub}</span>'
            '</div>'
            f'<div style="font-size:0.8rem; font-weight:700; color:#f59e0b; text-align:right;">${_price}</div>'
            '</div>'
        )
    rendered_bleeds = "".join(bleed_rows[:4]) if bleed_rows else '<div style="font-size:0.85rem; color:#94a3b8;">No strong bleed targets — nominate a filler.</div>'
    nom_card_html = (
        '<div style="background:#131b2e; border-top:4px solid #f59e0b; padding:10px 12px; border-radius:6px; height:100%;">'
        '<div style="font-size:0.75rem; color:#f59e0b; font-weight:700; margin-bottom:6px;">🎯 SMART NOMINATIONS (BLEED DEEP WR/RB)</div>'
        '<div style="font-size:0.68rem; color:#64748b; margin-bottom:6px;">Mid-tier depth rivals overpay for — protects your studs & scarce TE/QB</div>'
        f'{rendered_bleeds}</div>'
    )

    with st.expander("⚙️ Advanced nomination tactics (optional)"):
        st.caption("The Smart Nominations card above already picks the best cap-bleed target. "
                   "Use these only if you want a specific manual intent.")
        nom_strategy = st.radio(
            "Manual nomination intent:",
            ["🎯 Smart (bleed rival cap — recommended)", "💣 Landmine Trap (overvalued decoy)",
             "🥷 Stealth Sneak ($1-$3 value snipe)", "👑 Set the Market (price your own target)"],
            horizontal=False)
        if st.button("🤖 Generate AI Nomination Suggestion", use_container_width=True):
            with st.spinner("AI analyzing opponent budgets and traps..."):
                unpicked_top = ", ".join([f"{r['player_name']} (${r['market_cost']})" for _, r in df_unpicked.head(8).iterrows()])
                rivals_sum = ", ".join([f"{d['name']} (Cap: ${200-d['spent']})" for s, d in manager_wallets.items() if s != my_slot][:5])
                needs_sum = ", ".join([f"{pos}: {cnt}" for pos, cnt in pos_gaps.items() if cnt > 0])
                drain_str = "; ".join(f"{n['player_name']} ({n['position']}, ~${n.get('expected_price', n.get('drain', 0))} spend, {n['interested_rivals']} bidders)"
                                      for n in _best_bleeds if not n.get('i_want'))
                st.session_state.last_ai_nom = generate_ai_nomination(
                    nom_strategy, unpicked_top, rivals_sum,
                    needs_sum + f"\nTop rival-cap-drain targets (nominate these): {drain_str}")
        if st.session_state.last_ai_nom:
            with st.chat_message("assistant", avatar="🎯"):
                st.markdown(st.session_state.last_ai_nom)

    rec_col1, rec_col2, rec_col3 = st.columns(3)
    with rec_col1: st.markdown(stud_card_html, unsafe_allow_html=True)
    with rec_col2: st.markdown(bargain_card_html, unsafe_allow_html=True)
    with rec_col3: st.markdown(nom_card_html, unsafe_allow_html=True)

else:
    st.markdown("---"); st.markdown(f"##### 🎯 Targets & turn predictor ({qb_format})")
    snake_col1, snake_col2, snake_col3 = st.columns(3)
    
    primary_candidate_pool = non_faded_unpicked[non_faded_unpicked['position'].isin(display_positions)].copy()
    user_targets_pool = primary_candidate_pool[primary_candidate_pool['clean_name'].isin(st.session_state.my_targets)]
    
    # snake: rank by need-adjusted VONA (my_value = vona*need_mult in snake mode),
    # so scarce positions you must act on now outrank deep positions you can wait on.
    _snake_sort = 'my_value' if 'my_value' in primary_candidate_pool else 'live_vorp'
    if not user_targets_pool.empty:
        best_p = user_targets_pool.sort_values(by=[_snake_sort, 'live_vorp'], ascending=False).iloc[0]
        s_title = "⭐ YOUR PRIORITY TARGET"
    elif not primary_candidate_pool.empty:
        best_p = primary_candidate_pool.sort_values(by=[_snake_sort, 'live_vorp'], ascending=False).iloc[0]
        s_title = "👑 BEST AVAILABLE (VONA + VORP)"
    else:
        best_p = None

    with snake_col1:
        if best_p is not None:
            st.markdown(
                '<div style="background:#131b2e; border-top:4px solid #10b981; padding:12px; border-radius:6px; height:100%;">'
                f'<div style="font-size:0.75rem; color:#10b981; font-weight:700;">{s_title}</div>'
                f'<div style="font-size:1.15rem; font-weight:700; color:white; margin:4px 0;">{best_p["player_name"]} <span class="badge-pos pos-{best_p["position"]}">{best_p["position"]}</span></div>'
                f'<div style="font-size:0.85rem; color:#94a3b8;">Consensus ADP: <b>#{int(best_p["market_adp"])}</b> | VORP: <b style="color:#10b981;">+{round(best_p["live_vorp"], 1)}</b> | VONA: <b style="color:#38bdf8;">+{round(best_p.get("vona", 0), 1)}</b> ({best_p["tier"]})</div>'
                f'<div style="font-size:0.75rem; color:#cbd5e1; margin-top:6px;"><b>Recommendation:</b> {"High VONA — a positional cliff, grab now." if best_p.get("vona", 0) >= 15 else "Solid value; depth remains, can wait if needed."} Fills your {best_p["position"]} slot.</div>'
                '</div>', unsafe_allow_html=True
            )

    with snake_col2:
        # "Steals at ADP" — a genuine steal is when a player's VALUE (VORP) outranks
        # where the room drafts him (ADP). Offense-only + real-ADP (IDP/DST have no
        # ADP). Score = VORP-vs-ADP: how far his live_vorp rank beats his ADP slot.
        # Then DIVERSIFY across QB/RB/WR/TE (round-robin) so the card is a real mix,
        # not all-QB (superflex QBs skew a raw board_rank surplus).
        _adp_pool = non_faded_unpicked[
            non_faded_unpicked.get('has_adp', True)
            & non_faded_unpicked['position'].isin(['QB', 'RB', 'WR', 'TE'])
        ].copy()
        _adp_pool['adp_surplus'] = _adp_pool['market_adp'] - _adp_pool['board_rank']
        # value-vs-cost: rank by VORP among the ADP pool, compare to ADP order.
        _adp_pool = _adp_pool.sort_values('live_vorp', ascending=False).reset_index(drop=True)
        _adp_pool['vorp_rank'] = _adp_pool.index + 1
        _adp_pool = _adp_pool.sort_values('market_adp').reset_index(drop=True)
        _adp_pool['adp_order'] = _adp_pool.index + 1
        # steal_score: drafted later (high adp_order) than his value warrants (low vorp_rank)
        _adp_pool['steal_score'] = _adp_pool['adp_order'] - _adp_pool['vorp_rank']
        _cand = _adp_pool[_adp_pool['steal_score'] >= 2].sort_values(
            by=['steal_score', 'live_vorp'], ascending=[False, False])
        # round-robin by position for a balanced mix (max ~2 per position in top 4)
        from collections import defaultdict as _ddf
        _byp = _ddf(list)
        for _, _rw in _cand.iterrows():
            _byp[_rw['position']].append(_rw)
        _porder = sorted(_byp.keys(), key=lambda p: _byp[p][0]['steal_score'], reverse=True) if _byp else []
        _mix, _k = [], 0
        while len(_mix) < 4 and any(_byp.values()) and _porder:
            _pp = _porder[_k % len(_porder)]
            if _byp[_pp]:
                _mix.append(_byp[_pp].pop(0))
            _k += 1
            if _k > 100:
                break
        fallers = pd.DataFrame(_mix) if _mix else _cand.head(4)

        faller_rows = []
        for _, f_row in fallers.iterrows():
            f_starred = "⭐ " if f_row['clean_name'] in st.session_state.my_targets else ""
            val_spots = int(f_row.get('steal_score', f_row.get('adp_surplus', 0)))
            row_html = (
                '<div style="display:flex; justify-content:space-between; align-items:center; background:#0b0f19; padding:5px 8px; margin-bottom:4px; border-radius:4px; border-left:3px solid #3b82f6;">'
                '<div>'
                f'<span class="badge-pos pos-{f_row["position"]}">{f_row["position"]}</span> <b>{f_row["player_name"]}</b> {f_starred}<br>'
                f'<span style="font-size:0.72rem; color:#94a3b8;">ADP #{int(f_row["market_adp"])} · VORP +{round(f_row["live_vorp"],1)} ({f_row["tier"]})</span>'
                '</div>'
                f'<div style="font-size:0.8rem; font-weight:700; color:#38bdf8;">+{val_spots} value slots</div>'
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
        # Monte-Carlo survival: simulate the picks between now and my next selection
        # to estimate P(gone) — far better than a single ADP threshold.
        _picks_gap = max(0, next_my_pick_num - curr_overall_pick)
        _cand_pool = non_faded_unpicked[
            non_faded_unpicked.get('has_adp', True)
            & non_faded_unpicked['position'].isin(['QB', 'RB', 'WR', 'TE'])
        ].head(40)
        _mc_cands = [{'clean_name': r['clean_name'], 'market_adp': float(r['market_adp']),
                      'position': r['position']} for _, r in _cand_pool.iterrows()]
        _surv = ds.mc_snake_survival(_mc_cands, picks_until_next=_picks_gap, n_sims=250, seed=11)
        _cand_pool = _cand_pool.copy()
        _cand_pool['p_gone'] = _cand_pool['clean_name'].map(_surv).fillna(0.0)
        # "at-risk" = players I'd want (high VORP) with meaningful chance of vanishing
        dead_zone_targets = _cand_pool[(_cand_pool['p_gone'] >= 0.5)].sort_values(
            by=['live_vorp'], ascending=False).head(4)

        turn_rows = []
        for _, t_row in dead_zone_targets.iterrows():
            t_starred = "⭐ " if t_row['clean_name'] in st.session_state.my_targets else ""
            _pg = int(round(t_row['p_gone'] * 100))
            row_html = (
                '<div style="display:flex; justify-content:space-between; align-items:center; background:#0b0f19; padding:5px 8px; margin-bottom:4px; border-radius:4px; border-left:3px solid #ef4444;">'
                '<div>'
                f'<span class="badge-pos pos-{t_row["position"]}">{t_row["position"]}</span> <b>{t_row["player_name"]}</b> {t_starred}<br>'
                f'<span style="font-size:0.72rem; color:#94a3b8;">ADP #{int(t_row["market_adp"])} · VORP +{round(t_row["live_vorp"],1)} · won\'t reach pick #{next_my_pick_num}</span>'
                '</div>'
                f'<div style="font-size:0.8rem; font-weight:700; color:#f87171; text-align:right;">{_pg}% GONE</div>'
                '</div>'
            )
            turn_rows.append(row_html)

        rendered_turns = "".join(turn_rows) if turn_rows else '<div style="font-size:0.85rem; color:#94a3b8;">Next pick is close or top targets likely survive.</div>'
        st.markdown(
            f'<div style="background:#131b2e; border-top:4px solid #ef4444; padding:10px 12px; border-radius:6px; height:100%;">'
            f'<div style="font-size:0.75rem; color:#ef4444; font-weight:700; margin-bottom:6px;">🚨 TURN SURVIVAL WATCH (MONTE-CARLO — {_picks_gap} PICKS TO YOUR TURN)</div>'
            f'{rendered_turns}'
            f'</div>', unsafe_allow_html=True
        )

# 6. Draft Console
col_left, col_right = st.columns([1.4, 1])

with col_left:
    st.markdown("##### 🎯 Player console & mark drafted")
    player_options = df_unpicked['player_name'].tolist()
    if player_options:
        selected_player = st.selectbox("Search or Select Player:", player_options)
        p_data = df_unpicked[df_unpicked['player_name'] == selected_player].iloc[0]
        _cpp = player_price(p_data)          # CANONICAL price (same as verdict/cards)
        fair_val = _cpp['fair']
        mkt_val = _cpp['market']
        bid_to = min(my_max_bid, _cpp['ceiling'])
        plan_cap = _cpp['likely']
        delta_vs_mkt = int(bid_to - mkt_val)
        adp_rank = int(p_data['market_adp'])
        my_board_rank = int(p_data['board_rank'])
        
        p_card_col1, p_card_col2, p_card_col3, p_card_col4 = st.columns(4)
        if draft_mode == "🔨 Auction / Salary Cap":
            p_card_col1.metric("Fair Value", f"${fair_val}")
            p_card_col2.metric("Market $", f"${mkt_val}")
            p_card_col3.metric("Likely Sells", f"${plan_cap}")
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
    # Your starred targets still on the board — the one list you glance at to see
    # what YOU still want (replaces the old stale LANDMINE/QUICK-REACH cards, whose
    # nomination role is now covered by the game-theory Smart Nominations).
    st.markdown("#### ⭐ YOUR TARGETS REMAINING")
    _my_left = df_unpicked[df_unpicked['clean_name'].isin(st.session_state.my_targets)]
    if _my_left.empty:
        st.caption("No starred targets on the board. Star players in the sidebar Wishlist, "
                   "or check the 🚀 Edge tab for tier-jumpers.")
    else:
        _my_left = _my_left.sort_values('live_vorp', ascending=False).head(6)
        for _, tr in _my_left.iterrows():
            _tp = player_price(tr)
            if draft_mode == "🔨 Auction / Salary Cap":
                _right = f'<span class="landmine-tag" style="background:#10b98120; color:#34d399; border:1px solid #10b98140;">~${_tp["likely"]}</span>'
                _sub = f'Bid-to ${min(my_max_bid, _tp["ceiling"])} | Fair ${_tp["fair"]}'
            else:
                _right = f'<span class="landmine-tag" style="background:#3b82f620; color:#60a5fa; border:1px solid #3b82f640;">ADP #{int(tr["market_adp"])}</span>'
                _sub = f'VORP +{round(tr["live_vorp"],1)} ({tr["tier"]})'
            st.markdown(
                '<div style="background:#131b2e; border-left:3px solid #10b981; padding:8px 12px; margin-bottom:6px; border-radius:4px; display:flex; justify-content:space-between; align-items:center;">'
                f'<div><b>{tr["player_name"]}</b> <span class="badge-pos pos-{tr["position"]}">{tr["position"]}</span><br>'
                f'<span style="font-size:0.75rem; color:#94a3b8;">{_sub}</span></div>'
                f'{_right}</div>', unsafe_allow_html=True)

# Advisor metric legend — moved to the BOTTOM (reference, out of the draft flow).
with st.expander("ℹ️ How to read the advisor metrics"):
    if draft_mode == "🔨 Auction / Salary Cap":
        st.markdown(
            "- **Fair $** — value at par (VORP share of budget), already adjusted for live **room inflation**. "
            "For superflex QBs, blended toward the real league market to reflect 2-QB scarcity.\n"
            "- **Likely sells / Walk-away** — Monte-Carlo of the winning price from rivals' remaining cap, "
            "positional need, and archetype aggression. *Likely* = median sim; *Walk-away* = 80th-percentile "
            "(don't chase past it).\n"
            "- **Surplus / VORP-$** — arbitrage: fair value above market cost, and points-of-VORP per dollar.\n"
            "- **🏃 RUN / 🎯 rivals need** — a positional run is underway, or N rivals still must fill that slot "
            "(demand holds prices up).\n"
            "- **🔗 Handcuff** — the backup RB behind a workhorse (live Sleeper depth) — late insurance.\n"
            "- **Nomination drain** — Smart Nominations bleeds rivals on **deep** positions (WR/RB mid-tier) "
            "where replacement is cheap, so their spend is wasted. Protects your studs and scarce TE/QB — "
            "fitted from 3 years of your league's real auctions."
        )
    else:
        st.markdown(
            "- **VORP** — value over a realistic replacement starter (Superflex boosts QB scarcity).\n"
            "- **% GONE (Monte-Carlo)** — simulated probability a player is drafted **before your next pick**, "
            "using ADP + draft noise over the exact serpentine gap. ≥50% = grab now or lose him.\n"
            "- **+Spots Value** — falling past consensus ADP (a steal if he lasts to you).\n"
            "- **VONA** — value lost if you wait: high = a real positional cliff (draft now), low = depth remains (wait)."
        )

st.markdown("---")

# 7. Multi-Tab War Rooms
tab_edge, tab_off, tab_def, tab_intel, tab_matrix, tab_log = st.tabs([
    "🚀 EDGE / Tier-Jumpers",
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
            row_dict["Market $"] = f"${int(r['market_cost'])}"
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

with tab_edge:
    st.markdown("#### 🚀 EDGE BOARD — players best-positioned to OUTPERFORM this year")
    st.caption("Forward-looking: fuses value with cited outlook signals — vacated-role tier-jumpers "
               "(Tuten-type: inherits a departed teammate's touches), camp risers, and scheme fits. "
               "Grounded in real news (📰 pull latest for fresh reads) — never a hallucinated breakout.")
    _edge_pool = df_unpicked[df_unpicked['position'].isin(['QB','RB','WR','TE'])].copy()
    # only surface players with a REAL forward reason (cited riser/jumper or scheme fit),
    # so the board is signal, not the whole board re-sorted.
    if 'edge_reasons' not in _edge_pool.columns:
        _edge_pool = _edge_pool.assign(edge_reasons="", edge_score=_edge_pool.get('live_vorp', 0))
    _edge_pool = _edge_pool[_edge_pool['edge_reasons'].astype(str).str.strip() != ""]
    _edge_pool = _edge_pool.sort_values('edge_score', ascending=False).head(25)
    if _edge_pool.empty:
        st.info("No cited tier-jumpers/risers yet. Click **🚀 Pull Latest News** (with a Groq key) to "
                "populate live vacated-role jumpers (Tuten/Burden/Bucky-type) from the beat wires.")
    else:
        _erows = []
        for _, r in _edge_pool.iterrows():
            _mp = get_market_price(r)
            _erows.append({
                "Edge": round(float(r['edge_score']), 0),
                "Player": r['player_name'],
                "Pos": f'<span class="badge-pos pos-{r["position"]}">{r["position"]}</span>',
                "Tier": r['tier'],
                "Why positioned well": r['edge_reasons'],
                "Cited note": (str(r.get('intel_note','')).strip() or str(r.get('scheme_note','')).strip() or "—")[:120],
                "Market $": f"${int(_mp)}" if _mp else "—",
            })
        st.write(pd.DataFrame(_erows).to_html(escape=False, index=False), unsafe_allow_html=True)
        st.caption("Edge = VORP + scheme-fit + cited-riser bonus − risk. Higher = better bet vs price this year.")

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
        # Lead with REAL fitted behavior from 3yr Sleeper data (not the stale
        # hardcoded $ prose). The archetype title stays; the exploit is now data.
        _h = str(def_p.get('handle', '')).lower()
        _fit = auction_fit.get('by_manager', {}).get(_h, {})
        if _fit:
            _lean = " / ".join(_fit.get('top_positions', [])[:2]) or "balanced"
            _aggr = _fit.get('aggression', 1.0)
            _nom = _fit.get('nominates_early', '?')
            _t3 = int((_fit.get('top3_pct') or 0) * 100)
            _mx = _fit.get('max_bid', '?')
            # data-driven counter based on their real tendency
            if _aggr >= 1.25:
                _ctr = f"Aggressive triple-dipper — let him exhaust cap on 3 studs, then feast on his deflation."
            elif _aggr <= 0.85:
                _ctr = f"Disciplined value-spreader — won't chase; don't expect him to bail you out of bidding wars."
            else:
                _ctr = f"Balanced — contest his {_lean} targets at fair value to force full spend."
            # #6 (user-confirmed): cardinalsin is RB-heavy but STREAKY — baitable
            # only a little, not a lock. Flag strong single-position leans as streaky.
            _lean_top = _fit.get('pos_lean', {})
            _top_share = max(_lean_top.values()) if _lean_top else 0
            if _h == 'cardinalsin' or _top_share >= 0.45:
                _ctr += (" ⚠️ Usually RB-heavy but STREAKY — bait into RB wars with caution, "
                         "not a guaranteed tell.")
            # NOMINATE-vs-LEAN DIVERGENCE (user insight): if he nominates a position
            # he does NOT spend on, his early nominations are BAIT / price-setting —
            # read them as him draining others or pricing a position, not his intent.
            _lean_pos = _fit.get('top_positions', [])
            if _nom and _nom not in ('?', '') and _lean_pos and _nom not in _lean_pos:
                _ctr += (f" 🎭 <b>Nomination tell:</b> spends on {_lean} but nominates {_nom} early — "
                         f"his {_nom} noms are BAIT/price-setting, not what he wants. Don't chase his {_nom} "
                         f"nominations; his real targets are {_lean}.")
            hist_exploit = (f"<b>Leans {_lean}</b> · aggression {_aggr:.2f} · {_t3}% top-3 spend · "
                            f"nominates {_nom} early · max bid ${_mx}.<br>"
                            f"<span style='color:#38bdf8;'>{_ctr}</span>")
        else:
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
        if counts['RB'] < 4: needs.append(f"RB ({counts['RB']}/4)")
        if counts['WR'] < 4: needs.append(f"WR ({counts['WR']}/4)")
        if counts['TE'] < 2: needs.append(f"TE ({counts['TE']}/2)")
        if include_idp and counts['IDP'] < 4: needs.append(f"IDP ({counts['IDP']}/4)")
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
    st.markdown("##### 📊 League Exploit Map — Interactive (fitted from 3yr Sleeper auctions)")

    _hmap = {v.get("handle", "").lower(): v.get("name", "") for v in SOULJA_SOULJA_DEFAULTS.values()}
    _bm = auction_fit.get("by_manager", {})

    if HAS_PLOTLY and _bm:
        # ── Chart 1: positional spend HEATMAP (manager x position % of budget) ──
        _pos_order = ["QB", "RB", "WR", "TE"]
        _hm_rows, _hm_names = [], []
        for _hnd, _f in _bm.items():
            _lean = _f.get("pos_lean", {})
            if not _lean:
                continue
            _hm_names.append(_hmap.get(_hnd, _hnd))
            _hm_rows.append([round(100 * float(_lean.get(p, 0.0)), 0) for p in _pos_order])
        if _hm_rows:
            _hmdf = pd.DataFrame(_hm_rows, index=_hm_names, columns=_pos_order)
            _fig1 = px.imshow(_hmdf, text_auto=True, aspect="auto", color_continuous_scale="RdYlGn_r",
                              labels=dict(x="Position", y="Manager", color="% of $"))
            _fig1.update_layout(title="Where each manager pours their money (% of budget by position)",
                                height=380, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(_fig1, use_container_width=True)
            st.caption("🔴 Red = they overspend there → bait them / expect wars. 🟢 Green = they ignore it → your value.")

        _c1, _c2 = st.columns(2)
        # ── Chart 2: aggression vs. discipline SCATTER ──────────────────────────
        with _c1:
            _sc = []
            for _hnd, _f in _bm.items():
                _lean = _f.get("pos_lean", {})
                _spread = 1.0 - (max(_lean.values()) if _lean else 0.25)   # higher = more balanced
                _sc.append({"Manager": _hmap.get(_hnd, _hnd),
                            "Aggression (top-3 spend %)": round(100 * (_f.get("top3_pct") or 0), 0),
                            "Roster balance": round(100 * _spread, 0),
                            "Leans": " / ".join(_f.get("top_positions", [])[:2]),
                            "Nominates": _f.get("nominates_early", "?")})
            if _sc:
                _scdf = pd.DataFrame(_sc)
                _fig2 = px.scatter(_scdf, x="Aggression (top-3 spend %)", y="Roster balance",
                                   text="Manager", color="Aggression (top-3 spend %)",
                                   color_continuous_scale="Reds", size_max=18,
                                   hover_data=["Leans", "Nominates"])
                _fig2.update_traces(textposition="top center", marker=dict(size=14))
                _fig2.update_layout(title="Aggression vs. balance (top-right = blows budget early)",
                                    height=380, margin=dict(l=10, r=10, t=40, b=10), showlegend=False)
                st.plotly_chart(_fig2, use_container_width=True)
                st.caption("Top-right = stud-hungry (let them exhaust cap). Bottom-left = disciplined spreaders.")
        # ── Chart 3: price-vs-rank CURVES by position (cliffs visible) ──────────
        with _c2:
            _rows3 = []
            for _p in ["QB", "RB", "WR", "TE"]:
                for _r in range(1, 13):
                    _pr3 = league_market_cost(_p, _r)
                    if _pr3:
                        _rows3.append({"Positional Rank": _r, "Price ($)": _pr3, "Position": _p})
            if _rows3:
                _cdf = pd.DataFrame(_rows3)
                _fig3 = px.line(_cdf, x="Positional Rank", y="Price ($)", color="Position", markers=True)
                _fig3.update_layout(title="What each position actually sells for (hover $, see the cliffs)",
                                    height=380, margin=dict(l=10, r=10, t=40, b=10))
                st.plotly_chart(_fig3, use_container_width=True)
                st.caption("Steep drops = tier cliffs (grab before them). Flat = depth (wait). TE cliffs hardest.")
    else:
        # fallback: original static bars if plotly unavailable
        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            _hist_rows = [{"Manager": _hmap.get(h, h), "Top-3 Spend ($)": round((f.get("top3_pct") or 0) * 200)}
                          for h, f in _bm.items() if f.get("top3_pct") is not None]
            if _hist_rows:
                st.bar_chart(pd.DataFrame(sorted(_hist_rows, key=lambda r: -r["Top-3 Spend ($)"])).set_index("Manager"))
        with chart_col2:
            live_spend_df = pd.DataFrame([{
                "Manager": data['name'], "Cash Left": 200 - data['spent'],
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
    else:        st.info("No players drafted yet.")
