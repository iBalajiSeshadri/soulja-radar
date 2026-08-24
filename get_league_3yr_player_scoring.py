import requests
import pandas as pd
import json

LEAGUE_ID = "1385816551680143360"
SLEEPER_API = "https://api.sleeper.app/v1"

print("1. Connecting to Sleeper to fetch Soulja Soulja Scoring Settings...")
league_res = requests.get(f"{SLEEPER_API}/league/{LEAGUE_ID}").json()
s = league_res.get("scoring_settings", {})

print("2. Fetching NFL Player Master Database...")
players_res = requests.get(f"{SLEEPER_API}/players/nfl").json()

all_season_records = []

for season in [2023, 2024, 2025]:
    print(f"3. Fetching official NFL player stats for {season} season...")
    stats_url = f"{SLEEPER_API}/stats/nfl/regular/{season}"
    stats_res = requests.get(stats_url).json()
    
    for pid, pdata in players_res.items():
        pos = pdata.get("position")
        if not pos or pos not in ['QB', 'RB', 'WR', 'TE', 'DEF', 'K', 'LB', 'DL', 'DB', 'IDP']:
            continue
            
        p_stats = stats_res.get(pid, {})
        if not p_stats:
            continue
            
        # Calculate custom fantasy points using exact Soulja Soulja scoring rules
        total_pts = 0.0
        for stat_key, stat_val in p_stats.items():
            if stat_key in s:
                total_pts += float(stat_val) * float(s[stat_key])
                
        # Only record players with meaningful fantasy scoring (> 5.0 pts)
        if total_pts > 5.0:
            first_name = pdata.get("first_name", "")
            last_name = pdata.get("last_name", "")
            full_name = f"{first_name} {last_name}".strip() if first_name else pdata.get("search_full_name", pid)
            
            all_season_records.append({
                "season": season,
                "sleeper_id": pid,
                "player_name": full_name,
                "position": pos,
                "team": pdata.get("team", "FA"),
                "total_pts": round(total_pts, 2)
            })

df = pd.DataFrame(all_season_records)

# Calculate positional rank per season
df['pos_rank'] = df.groupby(['season', 'position'])['total_pts'].rank(ascending=False, method='min').astype(int)

# Sort by season and total points
df = df.sort_values(by=['season', 'total_pts'], ascending=[False, False]).reset_index(drop=True)

output_file = "soulja_3yr_player_scoring.csv"
df.to_csv(output_file, index=False)
print(f"\n=======================================================")
print(f"[SUCCESS] Generated historical scoring file across 2023, 2024, and 2025!")
print(f"File exported directly to: '{output_file}' ({len(df)} total player-season rows)")
print(f"=======================================================")