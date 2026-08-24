import streamlit as st
import pandas as pd
import numpy as np
import requests
import json
import os
import re
import random

# Page Configuration
st.set_page_config(
    page_title="Soulja Soulja Pro Radar",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling & Archetype Badges
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

    .intel-healthy { background-color: #10b98125; color: #34d399; padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 0.75rem; border: 1px solid #10b98160; }
    .intel-beat { background-color: #3b82f625; color: #93c5fd; padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 0.75rem; border: 1px solid #3b82f660; }
    .intel-hist { background-color: #64748b25; color: #cbd5e1; padding: 2px 6px; border-radius: 4px; font-weight: 600; font-size: 0.75rem; border: 1px solid #64748b60; }
    .intel-bust { background-color: #ef444430; color: #f87171; padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 0.75rem; border: 1px solid #ef444460; }
    .intel-injury { background-color: #dc262640; color: #fca5a5; padding: 2px 6px; border-radius: 4px; font-weight: 800; font-size: 0.75rem; border: 1px solid #dc2626; }
    .intel-surge { background-color: #f59e0b30; color: #fbbf24; padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 0.75rem; border: 1px solid #f59e0b60; }
    .source-link { color: #60a5fa; text-decoration: none; font-weight: 700; font-size: 0.72rem; border: 1px solid #3b82f660; padding: 1px 6px; border-radius: 3px; background: #3b82f615; margin-left: 6px; display: inline-block; }
    .source-link:hover { background: #3b82f630; color: #93c5fd; }

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

DST_SCHEDULE_MAP = {
    "HOU": "📅 W1: @ IND (🟢 Easy) | W2: vs TEN (🟢 Easy) | W3: @ MIN (🟡 Neutral) • 🟢 Top 5 Streamer",
    "DAL": "📅 W1: @ NYG (🟢 Easy) | W2: vs WAS (🟢 Easy) | W3: @ ARI (🟢 Easy) • 🟢 Top 3 Smash",
    "BAL": "📅 W1: @ KC (🔴 Tough) | W2: vs LV (🟢 Easy) | W3: @ DAL (🟡 Neutral) • 🟡 Neutral Start",
    "SF":  "📅 W1: vs NYJ (🟡 Neutral) | W2: @ MIN (🟢 Easy) | W3: @ LAR (🟡 Neutral) • 🟢 Favorable",
    "NYJ": "📅 W1: @ SF (🔴 Tough) | W2: @ TEN (🟢 Easy) | W3: vs NE (🟢 Easy) • 🟢 Favorable W2-3",
    "CLE": "📅 W1: vs DAL (🟡 Neutral) | W2: @ JAX (🟡 Neutral) | W3: vs NYG (🟢 Easy) • 🟢 Strong Start",
    "PIT": "📅 W1: @ ATL (🟡 Neutral) | W2: @ DEN (🟢 Easy) | W3: vs LAC (🟡 Neutral) • 🟢 Strong Start",
    "KC":  "📅 W1: vs BAL (🔴 Tough) | W2: vs CIN (🔴 Tough) | W3: @ ATL (🟡 Neutral) • 🔴 Brutal Early",
    "BUF": "📅 W1: vs ARI (🟡 Neutral) | W2: @ MIA (🔴 Tough) | W3: vs JAX (🟡 Neutral) • 🟡 Neutral",
    "PHI": "📅 W1: vs GB (🔴 Tough) | W2: vs ATL (🟡 Neutral) | W3: @ NO (🟢 Easy) • 🟡 Moderate",
    "MIA": "📅 W1: vs JAX (🟡 Neutral) | W2: vs BUF (🔴 Tough) | W3: @ SEA (🟡 Neutral) • 🟡 Neutral",
    "CIN": "📅 W1: vs NE (🟢 Easy) | W2: @ KC (🔴 Tough) | W3: vs WAS (🟢 Easy) • 🟢 W1 & W3 Stream",
    "CHI": "📅 W1: vs TEN (🟢 Easy) | W2: @ HOU (🔴 Tough) | W3: @ IND (🟢 Easy) • 🟢 W1 Streamer",
    "DEN": "📅 W1: @ SEA (🟡 Neutral) | W2: vs PIT (🟡 Neutral) | W3: @ TB (🟡 Neutral) • 🟡 Neutral",
    "LAC": "📅 W1: vs LV (🟢 Easy) | W2: @ CAR (🟢 Easy) | W3: @ PIT (🟡 Neutral) • 🟢 Top 3 Early Stream",
    "LAR": "📅 W1: @ DET (🔴 Tough) | W2: @ ARI (🟡 Neutral) | W3: vs SF (🔴 Tough) • 🔴 Tough Early",
    "DET": "📅 W1: vs LAR (🟡 Neutral) | W2: vs TB (🟡 Neutral) | W3: @ ARI (🟡 Neutral) • 🟡 Neutral",
    "GB":  "📅 W1: @ PHI (🔴 Tough) | W2: vs IND (🟢 Easy) | W3: @ TEN (🟢 Easy) • 🟢 W2-3 Stream",
    "IND": "📅 W1: vs HOU (🔴 Tough) | W2: @ GB (🟡 Neutral) | W3: vs CHI (🟡 Neutral) • 🟡 Neutral",
    "JAX": "📅 W1: @ MIA (🔴 Tough) | W2: vs CLE (🟡 Neutral) | W3: @ BUF (🔴 Tough) • 🔴 Tough Start",
    "LV":  "📅 W1: @ LAC (🟡 Neutral) | W2: @ BAL (🔴 Tough) | W3: vs CAR (🟢 Easy) • 🟡 W3 Target",
    "MIN": "📅 W1: @ NYG (🟢 Easy) | W2: vs SF (🔴 Tough) | W3: vs HOU (🔴 Tough) • 🟡 W1 Only",
    "NE":  "📅 W1: @ CIN (🔴 Tough) | W2: vs SEA (🟡 Neutral) | W3: @ NYJ (🔴 Tough) • 🔴 Tough Start",
    "NO":  "📅 W1: vs CAR (🟢 Easy) | W2: @ DAL (🔴 Tough) | W3: vs PHI (🔴 Tough) • 🟡 W1 Stream",
    "NYG": "📅 W1: vs MIN (🟡 Neutral) | W2: @ WAS (🟢 Easy) | W3: @ CLE (🔴 Tough) • 🟡 Neutral",
    "SEA": "📅 W1: vs DEN (🟢 Easy) | W2: @ NE (🟢 Easy) | W3: vs MIA (🔴 Tough) • 🟢 Top 5 Early Stream",
    "TB":  "📅 W1: vs WAS (🟢 Easy) | W2: @ DET (🔴 Tough) | W3: vs DEN (🟢 Easy) • 🟢 W1 & W3 Stream",
    "TEN": "📅 W1: @ CHI (🟡 Neutral) | W2: vs NYJ (🔴 Tough) | W3: vs GB (🟡 Neutral) • 🔴 Tough Start",
    "WAS": "📅 W1: @ TB (🟡 Neutral) | W2: vs NYG (🟡 Neutral) | W3: @ CIN (🔴 Tough) • 🟡 Neutral",
    "ARI": "📅 W1: @ BUF (🔴 Tough) | W2: vs LAR (🟡 Neutral) | W3: vs DET (🔴 Tough) • 🔴 Avoid Early",
    "ATL": "📅 W1: vs PIT (🟡 Neutral) | W2: @ PHI (🔴 Tough) | W3: vs KC (🔴 Tough) • 🔴 Tough Start",
    "CAR": "📅 W1: @ NO (🟡 Neutral) | W2: vs LAC (🟡 Neutral) | W3: @ LV (🟡 Neutral) • 🟡 Low Floor"
}

# 🌟 VERIFIED SOULJA SOULJA HISTORICAL CREW MAPPING
SOULJA_SOULJA_DEFAULTS = {
    1: {"handle": "addyrao", "name": "Addy Rao", "archetype": "🐢 Patient Hoarder", "class": "arch-hoard", "bias": "Late Room Dominator", "exploit": "Hoards cash early to clean up Tier 2/3 depth. Nominate his starting targets early to force capital spend."},
    2: {"handle": "skongara", "name": "Shantanu", "archetype": "👑 Stars & Scrubs", "class": "arch-stars", "bias": "Aggressive Marquee RB/WR1", "exploit": "Defending champion with 73.2% win rate. Pushes aggressively for top-5 overall assets. Push bids to fair value and let him choke early budget."},
    3: {"handle": "bluewatermelon", "name": "Bluewatermelon", "archetype": "🛡️ IDP & Floor Buyer", "class": "arch-idp", "bias": "Defensive Floor Focus", "exploit": "Conservative early bidder. Exploit his patient early cadence by securing deflated Tier 1/2 studs."},
    4: {"handle": "DjBallz", "name": "Balaji (You)", "archetype": "👑 Disciplined Anchor", "class": "arch-stars", "bias": "Pure VORP & IDP Efficiency", "exploit": "Focuses strictly on positive mathematical surplus; avoids inflated emotional bidding traps."},
    5: {"handle": "vnayini", "name": "Vinay", "archetype": "🐢 Mid-Tier Value Hunter", "class": "arch-hoard", "bias": "$15-$25 Value Sweeper", "exploit": "Consistent playoff contender (#4 finish in 2025). Nominate his secondary positions early to disrupt planned value traps."},
    6: {"handle": "Kopite", "name": "Kopite", "archetype": "⚖️ Balanced Accumulator", "class": "arch-balanced", "bias": "Tier 2/3 Depth", "exploit": "66.1% historical win rate (#2 in 2025). Spreads capital evenly across rounds 3-8. Contest his target depth directly."},
    7: {"handle": "chaituat", "name": "Chaitu", "archetype": "⚖️ Balanced Spender", "class": "arch-balanced", "bias": "Even Positional Allocation", "exploit": "Bait with high-name recognition; draft superior VORP assets in the subsequent tier."},
    8: {"handle": "cardinalsin", "name": "Harsha", "archetype": "🛡️ IDP & Elite TE Spender", "class": "arch-idp", "bias": "Heavy Defensive & TE Allocation", "exploit": "2024 runner-up who consistently spends up for premier LBs and top TEs. Nominate them early to burn his offensive cap."},
    9: {"handle": "rookieqbme", "name": "Siddanth", "archetype": "🥷 Opportunistic Value Sniper", "class": "arch-hoard", "bias": "Positional Run Exploiter", "exploit": "Capitalizes on late draft runs. Trigger tier cliffs at RB/TE to force him into suboptimal reaches."},
    10: {"handle": "siddharthasagar", "name": "Siddu", "archetype": "👑 Superstar Chaser", "class": "arch-stars", "bias": "High-Ceiling Champion (2024)", "exploit": "2024 champion with league-high point totals. Chases elite studs; bait with overvalued landmines and avoid bidding wars on his target anchors."}
}

def clean_name(name):
    if not isinstance(name, str):
        return ""
    name = name.lower().strip()
    name = re.sub(r"[^\w\s]", "", name)
    name = re.sub(r"\b(jr|sr|iii|ii|iv|v)\b", "", name)
    return " ".join(name.split())

# 1. State Initialization
if "drafted_picks" not in st.session_state:
    st.session_state.drafted_picks = {}
if "my_targets" not in st.session_state:
    st.session_state.my_targets = set()
if "my_fades" not in st.session_state:
    st.session_state.my_fades = set()

# 2. Data Loading Engine
@st.cache_data(ttl=30)
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
    
    if 'depth_chart_order' in df.columns:
        df['depth_chart_order'] = pd.to_numeric(df['depth_chart_order'], errors='coerce').fillna(1).astype(int)
    else:
        df['depth_chart_order'] = 1
        
    return df

@st.cache_data(ttl=10)
def load_camp_overrides():
    if os.path.exists("camp_overrides.json"):
        with open("camp_overrides.json", "r") as f:
            raw_data = json.load(f)
            return {clean_name(k): v for k, v in raw_data.items()}
    return {}

@st.cache_data(ttl=60)
def load_historical_standings():
    hist_file = "soulja_3yr_final_standings.csv"
    if os.path.exists(hist_file):
        try:
            hdf = pd.read_csv(hist_file)
            hdf.columns = [c.lower().strip() for c in hdf.columns]
            return hdf
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()

df_board = load_draft_board()
clean_overrides = load_camp_overrides()
df_standings = load_historical_standings()

if "custom_manager_names" not in st.session_state:
    st.session_state.custom_manager_names = {s: p["name"] for s, p in SOULJA_SOULJA_DEFAULTS.items()}

df_board['live_multiplier'] = 1.0
df_board['intel_note'] = ""
df_board['intel_tag'] = ""
df_board['source_url'] = ""

for idx, row in df_board.iterrows():
    c_p = row['clean_name']
    if c_p in clean_overrides:
        data = clean_overrides[c_p]
        df_board.at[idx, 'live_multiplier'] = data.get('multiplier', 1.0)
        df_board.at[idx, 'intel_note'] = data.get('note', '')
        df_board.at[idx, 'intel_tag'] = data.get('type', '')
        df_board.at[idx, 'source_url'] = data.get('source_url', '')

df_board['live_vorp'] = df_board['vorp'] * df_board['live_multiplier']

# 3. Positional Valuation Math
off_mask = df_board['position'].isin(['QB', 'RB', 'WR', 'TE'])
pos_off_vorp = df_board.loc[off_mask, 'live_vorp'].clip(lower=0).sum()
df_board.loc[off_mask, 'fair_value'] = (df_board.loc[off_mask, 'live_vorp'].clip(lower=0) / max(1.0, pos_off_vorp)) * (180 * 10 * 0.75)
df_board.loc[off_mask, 'fair_value'] = df_board.loc[off_mask, 'fair_value'].apply(lambda x: max(1, int(round(float(x)))))
df_board.loc[off_mask, 'market_cost'] = df_board.loc[off_mask, 'custom_rank'].apply(lambda r: max(1, int(round(64 * np.exp(-0.028 * float(r))))))

# IDP Hard Cap ($4-$6 Max)
idp_mask = df_board['position'].isin(['LB', 'DL', 'DB'])
pos_idp_vorp = df_board.loc[idp_mask, 'live_vorp'].clip(lower=0).sum()
df_board.loc[idp_mask, 'fair_value'] = (df_board.loc[idp_mask, 'live_vorp'].clip(lower=0) / max(1.0, pos_idp_vorp)) * (16 * 10 * 0.70)
df_board.loc[idp_mask, 'fair_value'] = df_board.loc[idp_mask, 'fair_value'].apply(lambda x: min(6, max(1, int(round(float(x))))))

idp_ranks = df_board[idp_mask].sort_values(by='live_vorp', ascending=False).reset_index()
idp_cost_map = {}
for i, r in idp_ranks.iterrows():
    cost = 5 if i < 3 else (3 if i < 8 else (2 if i < 16 else 1))
    idp_cost_map[r['clean_name']] = cost
df_board.loc[idp_mask, 'market_cost'] = df_board.loc[idp_mask, 'clean_name'].map(idp_cost_map).fillna(1).astype(int)

# D/ST Cap ($2-$3 Max)
def_mask = df_board['position'] == 'DEF'
pos_def_vorp = df_board.loc[def_mask, 'live_vorp'].clip(lower=0).sum()
df_board.loc[def_mask, 'fair_value'] = (df_board.loc[def_mask, 'live_vorp'].clip(lower=0) / max(1.0, pos_def_vorp)) * (4 * 10 * 0.70)
df_board.loc[def_mask, 'fair_value'] = df_board.loc[def_mask, 'fair_value'].apply(lambda x: min(3, max(1, int(round(float(x))))))

def_ranks = df_board[def_mask].sort_values(by='live_vorp', ascending=False).reset_index()
def_cost_map = {}
for i, r in def_ranks.iterrows():
    cost = 3 if i < 2 else (2 if i < 6 else 1)
    def_cost_map[r['clean_name']] = cost
df_board.loc[def_mask, 'market_cost'] = df_board.loc[def_mask, 'clean_name'].map(def_cost_map).fillna(1).astype(int)

df_board['fair_value'] = df_board['fair_value'].fillna(1).astype(int)
df_board['market_cost'] = df_board['market_cost'].fillna(1).astype(int)
df_board = df_board.sort_values(by=['fair_value', 'live_vorp'], ascending=[False, False]).reset_index(drop=True)
df_board['auction_rank'] = df_board.index + 1

player_pos_map = dict(zip(df_board['clean_name'], df_board['position']))
player_display_map = dict(zip(df_board['clean_name'], df_board['player_name']))

# 4. Sidebar Controls & Real Sleeper Sync
st.sidebar.title("⚡ Soulja Soulja Radar")
draft_mode = st.sidebar.radio("Draft Format:", ["🔨 Auction / Salary Cap", "🐍 Snake Draft"], horizontal=True)

league_size = 10
total_roster_slots = 18

with st.sidebar.expander("👥 Soulja Soulja League Managers", expanded=False):
    for i in range(1, league_size + 1):
        def_name = st.session_state.custom_manager_names.get(i, SOULJA_SOULJA_DEFAULTS.get(i, {}).get("name", f"Team {i}"))
        new_n = st.text_input(f"Slot #{i} Manager:", value=def_name, key=f"mgr_slot_input_{i}")
        st.session_state.custom_manager_names[i] = new_n

my_slot = st.sidebar.number_input(
    "Your Draft Slot / Team #", 
    min_value=1, 
    max_value=league_size, 
    value=4, # Default to Balaji (Slot 4)
    format="%d"
)
my_manager_display = st.session_state.custom_manager_names.get(my_slot, f"Team {my_slot}")
st.sidebar.caption(f"Drafting as: **{my_manager_display}** (Slot {my_slot})")

room_mode = st.sidebar.radio("Connection Mode:", ["🎮 Mock Sim Sandbox", "🌐 Live Sleeper Room Sync"], horizontal=True)

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

curr_overall_pick = len(st.session_state.drafted_picks) + 1
total_league_picks = league_size * total_roster_slots
snake_on_clock_team = get_snake_team_on_clock(curr_overall_pick, league_size)
next_my_pick_num = get_next_my_pick(curr_overall_pick, my_slot, league_size, total_league_picks)
picks_until_my_turn = max(0, next_my_pick_num - curr_overall_pick)

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
        st.rerun()
else:
    draft_id = st.sidebar.text_input("Sleeper Draft / League ID", value="1385816551680143360")
    if st.sidebar.button("🔄 Sync Live Sleeper API", use_container_width=True):
        st.rerun()
    if draft_id and draft_id.strip():
        try:
            # 1. Resolve live manager display names directly from Sleeper League endpoint
            u_res = requests.get(f"https://api.sleeper.app/v1/league/{draft_id.strip()}/users", timeout=4)
            if u_res.status_code == 200:
                for idx, u in enumerate(u_res.json()):
                    slot_idx = idx + 1
                    disp = u.get('display_name') or u.get('metadata', {}).get('team_name')
                    if disp and slot_idx <= league_size:
                        st.session_state.custom_manager_names[slot_idx] = disp
                        
            # 2. Ingest live picks directly from Sleeper Draft endpoint
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
unpicked_fair_sum = df_unpicked['fair_value'].sum()
inflation_index = round(remaining_league_cash / max(1.0, unpicked_fair_sum), 2)
my_wallet = manager_wallets.get(my_slot, {"spent": 0, "picks": 0})
my_cap_left = 200 - my_wallet['spent']
my_slots_left = total_roster_slots - my_wallet['picks']
my_max_bid = max(1, my_cap_left - (my_slots_left - 1))

if draft_mode == "🔨 Auction / Salary Cap":
    st.markdown(f"### 🏈 SOULJA SOULJA SALARY CAP AUCTION RADAR • `{my_manager_display}`")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("League Capital Remaining", f"${remaining_league_cash}", f"-${total_cash_spent} Spent")
    c2.metric("Room Inflation Index", f"{inflation_index}x", "Deflation (Bargains)" if inflation_index < 1.0 else "Inflation (Overpay)")
    c3.metric("Players Drafted", f"{len(picked_clean_names)} / 180", f"{180 - len(picked_clean_names)} Left")
    c4.metric("Your Max Single Bid", f"${my_max_bid}", f"${my_cap_left} Budget Left")
else:
    st.markdown(f"### 🐍 SOULJA SOULJA SNAKE DRAFT WAR ROOM • `{my_manager_display}`")
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
pos_targets = {'QB': 2, 'RB': 4, 'WR': 4, 'TE': 2, 'IDP': 4, 'DEF': 1}
pos_gaps = {pos: max(0, target - my_counts.get(pos, 0)) for pos, target in pos_targets.items()}

non_faded_unpicked = df_unpicked[~df_unpicked['clean_name'].isin(st.session_state.my_fades)].copy()
offense_needed = [p for p in ['QB', 'RB', 'WR', 'TE'] if pos_gaps.get(p, 0) > 0]
display_positions = ['QB', 'RB', 'WR', 'TE'] if offense_needed else ['LB', 'DL', 'DB', 'DEF']

if draft_mode == "🔨 Auction / Salary Cap":
    st.markdown("#### 🧠 REAL-TIME DYNAMIC TARGETING & NOMINATION ADVISOR")
    affordable_df = non_faded_unpicked[non_faded_unpicked['fair_value'] <= my_max_bid].copy()
    primary_candidate_pool = affordable_df[affordable_df['position'].isin(display_positions)].copy()

    top_stud_name = ""
    user_priority_pool = primary_candidate_pool[primary_candidate_pool['clean_name'].isin(st.session_state.my_targets)]

    if not user_priority_pool.empty:
        top_stud = user_priority_pool.sort_values(by='fair_value', ascending=False).iloc[0]
        top_stud_name = top_stud['clean_name']
        rec_bid = min(my_max_bid, int(round(top_stud['fair_value'] * max(0.90, inflation_index))))
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
        rec_bid = min(my_max_bid, int(round(top_stud['fair_value'] * max(0.90, inflation_index))))
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

    nom_strategy = st.radio("Select Your Tactical Nomination Intent:", ["💸 Bleed Rival Wallets (High-Cost Bait)", "💣 Landmine Trap (Overvalued Decoy)", "🥷 Stealth Sneak ($1-$3 Value Snipe)", "👑 Set the Market (Target Price Discovery)"], horizontal=True)
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
    st.markdown("#### 🐍 SNAKE DRAFT TURN PREDICTOR & VALUE ENGINE")
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
                f'<div style="font-size:0.85rem; color:#94a3b8;">Consensus ADP: <b>#{int(best_p["custom_rank"])}</b> | VORP: <b style="color:#10b981;">{round(best_p["live_vorp"], 1)}</b> ({best_p["tier"]})</div>'
                f'<div style="font-size:0.75rem; color:#cbd5e1; margin-top:6px;"><b>Recommendation:</b> Premier VORP target to fill your starting {best_p["position"]} slot.</div>'
                '</div>', unsafe_allow_html=True
            )

    with snake_col2:
        non_faded_unpicked['adp_fall'] = curr_overall_pick - non_faded_unpicked['custom_rank']
        fallers = non_faded_unpicked[non_faded_unpicked['adp_fall'] >= 2].sort_values(by=['adp_fall', 'live_vorp'], ascending=[False, False]).head(4)
        
        faller_rows = []
        for _, f_row in fallers.iterrows():
            f_starred = "⭐ " if f_row['clean_name'] in st.session_state.my_targets else ""
            drop_spots = int(f_row['adp_fall'])
            row_html = (
                '<div style="display:flex; justify-content:space-between; align-items:center; background:#0b0f19; padding:5px 8px; margin-bottom:4px; border-radius:4px; border-left:3px solid #3b82f6;">'
                '<div>'
                f'<span class="badge-pos pos-{f_row["position"]}">{f_row["position"]}</span> <b>{f_row["player_name"]}</b> {f_starred}<br>'
                f'<span style="font-size:0.72rem; color:#94a3b8;">ADP: #{int(f_row["custom_rank"])} | VORP: {round(f_row["live_vorp"], 1)}</span>'
                '</div>'
                f'<div style="font-size:0.8rem; font-weight:700; color:#38bdf8;">+{drop_spots} Spots</div>'
                '</div>'
            )
            faller_rows.append(row_html)
        
        rendered_fallers = "".join(faller_rows) if faller_rows else '<div style="font-size:0.85rem; color:#94a3b8;">Draft proceeding precisely on consensus ADP.</div>'
        st.markdown(
            f'<div style="background:#131b2e; border-top:4px solid #3b82f6; padding:10px 12px; border-radius:6px; height:100%;">'
            f'<div style="font-size:0.75rem; color:#3b82f6; font-weight:700; margin-bottom:6px;">📉 TOP ADP FALLERS (VALUE DROPS)</div>'
            f'{rendered_fallers}'
            f'</div>', unsafe_allow_html=True
        )

    with snake_col3:
        dead_zone_targets = non_faded_unpicked[
            (non_faded_unpicked['custom_rank'] > curr_overall_pick) &
            (non_faded_unpicked['custom_rank'] <= next_my_pick_num)
        ].sort_values(by='live_vorp', ascending=False).head(4)
        
        turn_rows = []
        for _, t_row in dead_zone_targets.iterrows():
            t_starred = "⭐ " if t_row['clean_name'] in st.session_state.my_targets else ""
            row_html = (
                '<div style="display:flex; justify-content:space-between; align-items:center; background:#0b0f19; padding:5px 8px; margin-bottom:4px; border-radius:4px; border-left:3px solid #ef4444;">'
                '<div>'
                f'<span class="badge-pos pos-{t_row["position"]}">{t_row["position"]}</span> <b>{t_row["player_name"]}</b> {t_starred}<br>'
                f'<span style="font-size:0.72rem; color:#94a3b8;">ADP #{int(t_row["custom_rank"])} (Won\'t make pick #{next_my_pick_num})</span>'
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
        selected_player = st.selectbox("Search or Select Player (Offense or IDP):", player_options)
        p_data = df_unpicked[df_unpicked['player_name'] == selected_player].iloc[0]
        fair_val = int(round(float(p_data['fair_value'])))
        mkt_val = int(round(float(p_data['market_cost'])))
        bid_to = int(round(fair_val * max(0.90, inflation_index)))
        plan_cap = int(round(fair_val * 0.95))
        delta_vs_mkt = int(bid_to - mkt_val)
        adp_rank = int(p_data['custom_rank'])
        
        p_card_col1, p_card_col2, p_card_col3, p_card_col4 = st.columns(4)
        if draft_mode == "🔨 Auction / Salary Cap":
            p_card_col1.metric("Fair Value", f"${fair_val}")
            p_card_col2.metric("Market ADP", f"${mkt_val}")
            p_card_col3.metric("Plan Budget", f"${plan_cap}")
            p_card_col4.metric("MAX BID-TO", f"${bid_to}", f"{delta_vs_mkt:+d} vs Mkt")
        else:
            p_card_col1.metric("Consensus ADP", f"#{adp_rank}")
            adp_delta = curr_overall_pick - adp_rank
            p_card_col2.metric("ADP Delta", f"{adp_delta:+d} Spots", "Value Drop" if adp_delta > 0 else "Reach")
            p_card_col3.metric("Tier Rating", f"{p_data['tier']}")
            p_card_col4.metric("VORP Rating", f"{round(p_data['live_vorp'], 1)} pts")
        
        tag_html = ""
        c_name_curr = p_data['clean_name']
        if c_name_curr in st.session_state.my_targets:
            tag_html += '<span class="pref-target">⭐ MY TARGET</span> '
        elif c_name_curr in st.session_state.my_fades:
            tag_html += '<span class="pref-fade">🚫 MY FADE</span> '

        tag = p_data['intel_tag']
        note = p_data['intel_note']
        if tag == 'INJURY' or "INJURY" in note or "IR" in note or "PUP" in note or "OUT" in note:
            tag_html += '<span class="intel-injury">❌ INJURY ALERT</span> '
        elif tag == 'QUESTIONABLE' or "Questionable" in note:
            tag_html += '<span class="intel-bust">🩹 QUESTIONABLE</span> '
        elif tag == 'HEALTHY' or "CLEARED" in note:
            tag_html += '<span class="intel-healthy">✅ CLEARED</span> '
        elif tag == 'BEAT' or "BEAT WIRE" in note or "ROTOBALLER" in note:
            tag_html += '<span class="intel-beat">📰 LIVE BEAT</span> '
        elif tag == 'HISTORICAL' or "LAST UPDATE" in note or "RECENT WIRE" in note:
            tag_html += '<span class="intel-hist">📰 RECENT WIRE</span> '
        elif "SLEEPER SURGE" in note or "WAIVER SPIKE" in note:
            tag_html += '<span class="intel-surge">🔥 WAIVER SPIKE</span> '

        if p_data['position'] == 'DEF':
            fallback_desc = DST_SCHEDULE_MAP.get(p_data['team'], f"Active {p_data['team']} DEF")
        else:
            d_raw = p_data.get('depth_chart_order')
            d_order = int(d_raw) if pd.notna(d_raw) else 1
            fallback_desc = f"Active {p_data['team']} {p_data['position']} • Depth Chart: #{d_order}"
            
        intel_display = note if note else fallback_desc
        
        p_url = str(p_data.get('source_url', '')).strip()
        p_link = f' <a href="{p_url}" target="_blank" class="source-link">🔗 Read Full Beat Wire</a>' if p_url and p_url.startswith("http") else ''
        
        st.markdown(f"**Position:** <span class='badge-pos pos-{p_data['position']}'>{p_data['position']}</span> | **Team:** `{p_data['team']}` | {tag_html} {intel_display}{p_link}", unsafe_allow_html=True)

        bcol1, bcol2, _ = st.columns([1, 1, 2])
        with bcol1:
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
                    index=my_slot - 1, 
                    format_func=lambda x: f"Slot {x}: {st.session_state.custom_manager_names.get(x, f'Team {x}')}"
                )
        else:
            with mcol1: won_price = st.number_input("Overall Pick #", min_value=1, max_value=total_league_picks, value=curr_overall_pick)
            with mcol2:
                mgr_choices = [i for i in range(1, league_size + 1)]
                won_team = st.selectbox(
                    "Drafting Manager:", 
                    mgr_choices, 
                    index=snake_on_clock_team - 1, 
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
                f'<span style="font-size:0.75rem; color:#94a3b8;">ADP: #{int(hr["custom_rank"])} | VORP: <b>{round(hr["live_vorp"], 1)}</b> ({hr["tier"]})</span></div>'
                f'<span class="landmine-tag" style="background:#3b82f620; color:#60a5fa; border:1px solid #3b82f640;">ELITE VORP</span></div>'
            )
            st.markdown(card_html, unsafe_allow_html=True)

st.markdown("---")

# 7. Multi-Tab War Rooms
tab_off, tab_def, tab_intel, tab_matrix, tab_log = st.tabs([
    "⚔️ Offense War Room", 
    "🛡️ IDP & D/ST War Room", 
    "🚀 Live News & Active Intel Board", 
    "🧠 Soulja Soulja Rival Intelligence & Visual Analytics", 
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
        
        pref_badge = ""
        c_n = r['clean_name']
        if c_n in st.session_state.my_targets:
            pref_badge = '<span class="pref-target">⭐ TARGET</span> '
        elif c_n in st.session_state.my_fades:
            pref_badge = '<span class="pref-fade">🚫 FADE</span> '

        tag_badge = ""
        tag = r['intel_tag']
        note = r['intel_note']
        if tag == 'INJURY' or "INJURY" in note or "IR" in note or "PUP" in note or "OUT" in note:
            tag_badge = '<span class="intel-injury">❌ INJURY</span> '
        elif tag == 'QUESTIONABLE' or "Questionable" in note:
            tag_badge = '<span class="intel-bust">🩹 QUESTIONABLE</span> '
        elif tag == 'HEALTHY' or "CLEARED" in note:
            tag_badge = '<span class="intel-healthy">✅ CLEARED</span> '
        elif tag == 'BEAT' or "BEAT WIRE" in note or "ROTOBALLER" in note:
            tag_badge = '<span class="intel-beat">📰 LIVE BEAT</span> '
        elif tag == 'HISTORICAL' or "LAST UPDATE" in note or "RECENT WIRE" in note:
            tag_badge = '<span class="intel-hist">📰 RECENT WIRE</span> '
        elif "SLEEPER SURGE" in note or "WAIVER SPIKE" in note:
            tag_badge = '<span class="intel-surge">🔥 WAIVER</span> '

        if pos_curr == 'DEF':
            fallback_desc = DST_SCHEDULE_MAP.get(r['team'], f"Active {r['team']} DEF")
        else:
            d_raw = r.get('depth_chart_order')
            d_order = int(d_raw) if pd.notna(d_raw) else 1
            fallback_desc = f"Active {r['team']} {r['position']} • Depth Chart: #{d_order}"
            
        url = str(r.get('source_url', '')).strip()
        link_html = f' <a href="{url}" target="_blank" class="source-link">🔗 Source</a>' if url and url.startswith("http") else ''
        
        intel_text = f"{pref_badge}{tag_badge}{note}{link_html}" if note else f"{pref_badge}{fallback_desc}"

        row_dict = {
            "Priority": int(r['auction_rank']),
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
            row_dict["Consensus ADP"] = f"#{int(r['custom_rank'])}"
            adp_diff = curr_overall_pick - int(r['custom_rank'])
            row_dict["ADP Status"] = f'<span style="color:#38bdf8; font-weight:700;">+{adp_diff} (Faller)</span>' if adp_diff > 0 else (f'<span style="color:#f87171;">{adp_diff} (Reach)</span>' if adp_diff < 0 else 'Even')

        row_dict["Intel / Real-Time Wire"] = intel_text
        table_rows.append(row_dict)
        
    st.write(pd.DataFrame(table_rows).to_html(escape=False, index=False), unsafe_allow_html=True)

with tab_off:
    pos_sub = st.radio("Offense Filter:", ["ALL OFFENSE", "RB", "WR", "TE", "QB"], horizontal=True)
    df_o = df_unpicked[df_unpicked['position'].isin(['QB', 'RB', 'WR', 'TE'])]
    if pos_sub != "ALL OFFENSE": df_o = df_o[df_o['position'] == pos_sub]
    render_board_table(df_o)

with tab_def:
    def_sub = st.radio("Defense Filter:", ["ALL DEFENSE & IDP", "LB", "DL", "DB", "DEF"], horizontal=True)
    df_d = df_unpicked[df_unpicked['position'].isin(['LB', 'DL', 'DB', 'DEF'])]
    if def_sub != "ALL DEFENSE & IDP": df_d = df_d[df_d['position'] == def_sub]
    render_board_table(df_d)

with tab_intel:
    df_i = df_unpicked[df_unpicked['intel_note'] != ""]
    st.markdown(f"**Showing {len(df_i)} active players with live news, injury designations, or waiver surges:**")
    render_board_table(df_i)

with tab_matrix:
    st.markdown("#### 🧠 SOULJA SOULJA RIVAL DRAFTER INTELLIGENCE & TACTICAL EXPLOITS")
    
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

        # Live Execution Drift Flags
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
        if counts['QB'] < 2: needs.append(f"QB ({counts['QB']}/2)")
        if counts['RB'] < 3: needs.append(f"RB ({counts['RB']}/3)")
        if counts['WR'] < 3: needs.append(f"WR ({counts['WR']}/3)")
        if counts['TE'] < 1: needs.append(f"TE ({counts['TE']}/1)")
        if counts['IDP'] < 3: needs.append(f"IDP ({counts['IDP']}/3)")
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
    st.markdown("##### 📊 Visual League Analytics: Historical Scoring & Live Purchasing Power")
    
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        st.markdown("**Historical 2-Year Average Fantasy Points (2024–2025):**")
        if not df_standings.empty:
            df_act = df_standings[df_standings['season'].isin([2024, 2025])]
            if not df_act.empty:
                fpts_summary = df_act.groupby('manager')['reg_fpts'].mean().reset_index()
                handle_to_name = {p['handle']: p['name'] for p in SOULJA_SOULJA_DEFAULTS.values()}
                fpts_summary['Manager Name'] = fpts_summary['manager'].map(handle_to_name).fillna(fpts_summary['manager'])
                fpts_summary = fpts_summary.set_index('Manager Name')['reg_fpts'].sort_values(ascending=True)
                st.bar_chart(fpts_summary)
        else:
            st.info("Historical standings CSV not detected.")
            
    with chart_col2:
        st.markdown("**Live Manager Purchasing Power (Remaining Budget vs Max Bid):**")
        live_spend_df = pd.DataFrame([{
            "Manager": data['name'],
            "Cash Left": 200 - data['spent'],
            "Max Single Bid": max(1, (200 - data['spent']) - ((total_roster_slots - data['picks']) - 1))
        } for data in manager_wallets.values()]).set_index("Manager")
        st.bar_chart(live_spend_df)

    # Deep-Dive Rival Inspector
    st.markdown("---")
    st.markdown("##### 🔍 Deep-Dive Soulja Soulja Manager Inspector")
    insp_col1, insp_col2 = st.columns([1.2, 2.5])
    with insp_col1:
        inspect_slot = st.selectbox(
            "Select Manager to Inspect:", 
            [i for i in range(1, league_size + 1) if i != my_slot], 
            format_func=lambda x: f"Slot {x}: {st.session_state.custom_manager_names.get(x, f'Team {x}')}"
        )
    
    insp_data = manager_wallets[inspect_slot]
    insp_spent = insp_data['itemized_spent']
    arch_title, _, exploit_text = classify_manager_archetype(insp_data, inspect_slot)
    
    with insp_col2:
        st.markdown(
            f'<div style="background:#131b2e; border-left:4px solid #3b82f6; padding:12px; border-radius:6px;">'
            f'<div style="font-size:0.85rem; color:#94a3b8;"><b>{insp_data["name"]} (Slot {inspect_slot}) Profile:</b> <span style="color:#60a5fa; font-weight:700;">{arch_title}</span></div>'
            f'<div style="font-size:0.8rem; color:#cbd5e1; margin-top:4px;"><b>Positional Capital Spent:</b> QB: ${insp_spent["QB"]} | RB: ${insp_spent["RB"]} | WR: ${insp_spent["WR"]} | TE: ${insp_spent["TE"]} | IDP: ${insp_spent["IDP"]} | DEF: ${insp_spent["DEF"]}</div>'
            f'<div style="font-size:0.8rem; color:#34d399; margin-top:6px;"><b>Exploit:</b> {exploit_text}</div>'
            f'</div>', unsafe_allow_html=True
        )

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