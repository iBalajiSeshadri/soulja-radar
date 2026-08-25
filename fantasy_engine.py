import json
import os
import re
import requests
import pandas as pd
import numpy as np
from config import (
    SLEEPER_API_URL, SLEEPER_PROJ_URL, SCORING_WEIGHTS, 
    STARTERS_CONFIG, DST_RANKINGS_2026
)

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

def fetch_fftoday_all_projections():
    """
    Ingests official FFToday projections for:
    - IDP: DL (PosID=50), LB (PosID=60), DB (PosID=70)
    - Offense: QB (PosID=10), RB (PosID=20), WR (PosID=30), TE (PosID=40)
    - Overall MFL Power consensus ranks
    """
    print("0. Ingesting FFToday Projections & IDP Data (DL/LB/DB)...")
    ff_ranks = {}
    ff_idp_pts = {}
    
    if not BS4_AVAILABLE:
        print("⚠️ BeautifulSoup not found. Skipping FFToday scrape.")
        return ff_ranks, ff_idp_pts
        
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
    
    # 1. Scrape IDP Positional Projections (DL=50, LB=60, DB=70)
    idp_configs = [(50, 'DL'), (60, 'LB'), (70, 'DB')]
    for pos_id, pos_code in idp_configs:
        for page in range(0, 2):  # Pages 0 and 1 cover top 100 per position
            url = f"https://www.fftoday.com/rankings/playerproj.php?PosID={pos_id}&cur_page={page}"
            try:
                res = requests.get(url, headers=headers, timeout=8)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, 'html.parser')
                    rows = soup.find_all('tr')
                    for row in rows:
                        cols = row.find_all('td')
                        if len(cols) >= 6:
                            link = cols[1].find('a') if len(cols) > 1 else None
                            p_name = link.get_text().strip() if link else cols[1].get_text().strip()
                            c_p = clean_name(p_name)
                            
                            if len(c_p) > 3:
                                # Last column is total projected fantasy points
                                pts_str = cols[-1].get_text().strip()
                                try:
                                    pts_val = float(pts_str)
                                    ff_idp_pts[c_p] = pts_val
                                except ValueError:
                                    pass
            except Exception as e:
                print(f"⚠️ FFToday IDP {pos_code} notice: {e}")
                
    # 2. Scrape MFL Power Overall Consensus Ranks
    for url in ["https://www.fftoday.com/mflpower/playerrank.php", "https://www.fftoday.com/mflpower/playerrank.php?o=2"]:
        try:
            res = requests.get(url, headers=headers, timeout=8)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                for row in soup.find_all('tr'):
                    cols = row.find_all('td')
                    if len(cols) >= 3:
                        r_str = cols[0].get_text().strip()
                        p_str = cols[1].get_text().strip()
                        if r_str.isdigit() and len(p_str) > 3:
                            ff_ranks[clean_name(p_str)] = int(r_str)
        except Exception as e:
            pass

    print(f"✓ Ingested {len(ff_idp_pts)} IDP projections and {len(ff_ranks)} power ranks from FFToday.")
    return ff_ranks, ff_idp_pts

