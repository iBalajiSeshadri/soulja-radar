"""
build_vacated_roles.py — deterministic vacated-opportunity engine.

The most reliable tier-jumper signal isn't news prose — it's DATA: compare each
team's 2025 usage to its 2026 roster. Players who accrued targets/carries for a
team in 2025 but are NO LONGER on that team (traded/FA/retired) leave a VACATED
pool. Whoever is now the top player at that position inherits it.

Verified example: Travis Etienne had 260 carries + 52 targets for JAX in 2025 and
is now on NO -> 260 carries + 52 targets vacated from JAX -> attributed to the top
returning JAX RB (Tuten).

Sources (free, deterministic):
- Sleeper 2025 stats: per-player rush_att / rec_tgt / rec AND the team they played
  for (the stat record carries 'team' = 2025 team of record).
- Sleeper current player DB: each player's CURRENT (2026) team.
- top_150_draft_board.csv: to pick the top returning/incoming player per team+pos.

Writes vacated_roles.json:
  { "clean_name": {"team": "JAX", "position": "RB",
                   "inherits_carries": 260, "inherits_targets": 52,
                   "from": ["Travis Etienne"]}, ... }
"""

import json
import re
import requests
from collections import defaultdict

SLEEPER = "https://api.sleeper.app/v1"
SLEEPER_STATS = "https://api.sleeper.com/stats/nfl/2025?season_type=regular"
UA = {"User-Agent": "Mozilla/5.0"}
OUT = "vacated_roles.json"


def clean_name(n):
    n = (n or "").lower().strip()
    n = re.sub(r"[^\w\s]", "", n)
    n = re.sub(r"\b(jr|sr|iii|ii|iv|v)\b", "", n)
    return " ".join(n.split())


