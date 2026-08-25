"""
build_dst_streamers.py — D/ST streaming-value layer.

Fuses two free, stable signals into a per-team D/ST streamer read for the
opening slate (Weeks 1-4):

  1. Opening schedule (Weeks 1-4 opponents) from nflverse 2026 schedule.
  2. Opponent OFFENSE strength proxy = that opponent's 2025 points/game
     (weak offense faced = good matchup for streaming a defense).
  3. DC-change context from coaching_scheme.json (_defense[TEAM].changed/dc/scheme).

Writes dst_streamers.json:
  { "_meta": {...},
    "TEAM": {
      "open_games": [{"wk":1,"opp":"...","home":true,"opp_ppg":14.2}, ...],
      "avg_opp_ppg": 17.3,          # lower = softer opening slate
      "soft_open": true,            # faces bottom-third offenses early
      "dc": "...", "dc_changed": bool, "def_scheme": "...",
      "streamer_note": "one-line actionable read"
    }, ... }
"""

import csv
import io
import json
import os
import requests
from collections import defaultdict

GAMES_URL = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}
OPEN_WEEKS = 4

# nflverse abbreviations -> the abbreviations used in coaching_scheme.json / the board.
NORM = {"LA": "LAR", "LAR": "LAR", "LAC": "LAC", "LV": "LV", "OAK": "LV",
        "WAS": "WAS", "WSH": "WAS", "SD": "LAC", "STL": "LAR", "JAC": "JAC",
        "JAX": "JAC", "TB": "TB", "TBB": "TB", "NO": "NO", "NOS": "NO",
        "GB": "GB", "GNB": "GB", "KC": "KC", "KAN": "KC", "SF": "SF", "SFO": "SF",
        "NE": "NE", "NWE": "NE", "ARI": "ARI", "ARZ": "ARI"}


def norm(t):
    return NORM.get(t, t)


def fetch_games():
    r = requests.get(GAMES_URL, headers=UA, timeout=25)
    r.raise_for_status()
    return list(csv.DictReader(io.StringIO(r.text)))


def offense_ppg_2025(rows):
    """Per-team 2025 offensive points/game (weak = good DST matchup)."""
    pf = defaultdict(list)
    for x in rows:
        if x.get("season") == "2025" and x.get("game_type") == "REG" \
           and x.get("home_score") and x.get("away_score"):
            try:
                hs, as_ = int(x["home_score"]), int(x["away_score"])
            except ValueError:
                continue
            pf[norm(x["home_team"])].append(hs)
            pf[norm(x["away_team"])].append(as_)
    return {t: round(sum(v) / len(v), 1) for t, v in pf.items() if v}


def opening_schedule_2026(rows):
    """Per-team list of {wk, opp, home} for Weeks 1..OPEN_WEEKS."""
    sched = defaultdict(list)
    for x in rows:
        if x.get("season") != "2026" or x.get("game_type") != "REG":
            continue
        try:
            wk = int(x["week"])
        except (ValueError, TypeError):
            continue
        if wk > OPEN_WEEKS:
            continue
        home, away = norm(x["home_team"]), norm(x["away_team"])
        sched[home].append({"wk": wk, "opp": away, "home": True})
        sched[away].append({"wk": wk, "opp": home, "home": False})
    for t in sched:
        sched[t].sort(key=lambda g: g["wk"])
    return sched


def load_def_context():
    if not os.path.exists("coaching_scheme.json"):
        return {}
    try:
        d = json.load(open("coaching_scheme.json"))
    except Exception:
        return {}
    return d.get("_defense", {})


def main():
    print("1. Fetching nflverse schedule + scores...")
    rows = fetch_games()
    ppg = offense_ppg_2025(rows)
    sched = opening_schedule_2026(rows)
    defc = load_def_context()
    print(f"   {len(ppg)} teams PPG, {len(sched)} teams with 2026 opening slate.")

    league_avg = round(sum(ppg.values()) / len(ppg), 1) if ppg else 22.0
    # "soft" threshold: opponents averaging in the softer third of the league
    ranked = sorted(ppg.values())
    soft_cut = ranked[len(ranked) // 3] if ranked else league_avg  # ~bottom third

    out = {"_meta": {
        "source": "nflverse games.csv (2026 schedule + 2025 offensive PPG)",
        "source_url": GAMES_URL,
        "open_weeks": OPEN_WEEKS,
        "league_avg_ppg_2025": league_avg,
        "soft_open_cutoff_ppg": soft_cut,
        "note": "Streaming DST read: low avg_opp_ppg over Weeks 1-4 = soft opening "
                "slate (weak offenses faced). Fused with DC-change context.",
        "generated_by": "build_dst_streamers.py",
    }}

    for team, games in sorted(sched.items()):
        for g in games:
            g["opp_ppg"] = ppg.get(g["opp"], league_avg)
        opp_ppgs = [g["opp_ppg"] for g in games]
        avg_opp = round(sum(opp_ppgs) / len(opp_ppgs), 1) if opp_ppgs else league_avg
        soft = avg_opp <= soft_cut
        dinfo = defc.get(team, {})
        dc = dinfo.get("dc", "")
        dc_changed = bool(dinfo.get("changed", False))
        def_scheme = dinfo.get("scheme", "")

        # Build a concise actionable note.
        slate = ", ".join(
            f"{'vs' if g['home'] else '@'} {g['opp']}({g['opp_ppg']:.0f})" for g in games
        )
        weak_opps = [g["opp"] for g in games if g["opp_ppg"] <= soft_cut]
        if soft:
            head = f"🟢 SOFT open ({avg_opp:.0f} opp PPG"
            if weak_opps:
                head += f"; {len(weak_opps)} bottom-third offense" + ("s" if len(weak_opps) != 1 else "")
            head += ") — strong streaming DST early."
        elif avg_opp >= league_avg + 2:
            head = f"🔴 TOUGH open ({avg_opp:.0f} opp PPG) — fade/stash early."
        else:
            head = f"🟡 Average open ({avg_opp:.0f} opp PPG)."
        dc_bit = ""
        if dc_changed and dc:
            dc_bit = f" 🛡️ New DC {dc}" + (f" ({def_scheme})" if def_scheme else "") + "."
        note = f"{head}{dc_bit} Wks1-{OPEN_WEEKS}: {slate}."

        out[team] = {
            "open_games": games,
            "avg_opp_ppg": avg_opp,
            "soft_open": soft,
            "dc": dc,
            "dc_changed": dc_changed,
            "def_scheme": def_scheme,
            "streamer_note": note,
        }

    with open("dst_streamers.json", "w") as f:
        json.dump(out, f, indent=2)
    n_soft = sum(1 for t, v in out.items() if not t.startswith("_") and v["soft_open"])
    print(f"2. Wrote dst_streamers.json — {len([k for k in out if not k.startswith('_')])} teams, "
          f"{n_soft} with soft opening slates (league avg {league_avg} PPG).")


if __name__ == "__main__":
    main()
