import requests
import pandas as pd
import json

LEAGUE_ID = "1385816551680143360"
SLEEPER_API = "https://api.sleeper.app/v1"

print("1. Fetching NFL Player Master Database...")
players_res = requests.get(f"{SLEEPER_API}/players/nfl").json()

current_league_id = LEAGUE_ID
all_standings = []
all_waivers = []

print("2. Traversing 3 years of Playoff Brackets, Standings & Waiver History...")

for depth in range(3):
    if not current_league_id:
        break
        
    league_res = requests.get(f"{SLEEPER_API}/league/{current_league_id}").json()
    season = league_res.get("season")
    league_name = league_res.get("name")
    
    print(f"  -> Processing Season: {season}...")
    
    # User and Roster mappings
    users_res = requests.get(f"{SLEEPER_API}/league/{current_league_id}/users").json()
    user_map = {u['user_id']: u.get('display_name') for u in users_res}
    
    rosters_res = requests.get(f"{SLEEPER_API}/league/{current_league_id}/rosters").json()
    roster_mgr_map = {}
    for r in rosters_res:
        rid = r.get("roster_id")
        owner_id = r.get("owner_id")
        roster_mgr_map[rid] = user_map.get(owner_id, f"Roster_{rid}")
        
    # --- A. FETCH PLAYOFF BRACKET / FINAL PLACEMENTS ---
    bracket_res = requests.get(f"{SLEEPER_API}/league/{current_league_id}/winners_bracket").json()
    final_ranks = {}
    
    if bracket_res:
        for match in bracket_res:
            p_rank = match.get("p") # Placement match (1 = 1st place/Champ match, 3 = 3rd place match, etc.)
            w_rid = match.get("w")
            l_rid = match.get("l")
            
            if p_rank == 1: # Championship Match
                if w_rid: final_ranks[w_rid] = 1 # CHAMPION
                if l_rid: final_ranks[l_rid] = 2 # RUNNER-UP
            elif p_rank == 3: # 3rd Place Match
                if w_rid: final_ranks[w_rid] = 3
                if l_rid: final_ranks[l_rid] = 4
            elif p_rank == 5: # 5th Place Match
                if w_rid: final_ranks[w_rid] = 5
                if l_rid: final_ranks[l_rid] = 6

    # Regular season standings + playoff final finish
    for r in rosters_res:
        rid = r.get("roster_id")
        mgr = roster_mgr_map.get(rid, "Unknown")
        st = r.get("settings", {})
        
        wins = st.get("wins", 0)
        losses = st.get("losses", 0)
        ties = st.get("ties", 0)
        fpts = st.get("fpts", 0) + (st.get("fpts_decimal", 0) / 100.0)
        fpts_against = st.get("fpts_against", 0) + (st.get("fpts_against_decimal", 0) / 100.0)
        
        # Final rank fallback if not placed in top bracket
        finish_rank = final_ranks.get(rid, st.get("rank", 10))
        
        all_standings.append({
            "season": season,
            "manager": mgr,
            "roster_id": rid,
            "reg_wins": wins,
            "reg_losses": losses,
            "reg_fpts": round(fpts, 2),
            "fpts_against": round(fpts_against, 2),
            "final_finish_rank": finish_rank
        })

    # --- B. FETCH ALL WEEKLY WAIVER TRANSACTIONS ---
    for week in range(1, 18):
        trx_res = requests.get(f"{SLEEPER_API}/league/{current_league_id}/transactions/{week}").json()
        if not trx_res:
            continue
            
        for t in trx_res:
            t_type = t.get("type")
            t_status = t.get("status")
            
            if t_type == "waiver" and t_status == "complete":
                adds = t.get("adds") or {}
                drops = t.get("drops") or {}
                settings = t.get("settings") or {}
                faab_bid = settings.get("waiver_bid", 0)
                
                # Get creator / roster ID
                rid = t.get("roster_ids", [None])[0]
                mgr = roster_mgr_map.get(rid, "Unknown")
                
                for pid, to_rid in adds.items():
                    p_info = players_res.get(pid, {})
                    first_name = p_info.get("first_name", "")
                    last_name = p_info.get("last_name", "")
                    player_added = f"{first_name} {last_name}".strip() or pid
                    pos = p_info.get("position", "")
                    
                    # Dropped player
                    player_dropped = "None"
                    if drops:
                        d_pid = list(drops.keys())[0]
                        d_info = players_res.get(d_pid, {})
                        player_dropped = f"{d_info.get('first_name', '')} {d_info.get('last_name', '')}".strip() or d_pid

                    all_waivers.append({
                        "season": season,
                        "week": week,
                        "manager": mgr,
                        "player_added": player_added,
                        "position": pos,
                        "player_dropped": player_dropped,
                        "faab_bid": faab_bid
                    })

    # Move to previous season
    current_league_id = league_res.get("previous_league_id")

# Export Standings & Playoff Finishes
df_standings = pd.DataFrame(all_standings)
df_standings.to_csv("soulja_3yr_final_standings.csv", index=False)

# Export Waivers
df_waivers = pd.DataFrame(all_waivers)
df_waivers.to_csv("soulja_3yr_waivers.csv", index=False)

print("\n=======================================================")
print(f"[SUCCESS] Exported 3-Year Final Standings -> 'soulja_3yr_final_standings.csv' ({len(df_standings)} rows)")
print(f"[SUCCESS] Exported 3-Year Complete Waiver History -> 'soulja_3yr_waivers.csv' ({len(df_waivers)} rows)")
print("=======================================================")