LEAGUE_ID = "1385816551680143360"
SLEEPER_API_URL = "https://api.sleeper.app/v1"
SLEEPER_PROJ_URL = "https://api.sleeper.com"

# League Scoring Weights
SCORING_WEIGHTS = {
    'pass_yd': 0.05,
    'pass_td': 4.0,
    'pass_int': -2.0,
    'pass_inc': -0.20,
    'pass_sack': -1.0,
    'bonus_pass_300': 3.0,
    'rush_att': 0.10,
    'rush_yd': 0.10,
    'rush_td': 6.0,
    'bonus_rush_100': 4.0,
    'rec': 0.40,
    'rec_yd': 0.10,
    'rec_td': 6.0,
    'bonus_rec_te': 0.50,
    'bonus_fd_te': 0.50,
    'bonus_rec_100': 5.0,
    # IDP Scoring
    'idp_tkl_solo': 1.5,
    'idp_tkl_ast': 0.75,
    'idp_sack': 4.0,
    'idp_int': 4.0,
    'idp_ff': 3.0,
    'idp_fr': 2.0,
    'idp_pass_def': 1.5,
    'idp_tkl_loss': 2.0,
    'idp_safety': 4.0,
    'idp_def_td': 6.0,
    'def_pts': 220.0
}

# 10-Team Roster Baselines (Superflex Hoarding Baseline = QB26)
STARTERS_CONFIG = {
    'QB': 26,
    'RB': 25,
    'WR': 30,
    'TE': 15,
    'LB': 16,
    'DL': 12,
    'DB': 14,
    'DEF': 10
}

# Consensus 32-Team D/ST Point Projections
DST_RANKINGS_2026 = [
    {"rank": 1,  "name": "Denver Broncos",        "team": "DEN", "proj_pts": 236.0},
    {"rank": 2,  "name": "Houston Texans",         "team": "HOU", "proj_pts": 230.0},
    {"rank": 3,  "name": "Seattle Seahawks",       "team": "SEA", "proj_pts": 225.0},
    {"rank": 4,  "name": "Minnesota Vikings",      "team": "MIN", "proj_pts": 220.0},
    {"rank": 5,  "name": "Los Angeles Chargers",   "team": "LAC", "proj_pts": 215.0},
    {"rank": 6,  "name": "Los Angeles Rams",       "team": "LAR", "proj_pts": 210.0},
    {"rank": 7,  "name": "Philadelphia Eagles",    "team": "PHI", "proj_pts": 206.0},
    {"rank": 8,  "name": "New Orleans Saints",     "team": "NO",  "proj_pts": 202.0},
    {"rank": 9,  "name": "Atlanta Falcons",        "team": "ATL", "proj_pts": 198.0},
    {"rank": 10, "name": "Baltimore Ravens",       "team": "BAL", "proj_pts": 194.0},
    {"rank": 11, "name": "Cleveland Browns",       "team": "CLE", "proj_pts": 188.0},
    {"rank": 12, "name": "Pittsburgh Steelers",    "team": "PIT", "proj_pts": 184.0},
    {"rank": 13, "name": "Detroit Lions",          "team": "DET", "proj_pts": 180.0},
    {"rank": 14, "name": "Jacksonville Jaguars",   "team": "JAC", "proj_pts": 176.0},
    {"rank": 15, "name": "Kansas City Chiefs",     "team": "KC",  "proj_pts": 172.0},
    {"rank": 16, "name": "Buffalo Bills",          "team": "BUF", "proj_pts": 168.0},
    {"rank": 17, "name": "Cincinnati Bengals",     "team": "CIN", "proj_pts": 164.0},
    {"rank": 18, "name": "Green Bay Packers",      "team": "GB",  "proj_pts": 160.0},
    {"rank": 19, "name": "New York Giants",        "team": "NYG", "proj_pts": 156.0},
    {"rank": 20, "name": "San Francisco 49ers",    "team": "SF",  "proj_pts": 152.0},
    {"rank": 21, "name": "Miami Dolphins",         "team": "MIA", "proj_pts": 148.0},
    {"rank": 22, "name": "Tampa Bay Buccaneers",   "team": "TB",  "proj_pts": 144.0},
    {"rank": 23, "name": "Tennessee Titans",       "team": "TEN", "proj_pts": 140.0},
    {"rank": 24, "name": "Arizona Cardinals",      "team": "ARI", "proj_pts": 136.0},
    {"rank": 25, "name": "Chicago Bears",          "team": "CHI", "proj_pts": 132.0},
    {"rank": 26, "name": "Las Vegas Raiders",      "team": "LV",  "proj_pts": 128.0},
    {"rank": 27, "name": "Indianapolis Colts",     "team": "IND", "proj_pts": 124.0},
    {"rank": 28, "name": "New England Patriots",   "team": "NE",  "proj_pts": 120.0},
    {"rank": 29, "name": "New York Jets",          "team": "NYJ", "proj_pts": 116.0},
    {"rank": 30, "name": "Carolina Panthers",      "team": "CAR", "proj_pts": 112.0},
    {"rank": 31, "name": "Washington Commanders",  "team": "WAS", "proj_pts": 108.0},
    {"rank": 32, "name": "Dallas Cowboys",         "team": "DAL", "proj_pts": 104.0}
]