def fetch_dynamic_players(players_db, ff_idp_pts, season="2026"):
    print("1. Ingesting full dynamic player registry (Offense + IDP) from Sleeper...")
    offense_players = []
    idp_players = []
    
    pos_map_idp = {
        'LB': 'LB', 'ILB': 'LB', 'OLB': 'LB',
        'DE': 'DL', 'DT': 'DL', 'DL': 'DL', 'NT': 'DL',
        'CB': 'DB', 'SS': 'DB', 'FS': 'DB', 'DB': 'DB', 'S': 'DB'
    }

    for pid, pdata in players_db.items():
        pos = pdata.get('position')
        team = pdata.get('team')
        status = pdata.get('status')
        if not team or status not in ['Active', 'Questionable', 'Doubtful', None]:
            continue
            
        full_name = f"{pdata.get('first_name', '')} {pdata.get('last_name', '')}".strip()
        c_name = clean_name(full_name)
        if not c_name:
            continue
            
        if pos in ['QB', 'RB', 'WR', 'TE']:
            offense_players.append({
                'sleeper_id': str(pid),
                'player_name': full_name,
                'position': pos,
                'team': team,
                'clean_name': c_name,
                'depth_chart_order': pdata.get('depth_chart_order', 1),
                'search_rank': float(pdata.get('search_rank') or 999)
            })
        elif pos in pos_map_idp:
            idp_players.append({
                'sleeper_id': str(pid),
                'player_name': full_name,
                'position': pos_map_idp[pos],
                'team': team,
                'clean_name': c_name,
                'depth_chart_order': pdata.get('depth_chart_order', 1),
                'search_rank': float(pdata.get('search_rank') or 999)
            })

    df_off = pd.DataFrame(offense_players)
    df_idp = pd.DataFrame(idp_players)

    # Pull Stat Projections from Sleeper API
    proj_url = f"{SLEEPER_PROJ_URL}/projections/nfl/{season}?season_type=regular"
    proj_map = {}
    try:
        p_res = requests.get(proj_url, timeout=8).json()
        for item in p_res:
            pid = str(item.get('player_id'))
            proj_map[pid] = item.get('stats', {})
    except Exception:
        pass

    stat_cols = ['pass_yds', 'pass_tds', 'pass_ints', 'pass_att', 'completions', 'sacks', 
                 'carries', 'rush_yds', 'rush_tds', 'receptions', 'rec_yds', 'rec_tds', 'first_downs']
    for col in stat_cols:
        df_off[col] = 0.0

    for idx, row in df_off.iterrows():
        pid = row['sleeper_id']
        stats = proj_map.get(pid, {})
        df_off.at[idx, 'pass_yds'] = float(stats.get('pass_yd', 0.0))
        df_off.at[idx, 'pass_tds'] = float(stats.get('pass_td', 0.0))
        df_off.at[idx, 'pass_ints'] = float(stats.get('pass_int', 0.0))
        df_off.at[idx, 'pass_att'] = float(stats.get('pass_att', 0.0))
        df_off.at[idx, 'completions'] = float(stats.get('pass_cmp', 0.0))
        df_off.at[idx, 'sacks'] = float(stats.get('pass_sack', 0.0))
        df_off.at[idx, 'carries'] = float(stats.get('rush_att', 0.0))
        df_off.at[idx, 'rush_yds'] = float(stats.get('rush_yd', 0.0))
        df_off.at[idx, 'rush_tds'] = float(stats.get('rush_td', 0.0))
        df_off.at[idx, 'receptions'] = float(stats.get('rec', 0.0))
        df_off.at[idx, 'rec_yds'] = float(stats.get('rec_yd', 0.0))
        df_off.at[idx, 'rec_tds'] = float(stats.get('rec_td', 0.0))
        df_off.at[idx, 'first_downs'] = float(stats.get('rec_fd', 0.0) + stats.get('rush_fd', 0.0))

    # Calculate IDP points by blending Sleeper stat projections with FFToday PosID 50/60/70 projections
    w = SCORING_WEIGHTS
    df_idp['proj_fpts'] = 0.0
    for idx, row in df_idp.iterrows():
        pid = row['sleeper_id']
        c_name = row['clean_name']
        stats = proj_map.get(pid, {})
        
        sleeper_pts = (float(stats.get('idp_tkl_solo', stats.get('tkl_solo', 0.0))) * w['idp_tkl_solo']) + \
                      (float(stats.get('idp_tkl_ast', stats.get('tkl_ast', 0.0))) * w['idp_tkl_ast']) + \
                      (float(stats.get('idp_sack', stats.get('sack', 0.0))) * w['idp_sack']) + \
                      (float(stats.get('idp_int', stats.get('int', 0.0))) * w['idp_int']) + \
                      (float(stats.get('idp_ff', stats.get('ff', 0.0))) * w['idp_ff']) + \
                      (float(stats.get('idp_fr', stats.get('fr', 0.0))) * w['idp_fr']) + \
                      (float(stats.get('idp_pass_def', stats.get('pass_def', 0.0))) * w['idp_pass_def']) + \
                      (float(stats.get('idp_tkl_loss', stats.get('tkl_loss', 0.0))) * w['idp_tkl_loss'])
        
        # Blend in FFToday direct IDP projections when available
        if c_name in ff_idp_pts:
            ff_pts = ff_idp_pts[c_name]
            final_pts = (sleeper_pts * 0.45) + (ff_pts * 0.55) if sleeper_pts > 20.0 else ff_pts
        else:
            final_pts = sleeper_pts
            
        if final_pts < 20.0:
            d_order = row.get('depth_chart_order', 3)
            pos_tier_base = {'LB': 175.0, 'DL': 155.0, 'DB': 150.0}.get(row['position'], 130.0)
            final_pts = max(15.0, pos_tier_base - (d_order * 30.0))
            
        df_idp.at[idx, 'proj_fpts'] = final_pts

    return df_off, df_idp

