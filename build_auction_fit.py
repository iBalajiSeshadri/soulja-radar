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

    # ── per-position DEPTH score (from full Sleeper history if available) ──────
    # Depth = how much a position rewards bidding on non-elite players. Deep
    # positions (lots drafted, lots of $ on rank-4+) are the best NOMINATION bait:
    # rivals overspend on replaceable talent. Scarce positions (QB/TE) score low
    # and are protected from nomination. Prefer the richer sleeper_history file.
    import os as _os
    depth_src = "sleeper_history_3yr.csv" if _os.path.exists("sleeper_history_3yr.csv") else HIST
    dd = pd.read_csv(depth_src)
    amt_col = "amount" if "amount" in dd else "winning_bid"
    dd = dd.dropna(subset=[amt_col])
    dseasons = max(1, dd["season"].nunique())
    dd["pr"] = dd.groupby(["season", "position"])[amt_col].rank(ascending=False, method="first")
    position_depth = {}
    for pos in ["QB", "RB", "WR", "TE"]:
        sub = dd[dd["position"] == pos]
        if len(sub) == 0:
            continue
        n_per = len(sub) / dseasons                       # players drafted per yr
        depth_spend = sub[sub["pr"] > 3][amt_col].sum() / dseasons   # $ on rank-4+
        # marginal-starter cheapness: avg price of rank 6-12 (the "you can wait" band)
        marg = sub[(sub["pr"] >= 6) & (sub["pr"] <= 12)][amt_col].mean()
        position_depth[pos] = {
            "n_per_yr": round(float(n_per), 1),
            "depth_spend_per_yr": round(float(depth_spend), 0),
            "marginal_price": round(float(marg) if not np.isnan(marg) else 0.0, 1),
        }
    # normalize a 0..1 depth index off depth_spend (WR/RB high, QB/TE low)
    _ds = {p: v["depth_spend_per_yr"] for p, v in position_depth.items()}
    _mx = max(_ds.values()) if _ds else 1.0
    for p in position_depth:
        position_depth[p]["depth_index"] = round(_ds[p] / max(1.0, _mx), 3)
    out["position_depth"] = position_depth

    with open(OUT, "w") as f:
        json.dump(out, f, indent=2)

    print(f"League mean top-3 spend: {mean_t3:.0%} | top-stud premium vs engine-fair: {stud_premium}x")
    print("Premium by overall rank (actual sold / engine fair):",
          {k: prem_points[k] for k in sorted(prem_points)[:8]})
    print("Per-manager aggression (from real 3yr behavior):")
    for m, v in sorted(by_manager.items(), key=lambda kv: -kv[1]["aggression"]):
        print(f"  {m:18} aggr={v['aggression']:.2f}  (top3 {v['top3_pct']:.0%}, max ${v['max_bid']})")
    print(f"\n✅ Wrote {OUT}.")
    if "position_depth" in out:
        print("Position depth (bleed targets high, protect low):")
        for p, v in sorted(out["position_depth"].items(), key=lambda kv: -kv[1]["depth_index"]):
            print(f"  {p}: depth_index={v['depth_index']:.2f} "
                  f"(${v['depth_spend_per_yr']:.0f}/yr on rank-4+, marginal ${v['marginal_price']:.0f})")


if __name__ == "__main__":
    main()
