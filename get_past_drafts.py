import requests
import json

LEAGUE_ID = "1385816551680143360"
URL = f"https://api.sleeper.app/v1/league/{LEAGUE_ID}"

print("Connecting to Sleeper to fetch league draft history...")
league_data = requests.get(URL).json()
previous_league_id = league_data.get("previous_league_id")

target_league = previous_league_id if previous_league_id else LEAGUE_ID

# Get drafts
drafts = requests.get(f"https://api.sleeper.app/v1/league/{target_league}/drafts").json()
users = requests.get(f"{URL}/users").json()
user_map = {u['user_id']: u.get('display_name') for u in users}

if not drafts:
    print("No draft records found for this league ID.")
else:
    for d in drafts:
        draft_id = d.get("draft_id")
        season = d.get("season")
        draft_type = d.get("type")
        print(f"\n=======================================================")
        print(f"  FOUND {season} DRAFT (Type: {draft_type.upper()})")
        print(f"=======================================================")
        
        picks = requests.get(f"https://api.sleeper.app/v1/draft/{draft_id}/picks").json()
        
        # Aggregate spending per manager if auction
        manager_spend = {}
        for p in picks:
            manager = user_map.get(p.get("picked_by"), "Unknown")
            amount = p.get("metadata", {}).get("amount", "N/A")
            player_name = f"{p.get('metadata', {}).get('first_name', '')} {p.get('metadata', {}).get('last_name', '')}"
            
            if manager not in manager_spend:
                manager_spend[manager] = []
            manager_spend[manager].append((player_name, amount))
            
        for manager, spend_list in manager_spend.items():
            print(f"\nManager: {manager}")
            # Show top 5 highest spent picks
            top_picks = sorted([x for x in spend_list if x[1] != 'N/A'], key=lambda x: int(x[1]), reverse=True)[:5]
            for name, cost in top_picks:
                print(f"   -> {name}: ${cost}")