def calculate_dynamic_natural_tiers(pos_df):
    if len(pos_df) == 0:
        return []
    
    pos = pos_df['position'].iloc[0] if 'position' in pos_df.columns else 'FLEX'
    vorp_vals = pos_df['vorp'].values.astype(float)
    n = len(vorp_vals)
    
    if n <= 1:
        return ["Tier 1"] * n
        
    config = {
        'QB': {'cliff': 12.0, 'max_span': 18.0, 'max_size': 6},
        'RB': {'cliff': 13.0, 'max_span': 20.0, 'max_size': 7},
        'WR': {'cliff': 11.0, 'max_span': 18.0, 'max_size': 8},
        'TE': {'cliff': 12.0, 'max_span': 18.0, 'max_size': 5},
        'LB': {'cliff': 10.0, 'max_span': 16.0, 'max_size': 6},
        'DL': {'cliff': 10.0, 'max_span': 16.0, 'max_size': 6},
        'DB': {'cliff': 10.0, 'max_span': 16.0, 'max_size': 6},
        'DEF': {'cliff': 8.0, 'max_span': 14.0, 'max_size': 6},
    }.get(pos, {'cliff': 11.0, 'max_span': 18.0, 'max_size': 6})
    
    tiers = []
    current_tier = 1
    tier_ceiling_val = vorp_vals[0]
    current_tier_count = 0
    
    for i in range(n):
        curr_val = vorp_vals[i]
        
        if i > 0:
            prev_val = vorp_vals[i - 1]
            adjacent_drop = prev_val - curr_val
            cumulative_span = tier_ceiling_val - curr_val
            
            is_cliff = adjacent_drop >= config['cliff']
            is_span_exceeded = cumulative_span >= config['max_span']
            is_size_exceeded = current_tier_count >= config['max_size']
            
            if (is_cliff or is_span_exceeded or is_size_exceeded) and current_tier < 5:
                current_tier += 1
                tier_ceiling_val = curr_val
                current_tier_count = 0
                
        tiers.append(f"Tier {current_tier}")
        current_tier_count += 1
        
    return tiers

