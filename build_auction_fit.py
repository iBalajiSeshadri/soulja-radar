"""
build_auction_fit.py — fit real auction behavior from the league's own history.

Replaces the hardcoded archetype-class aggression guesses with per-MANAGER
constants derived from soulja_3yr_auction_history.csv:

  - aggression: how top-heavy a manager spends. Anchored to their top-3 spend %
    (share of their $200 cap on their 3 priciest players) normalized around the
    league mean, mapped to a ~0.80–1.55 multiplier. Kopite (78% top-3) => high;
    Siddu (45%) => low.
  - stud_premium: how much the WINNING bid on a stud exceeded a naive VORP-fair
    price, league-wide — used to sanity-anchor the Monte-Carlo price model.

Writes auction_fit.json:
  { "_meta": {...},
    "by_manager": { "kopite": {"aggression":1.55,"top3_pct":0.78,"max_bid":62}, ... },
    "by_handle":  { same keyed by lowercase handle for app lookup },
    "stud_premium": 1.18 }
"""

import json
import pandas as pd
import numpy as np

HIST = "soulja_3yr_auction_history.csv"
OUT = "auction_fit.json"


def main():
    d = pd.read_csv(HIST)
    if "draft_type" in d:
        d = d[d["draft_type"] == "auction"]
    n_seasons = d["season"].nunique()

    # ── per-manager aggression from top-3 spend share ─────────────────────────
    stats = {}
    for m in d["manager"].unique():
        md = d[d["manager"] == m]
        seasons = max(1, md["season"].nunique())
        tot = md["winning_bid"].sum() / seasons
        top3 = md.sort_values("winning_bid", ascending=False).groupby("season").head(3)["winning_bid"].sum() / seasons
        top3_pct = round(float(top3) / max(1.0, float(tot)), 3)
        stats[m] = {"top3_pct": top3_pct, "max_bid": int(md["winning_bid"].max()),
                    "avg_bid": round(float(md["winning_bid"].mean()), 1)}

    mean_t3 = float(np.mean([s["top3_pct"] for s in stats.values()]))
    std_t3 = float(np.std([s["top3_pct"] for s in stats.values()])) or 0.01
    # map z-score of top3% to a multiplier centered on 1.0 (±~0.35 band)
    by_manager = {}
    for m, s in stats.items():
        z = (s["top3_pct"] - mean_t3) / std_t3
        aggr = round(float(np.clip(1.0 + 0.22 * z, 0.80, 1.55)), 3)
        by_manager[m.lower()] = {"aggression": aggr, "top3_pct": s["top3_pct"],
                                 "max_bid": s["max_bid"], "avg_bid": s["avg_bid"]}

    # ── league-wide stud price premium vs the ENGINE's VORP-fair value ────────
    # The VORP-share fair_value flattens the very top, but the market pays a
    # premium for elite players. Measure actual winning bid / engine par-fair at
    # top overall ranks, and fit a simple premium that decays with rank.
    b = pd.read_csv("top_150_draft_board.csv")
    o = b[b["position"].isin(["QB", "RB", "WR", "TE"])].copy()
    _v = o["vorp"].clip(lower=0)
    o["fair"] = (_v / _v.sum()) * (180 * 10 * 0.75)
    o = o.sort_values("fair", ascending=False).reset_index(drop=True)
    off = d[d["position"].isin(["QB", "RB", "WR", "TE"])].copy()
    off["ov_rank"] = off.groupby("season")["winning_bid"].rank(ascending=False, method="first")
    prem_points = {}
    for r in range(1, 21):
        act = off[off["ov_rank"] == r]["winning_bid"].mean()
        if r - 1 < len(o) and o.iloc[r - 1]["fair"] > 0 and not np.isnan(act):
            prem_points[r] = round(float(act) / float(o.iloc[r - 1]["fair"]), 3)
    # smooth into a decaying premium: top-rank premium fading to ~1.0 by rank ~25
    top_prem = round(float(np.mean([prem_points.get(r, 1.0) for r in (1, 2, 3)])), 3)
    stud_premium = top_prem

    out = {
        "_meta": {
            "source": HIST,
            "seasons": sorted(int(s) for s in d["season"].unique()),
            "note": "Per-manager aggression from top-3 spend share (normalized); "
                    "stud_premium = actual top-12 stud price vs par expectation.",
            "generated_by": "build_auction_fit.py",
            "league_mean_top3_pct": round(mean_t3, 3),
        },
        "by_manager": by_manager,
        "stud_premium": stud_premium,
        "premium_by_rank": {str(k): v for k, v in prem_points.items()},
    }
    with open(OUT, "w") as f:
        json.dump(out, f, indent=2)

    print(f"League mean top-3 spend: {mean_t3:.0%} | top-stud premium vs engine-fair: {stud_premium}x")
    print("Premium by overall rank (actual sold / engine fair):",
          {k: prem_points[k] for k in sorted(prem_points)[:8]})
    print("Per-manager aggression (from real 3yr behavior):")
    for m, v in sorted(by_manager.items(), key=lambda kv: -kv[1]["aggression"]):
        print(f"  {m:18} aggr={v['aggression']:.2f}  (top3 {v['top3_pct']:.0%}, max ${v['max_bid']})")
    print(f"\n✅ Wrote {OUT}.")


if __name__ == "__main__":
    main()
