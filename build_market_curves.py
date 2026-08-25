"""
build_market_curves.py — calibrate auction market_cost to the league's own history.

The generic 64*exp(-0.028*overall_rank) curve can't capture position-specific
spending shape (the Superflex QB premium, the steep TE cliff, RB depth spending).
This fits a per-position (positional-rank -> winning_bid) curve from the league's
real 2024-2025 auction results and writes market_curves.json:

  { "QB": {"a":..,"b":..,"c":..,"points":{"1":53.0,...}},   # a*exp(-b*rank)+c fit
    "RB": {...}, "WR": {...}, "TE": {...},
    "_meta": {...} }

app.py reads this and prices market_cost = fitted_curve[pos](positional_rank),
falling back to the exp curve for positions with too little data (DL/DB/DEF/IDP).
"""

import json
import numpy as np
import pandas as pd

HIST = "soulja_3yr_auction_history.csv"
OUT = "market_curves.json"
MIN_ROWS = 25  # need enough picks at a position to trust a fit


def fit_exp(ranks, prices):
    """Fit price ~ a*exp(-b*rank) + c via simple log-linear + grid on c.
    Robust for small n; returns (a, b, c)."""
    ranks = np.asarray(ranks, float)
    prices = np.asarray(prices, float)
    best = None
    # grid floor c (asymptotic min bid), fit a,b on log(price-c)
    for c in np.linspace(0.0, max(0.0, prices.min()), 8):
        y = prices - c
        mask = y > 0.5
        if mask.sum() < 3:
            continue
        # log(y) = log(a) - b*rank
        coef = np.polyfit(ranks[mask], np.log(y[mask]), 1)
        b = -coef[0]
        a = np.exp(coef[1])
        pred = a * np.exp(-b * ranks) + c
        sse = float(np.sum((pred - prices) ** 2))
        if best is None or sse < best[0]:
            best = (sse, a, b, c)
    if best is None:
        return float(prices.mean()), 0.0, 0.0
    return round(best[1], 3), round(best[2], 4), round(best[3], 2)


def main():
    d = pd.read_csv(HIST)
    d = d[d.get("draft_type", "auction") == "auction"] if "draft_type" in d else d
    # positional rank within each season (1 = most expensive at that position)
    d["pos_rank"] = d.groupby(["season", "position"])["winning_bid"].rank(
        ascending=False, method="first")

    curves = {"_meta": {
        "source": HIST,
        "seasons": sorted(int(s) for s in d["season"].unique()),
        "note": "Per-position positional-rank -> winning_bid fit (a*exp(-b*rank)+c) "
                "from league auction history. Captures SF QB premium + TE cliff.",
        "generated_by": "build_market_curves.py",
    }}

    for pos in ["QB", "RB", "WR", "TE", "LB", "DL", "DB", "DEF"]:
        sub = d[d["position"] == pos]
        if len(sub) < MIN_ROWS:
            continue
        # average bid by positional rank across seasons (the empirical curve)
        pts = sub.groupby("pos_rank")["winning_bid"].mean()
        ranks = pts.index.values.astype(float)
        prices = pts.values.astype(float)
        a, b, c = fit_exp(ranks, prices)
        curves[pos] = {
            "a": a, "b": b, "c": c,
            "n_picks": int(len(sub)),
            "points": {str(int(k)): round(float(v), 1) for k, v in pts.items()},
        }
        # show fit vs actual at a few ranks
        chk = ", ".join(
            f"r{r}: fit ${a*np.exp(-b*r)+c:.0f} vs act ${pts.get(r, float('nan')):.0f}"
            for r in [1, 3, 6, 10] if r in pts.index
        )
        print(f"  {pos:3} (n={len(sub):3}) a={a} b={b} c={c} | {chk}")

    with open(OUT, "w") as f:
        json.dump(curves, f, indent=2)
    fitted = [p for p in curves if not p.startswith("_")]
    print(f"\n✅ Wrote {OUT} — fitted curves for {fitted}.")


if __name__ == "__main__":
    main()
