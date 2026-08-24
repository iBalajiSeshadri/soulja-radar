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

# Custom Slate & Emerald Styling with Universal Tier-Last Badges
st.markdown("""
<style>
    .stApp { background-color: #0b0f19; color: #e2e8f0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    div[data-testid="stMetricValue"] { font-size: 1.6rem; color: #10b981; font-weight: 700; }
    div[data-testid="stMetricLabel"] { color: #94a3b8; font-size: 0.85rem; }
    .cliff-card { background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border-left: 4px solid #10b981; padding: 12px; border-radius: 6px; }
    .cliff-alert { border-left: 4px solid #ef4444 !important; }
    .landmine-tag { background-color: #ef444420; color: #f87171; padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 0.75rem; border: 1px solid #ef444440; }
    
    /* Universal Tier-Last Cliff Badges */
    .t-last { padding: 2px 6px; border-radius: 4px; font-weight: 800; font-size: 0.72rem; letter-spacing: 0.5px; }
    .t-last-t1 { background-color: #dc2626; color: white; border: 1px solid #f87171; box-shadow: 0 0 8px #dc262660; }
    .t-last-t2 { background-color: #ea580c; color: white; border: 1px solid #fb923c; }
    .t-last-t3 { background-color: #d97706; color: white; border: 1px solid #fcd34d; }
    .t-last-t4 { background-color: #475569; color: #f1f5f9; border: 1px solid #94a3b8; }
    .t-last-t5 { background-color: #334155; color: #cbd5e1; border: 1px solid #64748b; }
    
    /* User Preference Badges */
    .pref-target { background-color: #10b98130; color: #34d399; padding: 2px 6px; border-radius: 4px; font-weight: 800; font-size: 0.75rem; border: 1px solid #10b981; margin-right: 4px; }
    .pref-fade { background-color: #64748b30; color: #94a3b8; padding: 2px 6px; border-radius: 4px; font-weight: 800; font-size: 0.75rem; border: 1px solid #64748b; margin-right: 4px; }

    /* Intel Status Badges */
    .intel-healthy { background-color: #10b98125; color: #34d399; padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 0.75rem; border: 1px solid #10b98160; }
    .intel-beat { background-color: #3b82f625; color: #93c5fd; padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 0.75rem; border: 1px solid #3b82f660; }
    .intel-hist { background-color: #64748b25; color: #cbd5e1; padding: 2px 6px; border-radius: 4px; font-weight: 600; font-size: 0.75rem; border: 1px solid #64748b60; }
    .intel-bust { background-color: #ef444430; color: #f87171; padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 0.75rem; border: 1px solid #ef444460; }
    .intel-injury { background-color: #dc262640; color: #fca5a5; padding: 2px 6px; border-radius: 4px; font-weight: 800; font-size: 0.75rem; border: 1px solid #dc2626; }
    .intel-surge { background-color: #f59e0b30; color: #fbbf24; padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 0.75rem; border: 1px solid #f59e0b60; }
    .source-link { color: #60a5fa; text-decoration: none; font-weight: 700; font-size: 0.72rem; border: 1px solid #3b82f660; padding: 1px 6px; border-radius: 3px; background: #3b82f615; margin-left: 6px; display: inline-block; }
    .source-link:hover { background: #3b82f630; color: #93c5fd; }

    /* Positional Badges */
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

df_board = load_draft_board()
clean_overrides = load_camp_overrides()

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

# 3. Positional Valuation Math ($2,000 Total League Pool)
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

# 4. Sidebar Controls & Live Sync
st.sidebar.title("⚙️ Draft Room Link")
room_mode = st.sidebar.radio("Connection Mode:", ["🎮 Mock Sim Sandbox", "🌐 Live Sleeper Room Sync"], horizontal=True)

league_size = 10
total_roster_slots = 18
my_slot = st.sidebar.number_input("Your Slot / Team #", min_value=1, max_value=league_size, value=1)

manager_wallets = {}
for i in range(1, league_size + 1):
    manager_wallets[i] = {
        "spent": 0, "picks": 0, "name": f"Team {i}",
        "roster": [], "pos_counts": {'QB': 0, 'RB': 0, 'WR': 0, 'TE': 0, 'IDP': 0, 'DEF': 0}
    }

if room_mode == "🎮 Mock Sim Sandbox":
    st.sidebar.markdown("---")
    st.sidebar.markdown("#### 🎲 Sim Controls")
    col_s1, col_s2 = st.sidebar.columns(2)
    with col_s1:
        if st.button("⚡ Sim 1 Pick", use_container_width=True):
            unpicked_now = df_board[~df_board['clean_name'].isin(st.session_state.drafted_picks.keys())]
            if len(unpicked_now) > 0:
                target_p = unpicked_now.iloc[0]
                rand_team = random.choice([t for t in range(1, league_size + 1) if t != my_slot])
                var_price = max(1, int(round(target_p['market_cost'] * random.uniform(0.92, 1.08))))
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
                rand_team = random.choice([t for t in range(1, league_size + 1) if t != my_slot])
                var_price = max(1, int(round(target_p['market_cost'] * random.uniform(0.90, 1.10))))
                st.session_state.drafted_picks[target_p['clean_name']] = {
                    "price": var_price, "team": rand_team,
                    "player_name": target_p['player_name'], "position": target_p['position']
                }
            st.rerun()
    if st.sidebar.button("🗑️ Reset Draft Board", use_container_width=True):
        st.session_state.drafted_picks = {}
        st.rerun()
else:
    draft_id = st.sidebar.text_input("Sleeper Draft ID", value="")
    if st.sidebar.button("🔄 Sync Live Sleeper API", use_container_width=True):
        st.rerun()
    if draft_id and draft_id.strip():
        try:
            p_res = requests.get(f"https://api.sleeper.app/v1/draft/{draft_id.strip()}/picks", timeout=4)
            if p_res.status_code == 200:
                for p in p_res.json():
                    meta = p.get('metadata', {})
                    c_name = clean_name(f"{meta.get('first_name', '')} {meta.get('last_name', '')}")
                    amt = int(meta.get('amount') or p.get('amount') or 1)
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
    "⭐ My Targets (Never Bait / Prioritize Buying)",
    options=all_player_names,
    default=[p for p in all_player_names if clean_name(p) in st.session_state.my_targets]
)
st.session_state.my_targets = {clean_name(p) for p in selected_targets}

selected_fades = st.sidebar.multiselect(
    "🚫 My Fades (Do Not Buy / Prime Bait)",
    options=all_player_names,
    default=[p for p in all_player_names if clean_name(p) in st.session_state.my_fades]
)
st.session_state.my_fades = {clean_name(p) for p in selected_fades}

# Process Roster Breakdown and Wallet Accounting
for c_p, pdata in st.session_state.drafted_picks.items():
    s = pdata["team"]
    pos = pdata.get("position", player_pos_map.get(c_p, "FLEX"))
    if s in manager_wallets:
        manager_wallets[s]["spent"] += pdata["price"]
        manager_wallets[s]["picks"] += 1
        manager_wallets[s]["roster"].append(f"{pdata['player_name']} (${pdata['price']})")
        if pos in ['LB', 'DL', 'DB']:
            manager_wallets[s]["pos_counts"]['IDP'] += 1
        elif pos in manager_wallets[s]["pos_counts"]:
            manager_wallets[s]["pos_counts"][pos] += 1

total_cash_spent = sum(v["price"] for v in st.session_state.drafted_picks.values())
picked_clean_names = set(st.session_state.drafted_picks.keys())
df_unpicked = df_board[~df_board['clean_name'].isin(picked_clean_names)].copy()

# Macro Metrics Bar
remaining_league_cash = (league_size * 200) - total_cash_spent
unpicked_fair_sum = df_unpicked['fair_value'].sum()
inflation_index = round(remaining_league_cash / max(1.0, unpicked_fair_sum), 2)

st.markdown("### 🏈 SOULJA SOULJA QUANTITATIVE RADAR (OFFENSE + IDP)")

c1, c2, c3, c4 = st.columns(4)
c1.metric("League Capital Remaining", f"${remaining_league_cash}", f"-${total_cash_spent} Spent")
c2.metric("Room Inflation Index", f"{inflation_index}x", "Deflation (Bargains)" if inflation_index < 1.0 else "Inflation (Overpay)")
c3.metric("Players Drafted", f"{len(picked_clean_names)} / 180", f"{180 - len(picked_clean_names)} Left")
my_wallet = manager_wallets.get(my_slot, {"spent": 0, "picks": 0})
my_cap_left = 200 - my_wallet['spent']
my_slots_left = total_roster_slots - my_wallet['picks']
my_max_bid = max(1, my_cap_left - (my_slots_left - 1))
c4.metric("Your Max Single Bid", f"${my_max_bid}", f"${my_cap_left} Budget Left")

st.markdown("---")

# 5. POSITIONAL ACTIVE TIER CLIFF TRACKER
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
            if t_idx + 1 < len(tier_order):
                next_tier = tier_order[t_idx + 1]
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
            card_html = (
                '<div class="cliff-card">'
                f'<div style="font-size:0.8rem; color:#94a3b8;"><b>{pos} TIERS</b></div>'
                '<div style="font-size:1.1rem; font-weight:700; color:#64748b; margin-top:6px;">All Tiers Depleted</div>'
                '</div>'
            )
            st.markdown(card_html, unsafe_allow_html=True)

st.markdown("---")

# ==============================================================================
# 5.5 DYNAMIC REAL-TIME TARGETING & STRATEGIC NOMINATION PLAYBOOK
# ==============================================================================
st.markdown("#### 🧠 REAL-TIME DYNAMIC TARGETING & NOMINATION ADVISOR")

my_counts = my_wallet['pos_counts']
pos_targets = {'QB': 2, 'RB': 4, 'WR': 4, 'TE': 2, 'IDP': 4, 'DEF': 1}
pos_gaps = {pos: max(0, target - my_counts.get(pos, 0)) for pos, target in pos_targets.items()}

non_faded_unpicked = df_unpicked[~df_unpicked['clean_name'].isin(st.session_state.my_fades)].copy()
affordable_df = non_faded_unpicked[non_faded_unpicked['fair_value'] <= my_max_bid].copy()

# STRICT ISOLATION: Are starting offensive positions still open?
offense_needed = [p for p in ['QB', 'RB', 'WR', 'TE'] if pos_gaps.get(p, 0) > 0]

if offense_needed:
    primary_candidate_pool = affordable_df[affordable_df['position'].isin(offense_needed)].copy()
else:
    idp_needed = [p for p in ['LB', 'DL', 'DB', 'DEF'] if pos_gaps.get('IDP', 0) > 0 or pos_gaps.get('DEF', 0) > 0]
    primary_candidate_pool = affordable_df[affordable_df['position'].isin(idp_needed)].copy()

# 1. Top Recommended Target (Anchor)
top_stud_name = ""
user_priority_pool = primary_candidate_pool[primary_candidate_pool['clean_name'].isin(st.session_state.my_targets)]

if not user_priority_pool.empty:
    top_stud = user_priority_pool.sort_values(by='fair_value', ascending=False).iloc[0]
    top_stud_name = top_stud['clean_name']
    rec_bid = min(my_max_bid, int(round(top_stud['fair_value'] * max(0.90, inflation_index))))
    stud_badge_text = "⭐ YOUR PRIORITY TARGET"
    stud_card_html = (
        '<div style="background:#131b2e; border-top:4px solid #10b981; padding:12px; border-radius:6px; height:100%;">'
        f'<div style="font-size:0.75rem; color:#10b981; font-weight:700;">{stud_badge_text}</div>'
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
    stud_card_html = (
        '<div style="background:#131b2e; border-top:4px solid #10b981; padding:12px; border-radius:6px;">'
        '<div style="font-size:0.75rem; color:#10b981; font-weight:700;">👑 RECOMMENDED ANCHOR / STUD</div>'
        '<div style="font-size:0.9rem; color:#94a3b8; margin-top:8px;">All primary starting slots filled or budget constrained. Focus on value snipes.</div>'
        '</div>'
    )

# 2. MULTI-POSITIONAL ARBITRAGE & EFFICIENCY BREAKDOWN (QB / RB / WR / TE)
display_positions = ['QB', 'RB', 'WR', 'TE'] if offense_needed else ['LB', 'DL', 'DB', 'DEF']
pos_arb_rows = []

for target_pos in display_positions:
    pos_pool = primary_candidate_pool[
        (primary_candidate_pool['position'] == target_pos) &
        (primary_candidate_pool['clean_name'] != top_stud_name)
    ].copy()
    
    if not pos_pool.empty:
        pos_pool['surplus_val'] = pos_pool['fair_value'] - pos_pool['market_cost']
        pos_pool['ppd'] = pos_pool['live_vorp'] / pos_pool['market_cost'].clip(lower=1)
        pos_pool['target_boost'] = pos_pool['clean_name'].apply(lambda x: 1.6 if x in st.session_state.my_targets else 1.0)
        
        # Priority A: Genuine Positive Surplus
        pos_surplus = pos_pool[pos_pool['surplus_val'] > 0].copy()
        if not pos_surplus.empty:
            pos_surplus['score'] = pos_surplus['surplus_val'] * pos_surplus['ppd'] * pos_surplus['target_boost']
            best_p = pos_surplus.sort_values(by=['score', 'live_vorp'], ascending=[False, False]).iloc[0]
            val_text = f"+${int(best_p['surplus_val'])} Surplus"
            val_color = "#10b981"
        else:
            # Priority B: Points-Per-Dollar (PPD) Intra-Tier Efficiency
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

if pos_arb_rows:
    rendered_rows = "".join(pos_arb_rows)
    bargain_card_html = (
        '<div style="background:#131b2e; border-top:4px solid #3b82f6; padding:10px 12px; border-radius:6px; height:100%;">'
        '<div style="font-size:0.75rem; color:#3b82f6; font-weight:700; margin-bottom:6px;">💎 POSITIONAL ARBITRAGE (BEST PER POSITION)</div>'
        f'{rendered_rows}'
        '</div>'
    )
else:
    bargain_card_html = (
        '<div style="background:#131b2e; border-top:4px solid #3b82f6; padding:12px; border-radius:6px;">'
        '<div style="font-size:0.75rem; color:#3b82f6; font-weight:700;">💎 POSITIONAL ARBITRAGE</div>'
        '<div style="font-size:0.9rem; color:#94a3b8; margin-top:8px;">All starting positions filled or budget constrained.</div>'
        '</div>'
    )

# 3. MULTI-POSITIONAL STRATEGIC NOMINATION PLAYBOOK (QB / RB / WR / TE)
nom_strategy = st.radio(
    "Select Your Tactical Nomination Intent:",
    ["💸 Bleed Rival Wallets (High-Cost Bait)", "💣 Landmine Trap (Overvalued Decoy)", "🥷 Stealth Sneak ($1-$3 Value Snipe)", "👑 Set the Market (Target Price Discovery)"],
    horizontal=True
)

pos_nom_rows = []

for target_pos in display_positions:
    pos_pool = df_unpicked[df_unpicked['position'] == target_pos].copy()
    if pos_pool.empty:
        continue
        
    if nom_strategy == "💸 Bleed Rival Wallets (High-Cost Bait)":
        safe_pool = pos_pool[~pos_pool['clean_name'].isin(st.session_state.my_targets)].copy()
        fade_pool = safe_pool[safe_pool['clean_name'].isin(st.session_state.my_fades)].sort_values(by='market_cost', ascending=False)
        
        if not fade_pool.empty:
            nom_p = fade_pool.iloc[0]
            val_text = f"${int(nom_p['market_cost'])} Fade"
            val_color = "#ef4444"
        else:
            gen_pool = safe_pool[safe_pool['clean_name'] != top_stud_name].sort_values(by='market_cost', ascending=False)
            nom_p = gen_pool.iloc[0] if not gen_pool.empty else pos_pool.iloc[0]
            val_text = f"${int(nom_p['market_cost'])} Drain"
            val_color = "#f59e0b"
            
        is_p_starred = "🚫 " if nom_p['clean_name'] in st.session_state.my_fades else ""
        sub_desc = f"Fair: ${int(nom_p['fair_value'])} | Drain rival cap on non-target"

    elif nom_strategy == "💣 Landmine Trap (Overvalued Decoy)":
        safe_pool = pos_pool[~pos_pool['clean_name'].isin(st.session_state.my_targets)].copy()
        safe_pool['landmine_gap'] = safe_pool['market_cost'] - safe_pool['fair_value']
        nom_p = safe_pool.sort_values(by='landmine_gap', ascending=False).iloc[0] if not safe_pool.empty else pos_pool.iloc[0]
        
        gap = int(nom_p['market_cost'] - nom_p['fair_value'])
        val_text = f"+${gap} Trap" if gap > 0 else f"${gap} Fair"
        val_color = "#ef4444" if gap > 0 else "#94a3b8"
        is_p_starred = "🚫 " if nom_p['clean_name'] in st.session_state.my_fades else ""
        sub_desc = f"Bait: ${int(nom_p['market_cost'])} vs True Value ${int(nom_p['fair_value'])}"

    elif nom_strategy == "🥷 Stealth Sneak ($1-$3 Value Snipe)":
        cheap_pool = pos_pool[
            (pos_pool['market_cost'] <= 3) & 
            (~pos_pool['clean_name'].isin(st.session_state.my_fades))
        ].sort_values(by='live_vorp', ascending=False)
        
        nom_p = cheap_pool.iloc[0] if not cheap_pool.empty else pos_pool.sort_values(by='market_cost', ascending=True).iloc[0]
        val_text = f"${int(nom_p['market_cost'])} Snipe"
        val_color = "#10b981"
        is_p_starred = "⭐ " if nom_p['clean_name'] in st.session_state.my_targets else ""
        sub_desc = f"Sneak {round(nom_p['live_vorp'], 1)} VORP while room is distracted"

    else: # Set the Market
        user_targets = pos_pool[pos_pool['clean_name'].isin(st.session_state.my_targets)].sort_values(by='fair_value', ascending=False)
        if not user_targets.empty:
            nom_p = user_targets.iloc[0]
            val_text = f"${int(nom_p['fair_value'])} Target"
            val_color = "#10b981"
            is_p_starred = "⭐ "
            sub_desc = f"Establish floor price on your wishlist target"
        else:
            nom_p = pos_pool.sort_values(by='fair_value', ascending=False).iloc[0]
            val_text = f"${int(nom_p['fair_value'])} Floor"
            val_color = "#60a5fa"
            is_p_starred = ""
            sub_desc = f"Set baseline price before late inflation"

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

if pos_nom_rows:
    rendered_nom_rows = "".join(pos_nom_rows)
    nom_card_html = (
        '<div style="background:#131b2e; border-top:4px solid #f59e0b; padding:10px 12px; border-radius:6px; height:100%;">'
        '<div style="font-size:0.75rem; color:#f59e0b; font-weight:700; margin-bottom:6px;">🎯 POSITIONAL NOMINATIONS (BEST BAIT / SNIPES)</div>'
        f'{rendered_nom_rows}'
        '</div>'
    )
else:
    nom_card_html = (
        '<div style="background:#131b2e; border-top:4px solid #f59e0b; padding:12px; border-radius:6px;">'
        '<div style="font-size:0.75rem; color:#f59e0b; font-weight:700;">🎯 POSITIONAL NOMINATIONS</div>'
        '<div style="font-size:0.9rem; color:#94a3b8; margin-top:8px;">All available positions exhausted.</div>'
        '</div>'
    )

rec_col1, rec_col2, rec_col3 = st.columns(3)
with rec_col1:
    st.markdown(stud_card_html, unsafe_allow_html=True)
with rec_col2:
    st.markdown(bargain_card_html, unsafe_allow_html=True)
with rec_col3:
    st.markdown(nom_card_html, unsafe_allow_html=True)

st.markdown("---")

# 6. On-The-Block Valuation & Decoys
col_left, col_right = st.columns([1.2, 1])

with col_left:
    st.markdown("#### 🎯 ON-THE-BLOCK 4-PRICE VALUATION")
    player_options = df_unpicked['player_name'].tolist()
    if player_options:
        selected_player = st.selectbox("Search or Select Nominated Player (Offense or IDP):", player_options)
        p_data = df_unpicked[df_unpicked['player_name'] == selected_player].iloc[0]
        fair_val = int(round(float(p_data['fair_value'])))
        mkt_val = int(round(float(p_data['market_cost'])))
        bid_to = int(round(fair_val * max(0.90, inflation_index)))
        plan_cap = int(round(fair_val * 0.95))
        delta_vs_mkt = int(bid_to - mkt_val)
        
        p_card_col1, p_card_col2, p_card_col3, p_card_col4 = st.columns(4)
        p_card_col1.metric("Fair Value", f"${fair_val}")
        p_card_col2.metric("Market ADP", f"${mkt_val}")
        p_card_col3.metric("Plan Budget", f"${plan_cap}")
        p_card_col4.metric("MAX BID-TO", f"${bid_to}", f"{delta_vs_mkt:+d} vs Mkt")
        
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

        st.markdown("##### 🔨 Win or Record Nominated Bid")
        mcol1, mcol2, mcol3 = st.columns([1, 1, 1.2])
        with mcol1:
            won_price = st.number_input("Winning Bid ($)", min_value=1, max_value=200, value=mkt_val)
        with mcol2:
            won_team = st.number_input("Winning Team #", min_value=1, max_value=league_size, value=my_slot)
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

st.markdown("---")

# 7. Multi-Tab War Rooms & Rival Intelligence Matrix
tab_off, tab_def, tab_intel, tab_matrix, tab_log = st.tabs([
    "⚔️ Offense War Room", 
    "🛡️ IDP & D/ST War Room", 
    "🚀 Live News & Active Intel Board", 
    "👥 Rival Needs & Purchasing Power Matrix", 
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

        d_raw = r.get('depth_chart_order')
        d_order = int(d_raw) if pd.notna(d_raw) else 1
        
        url = str(r.get('source_url', '')).strip()
        link_html = f' <a href="{url}" target="_blank" class="source-link">🔗 Source</a>' if url and url.startswith("http") else ''
        
        fallback_desc = f"Active {r['team']} {r['position']} • Depth Chart: #{d_order}"
        intel_text = f"{pref_badge}{tag_badge}{note}{link_html}" if note else f"{pref_badge}{fallback_desc}"

        table_rows.append({
            "Priority": int(r['auction_rank']),
            "Player": r['player_name'],
            "Pos": f'<span class="badge-pos pos-{r["position"]}">{r["position"]}</span>',
            "Team": r['team'],
            "Tier": tier_badge,
            "VORP": round(float(r['live_vorp']), 1),
            "Fair Value": f"${int(r['fair_value'])}",
            "Market ADP": f"${int(r['market_cost'])}",
            "Intel / Real-Time Wire": intel_text
        })
    st.write(pd.DataFrame(table_rows).to_html(escape=False, index=False), unsafe_allow_html=True)

with tab_off:
    pos_sub = st.radio("Offense Filter:", ["ALL OFFENSE", "RB", "WR", "TE", "QB"], horizontal=True)
    df_o = df_unpicked[df_unpicked['position'].isin(['QB', 'RB', 'WR', 'TE'])]
    if pos_sub != "ALL OFFENSE":
        df_o = df_o[df_o['position'] == pos_sub]
    render_board_table(df_o)

with tab_def:
    def_sub = st.radio("Defense Filter:", ["ALL DEFENSE & IDP", "LB", "DL", "DB", "DEF"], horizontal=True)
    df_d = df_unpicked[df_unpicked['position'].isin(['LB', 'DL', 'DB', 'DEF'])]
    if def_sub != "ALL DEFENSE & IDP":
        df_d = df_d[df_d['position'] == def_sub]
    render_board_table(df_d)

with tab_intel:
    df_i = df_unpicked[df_unpicked['intel_note'] != ""]
    st.markdown(f"**Showing {len(df_i)} active players with live news, injury designations, historical blurbs, or waiver surges:**")
    render_board_table(df_i)

with tab_matrix:
    st.markdown("#### 👥 RIVAL ROSTER NEEDS & PURCHASING THREAT ENGINE")
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
        needs_str = ", ".join(needs) if needs else "✅ Starting Lineup Filled"
        
        threat_level = "🟢 LOW"
        if m_bid >= 35 and any(pos in needs_str for pos in ['QB', 'RB', 'WR']):
            threat_level = "🔴 EXTREME"
        elif m_bid >= 20:
            threat_level = "🟡 MEDIUM"
            
        roster_str = ", ".join(data['roster'][-4:]) if data['roster'] else "None"
        matrix_rows.append({
            "Slot": s, "Manager": f"⭐ YOU (Slot {s})" if s == my_slot else data['name'],
            "Cash Left": f"${c_left}", "Max Bid": f"${m_bid}", "Picks Made": data['picks'],
            "Threat Level": threat_level, "Urgent Needs": needs_str, "Recent Drafted Roster": roster_str
        })
    st.dataframe(pd.DataFrame(matrix_rows).sort_values(by="Max Bid", ascending=False), use_container_width=True, hide_index=True)

with tab_log:
    if st.session_state.drafted_picks:
        log_rows = [{"Player": v["player_name"], "Pos": v.get("position", "-"), "Price": f"${v['price']}", "Team": f"Team {v['team']}"} for v in st.session_state.drafted_picks.values()]
        st.table(pd.DataFrame(log_rows))
    else:
        st.info("No players drafted yet.")