def main():
    print("1. Pulling Sleeper 2025 stats + current player DB...")
    stats = requests.get(SLEEPER_STATS, headers=UA, timeout=20).json()
    pdb = requests.get(f"{SLEEPER}/players/nfl", headers=UA, timeout=30).json()

    # aggregate each player's 2025 season volume + the team they played for
    vol = {}  # pid -> {team2025, rush_att, rec_tgt, rec, name, pos}
    for s in stats:
        pid = str(s.get("player_id"))
        st = s.get("stats", {})
        t = s.get("team")
        if not pid or not t:
            continue
        e = vol.setdefault(pid, {"team2025": t, "rush_att": 0.0, "rec_tgt": 0.0, "rec": 0.0})
        # a player's team can appear across weeks; keep the most frequent later — for
        # season-total endpoint it's one record, so just accumulate.
        e["rush_att"] += float(st.get("rush_att", 0) or 0)
        e["rec_tgt"] += float(st.get("rec_tgt", 0) or 0)
        e["rec"] += float(st.get("rec", 0) or 0)
        e["team2025"] = t

    # departed volume per (team2025, position): player who played for team in 2025
    # but is NOT on that team now.
    vacated = defaultdict(lambda: {"carries": 0.0, "targets": 0.0, "from": []})
    for pid, e in vol.items():
        p = pdb.get(pid, {})
        pos = p.get("position")
        if pos not in ("RB", "WR", "TE", "QB"):
            continue
        cur_team = p.get("team")            # 2026 team (None if FA)
        team25 = e["team2025"]
        if team25 and cur_team != team25:   # departed from team25
            if e["rush_att"] + e["rec_tgt"] < 20:   # ignore trivial volume
                continue
            key = (team25, pos)
            vacated[key]["carries"] += e["rush_att"]
            vacated[key]["targets"] += e["rec_tgt"]
            nm = f"{p.get('first_name','')} {p.get('last_name','')}".strip()
            vacated[key]["from"].append((nm, int(e["rush_att"]), int(e["rec_tgt"])))

    print(f"   {len(vacated)} team-position vacated pools found.")

    # ── WORKHORSE / TARGET SHARE (user: 'solo RB1 with low shared carries = gold')
    # For each team, compute each RB's share of team RB carries and each WR's share
    # of team WR targets in 2025. A returning player who commanded a high share is a
    # proven bell-cow (fantasy gold); a low share = committee risk.
    team_rb_car = defaultdict(float)   # team2025 -> total RB carries
    team_wr_tgt = defaultdict(float)   # team2025 -> total WR targets
    for pid, e in vol.items():
        p = pdb.get(pid, {})
        pos = p.get("position")
        if pos == "RB":
            team_rb_car[e["team2025"]] += e["rush_att"]
        elif pos == "WR":
            team_wr_tgt[e["team2025"]] += e["rec_tgt"]
    share_map = {}   # clean_name -> {workhorse_share / target_share} for RETURNING players
    for pid, e in vol.items():
        p = pdb.get(pid, {})
        pos = p.get("position"); cur = p.get("team"); t25 = e["team2025"]
        if cur != t25:   # only returning players (same team) — a proven role that carries over
            continue
        cn = clean_name(f"{p.get('first_name','')} {p.get('last_name','')}")
        if pos == "RB" and team_rb_car.get(t25, 0) > 50 and e["rush_att"] >= 100:
            share_map[cn] = {"workhorse_share": round(e["rush_att"] / team_rb_car[t25], 2),
                             "carries_2025": int(e["rush_att"])}
        elif pos == "WR" and team_wr_tgt.get(t25, 0) > 50 and e["rec_tgt"] >= 70:
            share_map[cn] = {"target_share": round(e["rec_tgt"] / team_wr_tgt[t25], 2),
                             "targets_2025": int(e["rec_tgt"])}

    # attribute each vacated pool to the top RETURNING/incoming player at that
    # team+position, using the draft board's projections (proj_fpts).
    import csv
    board = list(csv.DictReader(open("top_150_draft_board.csv")))
    def board_top(team, pos):
        cand = [r for r in board if r["team"] == team and r["position"] == pos]
        cand.sort(key=lambda r: float(r.get("proj_fpts", 0)), reverse=True)
        return cand

    out = {}
    for (team, pos), pool in vacated.items():
        cand = board_top(team, pos)
        if not cand:
            continue
        top = cand[0]   # the ascending player who inherits
        out[top["clean_name"]] = {
            "team": team, "position": pos,
            "inherits_carries": int(round(pool["carries"])),
            "inherits_targets": int(round(pool["targets"])),
            "from": [f"{n} ({c}c/{t}tgt)" for n, c, t in sorted(pool["from"], key=lambda x: -(x[1]+x[2]))[:3]],
        }

    # merge in workhorse/target share for returning players (may or may not also
    # be a vacated inheritor)
    for cn, sh in share_map.items():
        out.setdefault(cn, {}).update(sh)

    with open(OUT, "w") as f:
        json.dump({"_meta": {"source": "Sleeper 2025 stats vs 2026 rosters",
                             "note": "Deterministic vacated targets/carries attributed to the top "
                                     "returning player at each team+position; plus 2025 workhorse "
                                     "carry-share (RB) and target-share (WR) for returning players."},
                   "players": out}, f, indent=2)
    print(f"2. Wrote {OUT} — {len(out)} players inheriting vacated volume.")
    # show the biggest inheritors
    top_inheritors = sorted(out.items(), key=lambda kv: -(kv[1].get("inherits_carries", 0) + kv[1].get("inherits_targets", 0)))[:10]
    print("   Biggest vacated-role inheritors:")
    for cn, v in top_inheritors:
        nm = next((r["player_name"] for r in board if r["clean_name"] == cn), cn)
        print(f"     {nm:22} {v.get('position','?')} {v.get('team','?')}: "
              f"+{v.get('inherits_carries',0)}c/+{v.get('inherits_targets',0)}tgt "
              f"from {v['from'][0] if v.get('from') else '?'}")


if __name__ == "__main__":
    main()
