import requests
import pandas as pd
import numpy as np
import time
import os
import re
import json
import sys

# Import Rich for Flicker-Free UI
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.live import Live
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

console = Console() if RICH_AVAILABLE else None

MANAGER_PROFILES = {
    'kopite': 'CAP HEMOPHILIAC [High Overpay Risk]',
    'addyrao': 'SUNK-COST SPENDER [QB/RB Anchor]',
    'bluewatermelon': 'BALANCED WHALE [TE/WR Focus]',
    'cardinalsin': 'POSITIONAL PANIC [RB Dependent]',
    'chaituat': 'IMPULSE PIVOTER [Recency Bias]',
    'rookieqbme': 'VALUE HESITATOR [Mid-Tier Collector]',
    'siddharthasagar': 'DRAFT MASTER [Hesitant Value]',
    'skongara': 'FAAB ASSASSIN [High Floor / Playoff DEF Nukes]',
    'vnayini': 'ANTI-WHALE [$40 Ceiling Anchor]',
    'djballz': 'PREDATORY ARBITRAGE [User]',
    'balaji': 'PREDATORY ARBITRAGE [User]'
}

def clean_name(name):
    if not isinstance(name, str):
        return ""
    name = name.lower()
    name = re.sub(r"[^\w\s]", "", name)
    name = re.sub(r"\b(jr|sr|iii|ii|iv|v)\b", "", name)
    return " ".join(name.split())

def assign_tiers(df):
    df = df.copy()
    df['tier'] = 1
    for pos, group in df.groupby('position'):
        q85 = group['vorp'].quantile(0.85)
        q60 = group['vorp'].quantile(0.60)
        q30 = group['vorp'].quantile(0.30)
        
        def calc_tier(v):
            if v >= q85: return 1
            elif v >= q60: return 2
            elif v >= q30: return 3
            else: return 4
            
        df.loc[group.index, 'tier'] = group['vorp'].apply(calc_tier)
    return df

def apply_camp_news_and_injuries(df_board, sleeper_players_db):
    """
    1. Checks Sleeper API real-time status (IR, PUP, Out, Holdout)
    2. Reads local 'camp_overrides.json' for hype/risk multipliers
    """
    df = df_board.copy()
    camp_overrides = {}
    if os.path.exists("camp_overrides.json"):
        try:
            with open("camp_overrides.json", "r") as f:
                camp_overrides = json.load(f)
        except Exception:
            pass
            
    updated_vorps = []
    camp_notes = []
    
    for idx, row in df.iterrows():
        p_name = row['player_name']
        vorp = row['vorp']
        note = ""
        multiplier = 1.0
        
        # Check Sleeper Injury / Active Status
        c_name = row.get('clean_name', clean_name(p_name))
        s_info = sleeper_players_db.get(c_name, {})
        inj_status = s_info.get('injury_status') or s_info.get('status')
        
        if inj_status in ['IR', 'PUP', 'Out']:
            multiplier *= 0.0
            note = f"❌ OUT ({inj_status})"
        elif inj_status == 'Doubtful':
            multiplier *= 0.40
            note = f"⚠️ DOUBTFUL"
        elif inj_status == 'Questionable':
            multiplier *= 0.85
            note = f"🩹 QUESTIONABLE"
            
        # Check Manual Camp Overrides File
        if p_name in camp_overrides:
            c_data = camp_overrides[p_name]
            multiplier *= c_data.get('multiplier', 1.0)
            c_note = c_data.get('note', '')
            note = f"{note} | {c_note}".strip(" |")
            
        adjusted_vorp = round(vorp * multiplier, 2)
        updated_vorps.append(adjusted_vorp)
        camp_notes.append(note if note else "OK")
        
    df['vorp'] = updated_vorps
    df['camp_intel'] = camp_notes
    return df

# 1. Load Custom VORP Board
board_file = "top_150_draft_board.csv"
if not os.path.exists(board_file):
    print(f"Error: '{board_file}' missing! Run fantasy_engine.py first.")
    sys.exit(1)

df_board = pd.read_csv(board_file)
df_board.columns = [c.lower() for c in df_board.columns]
if 'player_name' not in df_board.columns and 'player' in df_board.columns:
    df_board['player_name'] = df_board['player']

