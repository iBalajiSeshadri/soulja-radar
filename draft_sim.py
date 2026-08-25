"""
draft_sim.py — advanced draft math for soulja-radar (auction + snake).

Pure, testable functions (no Streamlit) so the modeling can be unit-tested
headless. Two engines:

1. Monte-Carlo survival / price:
   - snake: P(player is gone before my next pick) by simulating the intervening
     picks as draws weighted by ADP proximity + positional demand.
   - auction: expected winning-price distribution for a player given remaining
     rival budgets and their positional need (median / 80th percentile).

2. Game-theory nomination optimizer:
   - score each nominatable player by expected rival cap-drain (their collective
     willingness-to-pay) MINUS my own interest, so I nominate players that bleed
     opponents on guys I don't want.

All functions take plain dicts / lists so they're trivial to test and to call
from app.py with columns pulled out of the board DataFrame.
"""

import random
import statistics
from collections import defaultdict


# ─────────────────────────── SNAKE: Monte-Carlo survival ──────────────────────

def mc_snake_survival(candidates, picks_until_next, n_sims=400, adp_sigma=6.0, seed=None):
    """Estimate P(gone before my next pick) for each candidate.

    candidates: list of dicts {clean_name, market_adp, position}
    picks_until_next: number of picks between now and my next selection.
    Model: each intervening pick selects the available player whose ADP is closest
    to the current overall pick number, with Gaussian noise on ADP (drafts are
    noisy). Repeat n_sims times; survival = fraction of sims the player was NOT
    taken in the window.

    Returns {clean_name: prob_gone (0..1)}.
    """
    if picks_until_next <= 0 or not candidates:
        return {c["clean_name"]: 0.0 for c in candidates}
    rng = random.Random(seed)
    gone_counts = defaultdict(int)
    # current overall pick = min ADP baseline; we simulate picks_until_next selections
    base_pick = min((c.get("market_adp", 999) for c in candidates), default=1)
    for _ in range(n_sims):
        # assign each candidate a noisy "draft position" this sim
        noisy = []
        for c in candidates:
            adp = float(c.get("market_adp", 999))
            noisy.append((c["clean_name"], adp + rng.gauss(0, adp_sigma)))
        noisy.sort(key=lambda kv: kv[1])
        # the players with the lowest noisy ADP get taken in the window
        taken = set(name for name, _ in noisy[:picks_until_next])
        for c in candidates:
            if c["clean_name"] in taken:
                gone_counts[c["clean_name"]] += 1
    return {c["clean_name"]: round(gone_counts[c["clean_name"]] / n_sims, 3) for c in candidates}


# ─────────────────────────── AUCTION: Monte-Carlo price ───────────────────────

def mc_auction_price(player, rivals, my_max_bid, n_sims=400, seed=None):
    """Estimate the winning-price distribution for a player in an auction.

    player: {fair_value, position}
    rivals: list of dicts {cap_left, need_at_pos (0..1 how much they need this pos),
            aggression (0.8..1.6 archetype spend tendency)}
    Model: each rival's willingness-to-pay ~ fair_value * aggression * (0.6 + 0.8*need),
    with noise, capped by their cap_left. Winning price = 2nd-highest willingness + 1
    (auction closes just above the runner-up), capped by top bidder's cap.

    Returns {median, p80, p20, mean} of simulated winning prices.
    """
    fv = float(player.get("fair_value", 1))
    rng = random.Random(seed)
    prices = []
    for _ in range(n_sims):
        wtps = []
        for r in rivals:
            cap = float(r.get("cap_left", 0))
            if cap < 1:
                continue
            need = float(r.get("need_at_pos", 0.5))
            aggr = float(r.get("aggression", 1.0))
            # willingness centered near fair value; needy+aggressive rivals stretch a
            # bit past it, but bounded so a single stud can't imply an absurd price.
            wtp = fv * aggr * (0.75 + 0.35 * need) * rng.gauss(1.0, 0.12)
            wtp = min(cap, max(1.0, wtp))
            wtps.append(wtp)
        wtps.append(min(my_max_bid, fv * rng.gauss(1.0, 0.1)))
        wtps.sort(reverse=True)
        if len(wtps) >= 2:
            # price closes partway between runner-up and top bidder (not a full +1 jump)
            price = wtps[1] + 0.4 * (wtps[0] - wtps[1]) + 1.0
            price = min(price, wtps[0])
        else:
            price = max(1.0, wtps[0] if wtps else 1.0)
        prices.append(price)
    prices.sort()
    n = len(prices)
    def pct(p):
        return round(prices[min(n - 1, int(p * n))], 1)
    return {
        "median": round(statistics.median(prices), 1),
        "p20": pct(0.20),
        "p80": pct(0.80),
        "mean": round(statistics.mean(prices), 1),
    }


# ─────────────────────────── Game-theory nomination ───────────────────────────

def nomination_scores(candidates, rivals, my_interest_names, n_top=6):
    """Rank nominatable players by expected rival cap-drain minus my own interest.

    candidates: list {clean_name, player_name, position, fair_value, market_cost}
    rivals: list {cap_left, needs: set(positions), aggression}
    my_interest_names: set of clean_names I actually want (avoid nominating these).

    drain = expected dollars this nomination pulls out of RIVAL wallets =
            sum over rivals of their willingness-to-pay (fair_value * aggression *
            need_boost), but only counts as "good drain" for players I DON'T want.
    score = drain * (0.15 if I want him else 1.0)   # heavily penalize self-interest
    Returns top n_top list of {clean_name, player_name, position, drain, score, why}.
    """
    out = []
    for c in candidates:
        fv = float(c.get("fair_value", 1))
        pos = c.get("position", "")
        drain = 0.0
        interested_rivals = 0
        _wtps = []
        for r in rivals:
            cap = float(r.get("cap_left", 0))
            if cap < fv * 0.5:
                continue  # can't really contest
            need = 1.0 if pos in r.get("needs", set()) else 0.4
            aggr = float(r.get("aggression", 1.0))
            wtp = min(cap, fv * aggr * (0.75 + 0.35 * need))
            _wtps.append(wtp)
            if wtp >= fv * 0.8:
                interested_rivals += 1
        # "drain" = what the WINNING rival actually pays (the price this nomination
        # pulls out of one wallet), ~ the top rival WTP — not the sum of all WTPs.
        if _wtps:
            _wtps.sort(reverse=True)
            drain = _wtps[0]
        i_want = c["clean_name"] in my_interest_names
        # good bleed = high winner-pays (drain) AND multiple rivals contesting it;
        # heavily penalize nominating a player I actually want.
        score = drain * (1 + 0.25 * interested_rivals) * (0.15 if i_want else 1.0)
        # a good bleed target: rivals want him, I don't, price is high
        why = (f"{interested_rivals} rival(s) likely bid; winner pays ~${int(drain)} "
               f"— cap pulled from a rival wallet")
        if i_want:
            why = "AVOID nominating — this is one of YOUR targets."
        out.append({
            "clean_name": c["clean_name"],
            "player_name": c.get("player_name", c["clean_name"]),
            "position": pos,
            "fair_value": int(fv),
            "drain": int(drain),
            "interested_rivals": interested_rivals,
            "score": round(score, 1),
            "i_want": i_want,
            "why": why,
        })
    out.sort(key=lambda d: d["score"], reverse=True)
    return out[:n_top]
