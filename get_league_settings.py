import requests
import json

LEAGUE_ID = "1385816551680143360"
URL = f"https://api.sleeper.app/v1/league/{LEAGUE_ID}"

res = requests.get(URL).json()
users = requests.get(f"{URL}/users").json()
user_map = {u['user_id']: u.get('display_name') for u in users}

roster_positions = res.get('roster_positions', [])
scoring = res.get('scoring_settings', {})

print("=======================================================")
print(f"LEAGUE NAME: {res.get('name')} ({res.get('total_rosters')} Teams)")
print("=======================================================")
print("\n--- ROSTER SLOTS ---")
for pos in set(roster_positions):
    print(f"  {pos}: {roster_positions.count(pos)}")

print("\n--- SCORING RULES ---")
for rule, val in scoring.items():
    print(f"  {rule}: {val}")

print("\n--- MANAGERS & TEAMS ---")
rosters = requests.get(f"{URL}/rosters").json()
for r in rosters:
    owner = user_map.get(r.get('owner_id'), 'Unowned')
    print(f"  Roster {r.get('roster_id')}: {owner}")