df_board['clean_name'] = df_board['player_name'].apply(clean_name)
df_board = assign_tiers(df_board)
df_board['picked'] = False

TOTAL_LEAGUE_CASH = 2000
TOTAL_ROSTER_SLOTS = 170
surplus_cash = TOTAL_LEAGUE_CASH - TOTAL_ROSTER_SLOTS
total_pos_vorp = df_board[df_board['vorp'] > 0]['vorp'].sum()

os.system('clear' if os.name == 'posix' else 'cls')
print("==================================================================")
print("   SOULJA SOULJA LIVE DRAFT ASSISTANT v5.2 (CAMP & INJURY SYNC)")
print("==================================================================")

draft_id = input("\nPaste Sleeper Mock/Real Draft ID: ").strip()

try:
    draft_slot_input = int(input("Enter your Team / Draft Slot # (e.g. 1 for Team 1): ").strip())
except ValueError:
    draft_slot_input = 1

SLEEPER_API = "https://api.sleeper.app/v1"

# Fetch Sleeper Player DB for live injury status
sleeper_players_db = {}
try:
    print("\nSyncing live Sleeper NFL Player Database & Injury Status...")
    raw_p_db = requests.get(f"{SLEEPER_API}/players/nfl", timeout=8).json()
    if isinstance(raw_p_db, dict):
        for pid, pdata in raw_p_db.items():
            fn = pdata.get('first_name', '')
            ln = pdata.get('last_name', '')
            full_c = clean_name(f"{fn} {ln}")
            sleeper_players_db[full_c] = {
                'status': pdata.get('status'),
                'injury_status': pdata.get('injury_status')
            }
    print("✓ Live Injury Database Synced successfully!")
except Exception:
    print("⚠️ Could not fetch live Sleeper Player DB. Falling back to local board.")

# Apply Camp Overrides & Injury Multipliers
df_board = apply_camp_news_and_injuries(df_board, sleeper_players_db)

# Fetch Draft Users & Map Managers
user_id_map = {}
slot_manager_map = {}

try:
    draft_users = requests.get(f"{SLEEPER_API}/draft/{draft_id}/users", timeout=5).json()
    if isinstance(draft_users, list):
        for u in draft_users:
            uid = u.get('user_id')
            dname = u.get('display_name', 'Manager').strip()
            user_id_map[uid] = dname
            
    draft_info = requests.get(f"{SLEEPER_API}/draft/{draft_id}", timeout=5).json()
    d_type = draft_info.get("type", "snake").lower()
    is_snake = (d_type != "auction")
    num_teams = draft_info.get("settings", {}).get("teams", 10)
    
    draft_slots = draft_info.get("draft_order", {})
    if draft_slots:
        for uid, slot_num in draft_slots.items():
            mgr_name = user_id_map.get(uid, f"Team_{slot_num}")
            slot_manager_map[int(slot_num)] = mgr_name
except Exception:
    d_type = "snake"
    is_snake = True
    num_teams = 10

processed_picks = set()
recent_picks_list = []
league_cash_remaining = TOTAL_LEAGUE_CASH
open_slots_remaining = TOTAL_ROSTER_SLOTS

all_team_rosters = {i: {'QB': 0, 'RB': 0, 'WR': 0, 'TE': 0, 'DEF': 0, 'LB': 0, 'DL': 0, 'DB': 0} for i in range(1, num_teams + 1)}
my_player_byes = {'QB': [], 'RB': [], 'WR': [], 'TE': []}
my_cash_spent = 0

def fetch_sleeper_picks(d_id):
    retries = 3
    for attempt in range(retries):
        try:
            res = requests.get(f"{SLEEPER_API}/draft/{d_id}/picks", timeout=4)
            if res.status_code == 200:
                return res.json()
        except Exception:
            time.sleep(1)
    return None

