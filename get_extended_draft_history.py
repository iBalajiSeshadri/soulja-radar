import requests
import pandas as pd

LEAGUE_ID = "1385816551680143360"
SLEEPER_API = "https://api.sleeper.app/v1"

print("Connecting to Sleeper API to fetch active player database...")
players_res = requests.get(f"{SLEEPER_API}/players/nfl").json()

current_league_id = LEAGUE_ID
all_picks = []

print("Traversing league history across past 3 seasons...")

for depth in range(3):
    if not current_league_id:
        break
        
    league_res = requests.get(f"{SLEEPER_API}/league/{current_league_id}").json()
    season = league_res.get("season")
    league_name = league_res.get("name")
    
    # Map user IDs to display names for this specific season
    users_res = requests.get(f"{SLEEPER_API}/league/{current_league_id}/users").json()
    user_map = {u['user_id']: u.get('display_name') for u in users_res}
    
    drafts_res = requests.get(f"{SLEEPER_API}/league/{current_league_id}/drafts").json()
    
    for d in drafts_res:
        draft_id = d.get("draft_id")
        draft_type = d.get("type")
        
        picks_res = requests.get(f"{SLEEPER_API}/draft/{draft_id}/picks").json()
        
        for p in picks_res:
            pid = p.get("player_id")
            p_info = players_res.get(pid, {})
            
            # Extract player names and position safely
            first_name = p.get("metadata", {}).get("first_name") or p_info.get("first_name", "")
            last_name = p.get("metadata", {}).get("last_name") or p_info.get("last_name", "")
            full_name = f"{first_name} {last_name}".strip()
            pos = p.get("metadata", {}).get("position") or p_info.get("position", "")
            
            # Extract winning bid amount
            amount_str = p.get("metadata", {}).get("amount", "0")
            try:
                amount = int(amount_str)
            except ValueError:
                amount = 0
                
            picked_by_id = p.get("picked_by")
            manager = user_map.get(picked_by_id, "Unknown")
            
            all_picks.append({
                "season": season,
                "nomination_order": p.get("pick_no"),
                "player_name": full_name,
                "position": pos,
                "winning_bid": amount,
                "manager": manager,
                "draft_type": draft_type
            })
            
    # Move backwards to previous season
    current_league_id = league_res.get("previous_league_id")
python3 get_extended_draft_history.py
df = pd.DataFrame(all_picks)

if not df.empty:
    output_filename = "soulja_3yr_auction_history.csv"
    df.to_csv(output_filename, index=False)
    print(f"\n=======================================================")
    print(f"[SUCCESS] Processed {len(df)} picks across {df['season'].nunique()} seasons!")
    print(f"File exported directly to: '{output_filename}'")
    print(f"=======================================================")
else:
    print("No draft picks found in Sleeper history.")