def calculate_master_board(scoring=None, starters=None, superflex=True, include_idp=True):
    """Build the VORP board. Optionally accept a league-specific scoring dict and
    starters config (from Sleeper) so the board reflects ANY league's rules.
    Defaults to the module config (Soulja) for backward compatibility."""
    global SCORING_WEIGHTS, STARTERS_CONFIG
    if scoring:
        SCORING_WEIGHTS = {**SCORING_WEIGHTS, **scoring}
    if starters:
        STARTERS_CONFIG = {**STARTERS_CONFIG, **starters}
    fftoday_ranks, ff_idp_pts = fetch_fftoday_all_projections()
    players_db = requests.get(f"{SLEEPER_API_URL}/players/nfl").json()
    df_off, df_idp = fetch_dynamic_players(players_db, ff_idp_pts)

    # 1. Calculate Offense Baseline Points from League Scoring Rules
    w = SCORING_WEIGHTS
    df_off['incompletions'] = np.maximum(0.0, df_off['pass_att'] - df_off['completions'])
    pass_pts = (df_off['pass_yds'] * w['pass_yd']) + (df_off['pass_tds'] * w['pass_td']) + \
               (df_off['pass_ints'] * w['pass_int']) + (df_off['incompletions'] * w['pass_inc']) + \
               (df_off['sacks'] * w['pass_sack']) + np.where(df_off['pass_yds'] >= 4000, w['bonus_pass_300'], 0)
    rush_pts = (df_off['carries'] * w['rush_att']) + (df_off['rush_yds'] * w['rush_yd']) + \
               (df_off['rush_tds'] * w['rush_td']) + np.where(df_off['rush_yds'] >= 1000, w['bonus_rush_100'], 0)
    
    te_mask = df_off['position'] == 'TE'
    rec_bonus = np.where(te_mask, w['bonus_rec_te'], 0.0)
    fd_bonus = np.where(te_mask, w['bonus_fd_te'], 0.0)
    rec_pts = (df_off['receptions'] * (w['rec'] + rec_bonus)) + \
              (df_off['rec_yds'] * w['rec_yd']) + \
              (df_off['rec_tds'] * w['rec_td']) + \
              (df_off['first_downs'] * fd_bonus) + \
              np.where(df_off['rec_yds'] >= 1000, w['bonus_rec_100'], 0)

    df_off['proj_fpts'] = pass_pts + rush_pts + rec_pts
    df_off = df_off[df_off['proj_fpts'] > 20.0].copy()

    # 2. Defenses (D/ST)
    df_defs = pd.DataFrame([{
        "player_name": d["name"], "position": "DEF", "team": d["team"],
        "proj_fpts": float(d["proj_pts"]), "clean_name": clean_name(d["name"]),
        "depth_chart_order": 1, "search_rank": float(idx + 150)
    } for idx, d in enumerate(DST_RANKINGS_2026)])

    full_df = pd.concat([
        df_off[['player_name', 'position', 'team', 'proj_fpts', 'clean_name', 'depth_chart_order', 'search_rank']],
        df_idp[['player_name', 'position', 'team', 'proj_fpts', 'clean_name', 'depth_chart_order', 'search_rank']],
        df_defs
    ], ignore_index=True)

    # 3. Model Weighting: Blend FFToday Consensus Ranks
    full_df['custom_rank'] = full_df['search_rank']
    for idx, row in full_df.iterrows():
        c_name = row['clean_name']
        if c_name in fftoday_ranks:
            blended = (row['search_rank'] * 0.50) + (fftoday_ranks[c_name] * 0.50)
            full_df.at[idx, 'custom_rank'] = round(blended, 1)

    # 4. Pure Baseline VORP Calculation
    full_df['vorp'] = 0.0
    for pos, threshold in STARTERS_CONFIG.items():
        pos_mask = full_df['position'] == pos
        pos_df = full_df[pos_mask].sort_values(by='proj_fpts', ascending=False)
        if len(pos_df) >= threshold:
            replacement_val = pos_df.iloc[threshold - 1]['proj_fpts']
        elif len(pos_df) > 0:
            replacement_val = pos_df.iloc[-1]['proj_fpts']
        else:
            replacement_val = 0.0
        full_df.loc[pos_mask, 'vorp'] = full_df['proj_fpts'] - replacement_val

    # 5. Apply Multi-Constraint Natural Tiers
    full_df['tier'] = "Tier 4"
    for pos in full_df['position'].unique():
        pm = full_df['position'] == pos
        pos_sorted = full_df[pm].sort_values(by='vorp', ascending=False)
        pos_tiers = calculate_dynamic_natural_tiers(pos_sorted)
        full_df.loc[pos_sorted.index, 'tier'] = pos_tiers

    full_df = full_df.sort_values(by='vorp', ascending=False).reset_index(drop=True)
    full_df['rank'] = full_df.index + 1
    return full_df

if __name__ == "__main__":
    board = calculate_master_board()
    top_board = board.head(300)
    top_board.to_csv("top_150_draft_board.csv", index=False)
    print(f"\n✅ SUCCESS: Calculated clean natural tiers across {len(top_board)} assets to 'top_150_draft_board.csv'!")