def calculate_radar_scores(df_unpicked, my_counts, run_counts, next_team_counts):
    max_board_vorp = df_unpicked['vorp'].max() if not df_unpicked.empty else 0
    
    qb = my_counts.get('QB', 0)
    rb = my_counts.get('RB', 0)
    wr = my_counts.get('WR', 0)
    te = my_counts.get('TE', 0)
    def_cnt = my_counts.get('DEF', 0)
    idp_cnt = my_counts.get('LB', 0) + my_counts.get('DL', 0) + my_counts.get('DB', 0) + my_counts.get('IDP', 0)
    
    scores = []
    tags = []
    
    for idx, row in df_unpicked.iterrows():
        pos = row['position']
        vorp = row['vorp']
        tier = row['tier']
        p_bye = row.get('bye_week', 0) if 'bye_week' in row else row.get('bye', 0)
        c_intel = row.get('camp_intel', 'OK')
        
        starter_needed = False
        urgency = 1.0
        
        if pos == 'QB' and qb < 2: starter_needed = True; urgency = 1.5 if qb == 0 else 1.3
        elif pos == 'RB' and rb < 2: starter_needed = True; urgency = 1.4 if rb == 0 else 1.3
        elif pos == 'WR' and wr < 2: starter_needed = True; urgency = 1.3 if wr == 0 else 1.2
        elif pos == 'TE' and te < 1: starter_needed = True; urgency = 1.4
        elif pos == 'DEF' and def_cnt < 1: starter_needed = True; urgency = 1.1
        elif pos in ['LB', 'DL', 'DB', 'IDP'] and idp_cnt < 1: starter_needed = True; urgency = 1.1
            
        # Base Score
        if starter_needed:
            score = 200.0 + (vorp * urgency)
            tag = "STARTER NEED"
        else:
            if pos == 'QB':
                score = vorp * 0.01 if qb >= 2 else vorp * 0.10
            elif pos == 'TE':
                score = vorp * 0.10 if te >= 2 else vorp * 0.30
            elif pos == 'RB':
                score = vorp * 0.70
            elif pos == 'WR':
                score = vorp * 0.60
            else:
                score = vorp * 0.10
            tag = "BENCH DEPTH"
            
        # Append Camp Intel Note if present
        if c_intel and c_intel != "OK":
            tag = f"{tag} | {c_intel}"

        # Feature 1: INSANE VALUE OVERRIDE (DISABLED IF SATURATED)
        is_pos_maxed = (
            (pos == 'QB' and qb >= 2) or
            (pos == 'TE' and te >= 2) or
            (pos == 'DEF' and def_cnt >= 1) or
            (pos in ['LB', 'DL', 'DB', 'IDP'] and idp_cnt >= 1)
        )
        
        if vorp > 15.0 and not is_pos_maxed:
            if vorp >= 100.0 or (max_board_vorp > 0 and vorp >= max_board_vorp * 0.85):
                if not starter_needed:
                    score = max(score, 230.0 + vorp)
                    tag = "🔥 INSANE VALUE / TIER FALL"
                
        # Feature 2: POSITIONAL RUN & TIER CLIFF BOOST (STRICTLY VORP > 0)
        if vorp > 0:
            pos_unpicked = df_unpicked[df_unpicked['position'] == pos]
            if not pos_unpicked.empty:
                min_tier = pos_unpicked['tier'].min()
                rem_in_tier = len(pos_unpicked[pos_unpicked['tier'] == min_tier])
                
                if run_counts.get(pos, 0) >= 2 and rem_in_tier <= 2 and tier == min_tier:
                    score += 40.0
                    tag += f" | 🚨 TIER CLIFF ({rem_in_tier} in T{min_tier})"
                
        # Feature 3: OPPONENT BLOCKING
        next_needs_pos = False
        if pos == 'QB' and next_team_counts.get('QB', 0) < 2: next_needs_pos = True
        elif pos == 'RB' and next_team_counts.get('RB', 0) < 2: next_needs_pos = True
        elif pos == 'TE' and next_team_counts.get('TE', 0) < 1: next_needs_pos = True
        elif pos == 'WR' and next_team_counts.get('WR', 0) < 2: next_needs_pos = True
        
        if next_needs_pos and starter_needed and vorp > 0:
            score += 25.0
            tag += " | 🛡️ BLOCK NEXT"
            
        # Feature 4: BYE WEEK SHIELD WARNING
        if pos in ['QB', 'RB', 'WR', 'TE'] and p_bye > 0:
            if p_bye in my_player_byes.get(pos, []):
                tag += f" | ⚠️ BYE CLASH (Wk {p_bye})"
                score -= 15.0
                
        scores.append(round(score, 1))
        tags.append(tag)
        
    df_unpicked['radar_score'] = scores
    df_unpicked['radar_tag'] = tags
    return df_unpicked

def generate_dashboard():
    unpicked = df_board[df_board['picked'] != True].copy()
    
    recent_pos = [p['pos'] for p in recent_picks_list[-6:]] if recent_picks_list else []
    run_counts = pd.Series(recent_pos).value_counts().to_dict()
    
    next_team_slot = (draft_slot_input % num_teams) + 1
    next_team_counts = all_team_rosters.get(next_team_slot, {})
    next_mgr_raw = slot_manager_map.get(next_team_slot, f"Team {next_team_slot}")
    next_mgr_profile = MANAGER_PROFILES.get(next_mgr_raw.lower(), "NEUTRAL STRATEGIST")
    
    my_counts = all_team_rosters.get(draft_slot_input, {})
    
    unpicked = calculate_radar_scores(unpicked, my_counts, run_counts, next_team_counts)
    
    curr_pick = len(processed_picks) + 1
    curr_round = ((curr_pick - 1) // num_teams) + 1
    curr_round_pick = ((curr_pick - 1) % num_teams) + 1
    
    on_clock_slot = curr_round_pick if (curr_round % 2 != 0 or not is_snake) else (num_teams - curr_round_pick + 1)
    is_my_turn = (on_clock_slot == draft_slot_input)
    is_on_deck = abs(on_clock_slot - draft_slot_input) == 1
    
    if is_my_turn or is_on_deck:
        sys.stdout.write('\a')
        sys.stdout.flush()

    if RICH_AVAILABLE:
        table_targets = Table(title="🎯 TOP OVERALL RADAR TARGETS (NEED + VALUE)", box=box.ROUNDED, header_style="bold cyan")
        table_targets.add_column("Rank", style="dim", width=6)
        table_targets.add_column("Player", style="bold white", width=20)
        table_targets.add_column("Pos", style="yellow", width=6)
        table_targets.add_column("Team", width=6)
        table_targets.add_column("VORP", justify="right", width=8)
        table_targets.add_column("Score", justify="right", style="bold green", width=8)
        table_targets.add_column("Action Tag & Intel", style="bold magenta")

        top_radar = unpicked.sort_values(by='radar_score', ascending=False).head(5)
        for _, r in top_radar.iterrows():
            table_targets.add_row(
                str(r['custom_rank']), r['player_name'], r['position'], r['team'],
                f"{r['vorp']:.1f}", f"{r['radar_score']:.1f}", r['radar_tag']
            )

        table_buckets = Table(title="📊 POSITIONAL BUCKET MATRIX (TOP 3 AVAILABLE PER POSITION)", box=box.SQUARE, header_style="bold yellow")
        table_buckets.add_column("Bucket", style="bold yellow", width=10)
        table_buckets.add_column("Rank", style="dim", width=6)
        table_buckets.add_column("Player Name", style="bold white", width=20)
        table_buckets.add_column("Team", width=6)
        table_buckets.add_column("VORP", justify="right", width=8)
        table_buckets.add_column("Need Score", justify="right", style="bold green", width=10)
        table_buckets.add_column("Status / Tag", style="magenta")

        buckets = ['RB', 'WR', 'TE', 'QB', 'DEF/IDP']
        for b in buckets:
            if b == 'DEF/IDP':
                p_df = unpicked[unpicked['position'].isin(['DEF', 'LB', 'DL', 'DB', 'IDP'])].sort_values(by='radar_score', ascending=False).head(3)
            else:
                p_df = unpicked[unpicked['position'] == b].sort_values(by='radar_score', ascending=False).head(3)
                
            for _, r in p_df.iterrows():
                table_buckets.add_row(
                    b, str(r['custom_rank']), r['player_name'], r['team'],
                    f"{r['vorp']:.1f}", f"{r['radar_score']:.1f}", r['radar_tag']
                )

        status_text = f"[bold green]MY TURN NOW![/bold green]" if is_my_turn else (f"[bold yellow]ON DECK (1 Away)[/bold yellow]" if is_on_deck else "Waiting...")
        
        league_qb_open = sum([max(0, 2 - r.get('QB', 0)) for r in all_team_rosters.values()])
        league_rb_open = sum([max(0, 2 - r.get('RB', 0)) for r in all_team_rosters.values()])
        league_wr_open = sum([max(0, 2 - r.get('WR', 0)) for r in all_team_rosters.values()])
        league_te_open = sum([max(0, 1 - r.get('TE', 0)) for r in all_team_rosters.values()])

        header_pnl = Panel(
            f"[bold white]Draft Type:[/bold white] {d_type.upper()} | [bold white]Pick:[/bold white] Rd {curr_round}, Pick {curr_round_pick} (#{curr_pick}) | [bold white]Status:[/bold white] {status_text}\n"
            f"[bold white]My Roster (Team {draft_slot_input}):[/bold white] {my_counts}\n"
            f"[bold white]Next Manager Up (Slot {next_team_slot}):[/bold white] [bold red]{next_mgr_raw.upper()}[/bold red] ({next_mgr_profile})\n"
            f"[bold white]League Open Starters:[/bold white] QB:[cyan]{league_qb_open}[/cyan] | RB:[yellow]{league_rb_open}[/yellow] | WR:[blue]{league_wr_open}[/blue] | TE:[green]{league_te_open}[/green]",
            title="🏈 SOULJA SOULJA LIVE DRAFT RADAR v5.2",
            border_style="red" if is_my_turn else "blue"
        )

        console.clear()
        console.print(header_pnl)
        console.print(table_targets)
        console.print(table_buckets)
    else:
        os.system('clear' if os.name == 'posix' else 'cls')
        print("=================================================================================")
        print(f" 🏈 SOULJA SOULJA DRAFT RADAR v5.2 | Rd {curr_round}, Pick {curr_round_pick} (#{curr_pick})")
        print(f" 👤 MY ROSTER (TEAM {draft_slot_input}): {my_counts}")
        print(f" 👁️ NEXT MANAGER UP (SLOT {next_team_slot}): {next_mgr_raw.upper()} ({next_mgr_profile})")
        print("=================================================================================")
        print("\n🎯 TOP RADAR TARGETS FOR YOUR ROSTER:")
        top_radar = unpicked.sort_values(by='radar_score', ascending=False).head(5)
        print(top_radar[['custom_rank', 'player_name', 'position', 'team', 'vorp', 'radar_score', 'radar_tag']].to_string(index=False))

# Main Execution Loop
while True:
    try:
        picks_res = fetch_sleeper_picks(draft_id)
        
        new_picks = False
        if isinstance(picks_res, list):
            for p in picks_res:
                pick_no = p.get("pick_no")
                if pick_no not in processed_picks:
                    processed_picks.add(pick_no)
                    new_picks = True
                    
                    p_meta = p.get("metadata", {})
                    first_n = p_meta.get("first_name", "")
                    last_n = p_meta.get("last_name", "")
                    raw_p_name = f"{first_n} {last_n}".strip() or p_meta.get("player_name", "Unknown Player")
                    c_name = clean_name(raw_p_name)
                    
                    try:
                        amount = int(p_meta.get("amount", 1))
                    except (ValueError, TypeError):
                        amount = 1
                    
                    slot = p.get("draft_slot", 1)
                    df_board.loc[df_board['clean_name'] == c_name, 'picked'] = True
                    
                    p_match = df_board[df_board['clean_name'] == c_name]
                    if not p_match.empty:
                        p_pos = p_match.iloc[0]['position']
                        p_bye = p_match.iloc[0].get('bye_week', 0)
                        all_team_rosters[slot][p_pos] = all_team_rosters[slot].get(p_pos, 0) + 1
                        recent_picks_list.append({'player': raw_p_name, 'pos': p_pos, 'slot': slot})
                        
                        if slot == draft_slot_input and p_pos in my_player_byes:
                            my_player_byes[p_pos].append(p_bye)

                    league_cash_remaining -= amount
                    open_slots_remaining -= 1

        if new_picks or len(processed_picks) == 0:
            generate_dashboard()

        time.sleep(2.0)

    except KeyboardInterrupt:
        print("\n[Exiting Live Draft Assistant v5.2]")
        break
    except Exception as e:
        time.sleep(2.0)