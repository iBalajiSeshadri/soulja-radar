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


# ─────────────────────── Depth-based nomination (preferred) ───────────────────

def nomination_by_depth(candidates, rivals, position_depth, my_interest_names=None,
                        n_top=6, min_depth=0.9, protect_top_n=3):
    """Rank nominations by POSITIONAL DEPTH x rival demand — bleed rivals on
    replaceable talent at deep positions (WR/RB), never on scarce ones (TE/QB top).

    candidates: list {clean_name, player_name, position, fair_value, market_cost}
    rivals: list {cap_left, needs:set, aggression}
    position_depth: {pos: {"depth_index": 0..1, "marginal_price": $}}  (from history)
    my_interest_names: optional set to still avoid nominating your explicit targets.
    protect_top_n: skip the top-N priced players at each position (the studs YOU
        might want) — nominate genuine mid-tier depth instead, not elites.

    A player is a good bleed if his position is DEEP (cheap replacement) yet the
    market still pays a real price AND rivals still need the slot — wasted cap for
    them. Scarce positions (low depth_index) and each position's elites are
    excluded so we never nominate a player you'd plausibly want.
    """
    my_interest_names = my_interest_names or set()
    # rank within each deep position to identify (and skip) the elites
    by_pos = {}
    for c in candidates:
        by_pos.setdefault(c.get("position", ""), []).append(c)
    protected = set()
    for pos, lst in by_pos.items():
        lst_sorted = sorted(lst, key=lambda x: float(x.get("fair_value", 0)), reverse=True)
        for c in lst_sorted[:protect_top_n]:
            protected.add(c["clean_name"])

    out = []
    for c in candidates:
        pos = c.get("position", "")
        pd_info = position_depth.get(pos, {})
        depth = float(pd_info.get("depth_index", 0.0))
        if depth < min_depth:
            continue  # scarce position — protect, don't nominate
        if c["clean_name"] in my_interest_names or c["clean_name"] in protected:
            continue  # honor explicit targets + skip each position's elites
        fv = float(c.get("fair_value", 1))
        interested = 0
        top_price = 0.0
        for r in rivals:
            cap = float(r.get("cap_left", 0))
            if cap < fv * 0.5:
                continue
            need = 1.0 if pos in r.get("needs", set()) else 0.4
            aggr = float(r.get("aggression", 1.0))
            wtp = min(cap, fv * aggr * (0.75 + 0.35 * need))
            top_price = max(top_price, wtp)
            if pos in r.get("needs", set()) and wtp >= fv * 0.7:
                interested += 1
        if interested == 0 and top_price < fv:
            continue
        # waste = what a rival pays above the cheap marginal replacement at this pos
        marginal = float(pd_info.get("marginal_price", 1.0))
        waste = max(0.0, top_price - marginal)
        # prefer REPLACEABLE players: high waste relative to their own value means
        # the rival is overpaying for depth they could get cheap. Studs (fv high,
        # low waste ratio) score lower so we bleed on mid-tier, not your studs.
        waste_ratio = waste / max(1.0, fv)
        # BLEED score — reward DEPTH x WASTE (rivals overpaying for replaceable
        # talent at a deep position), NOT raw price. Previously top_price dominated,
        # which biased the card toward the most EXPENSIVE names (studs/RBs) even when
        # rivals weren't actually overpaying. The point of a bleed nomination is to
        # make a rival waste cap on depth they could get cheap — that peaks at the
        # DEEPEST positions (WR 1.0, RB ~0.99 per league history), which is exactly
        # where 3yr data says to drain them. So: wasted cap is the primary driver,
        # scaled by how deep the position is; price is a mild tiebreaker only.
        score = (depth ** 2) * (waste + 0.15 * top_price) * (1 + 0.4 * interested)
        out.append({
            "clean_name": c["clean_name"],
            "player_name": c.get("player_name", c["clean_name"]),
            "position": pos,
            "fair_value": int(fv),
            "expected_price": int(round(top_price)),
            "wasted_cap": int(round(waste)),
            "interested_rivals": interested,
            "depth_index": round(depth, 2),
            "score": round(score, 1),
            "why": (f"deep {pos} (replacement ~${int(marginal)}); {interested} rival(s) "
                    f"still need {pos} and will pay ~${int(top_price)} — ~${int(waste)} wasted cap"),
        })
    out.sort(key=lambda d: d["score"], reverse=True)
    # DIVERSIFY the top-N: nominating the same position 4x in a row is a weak play
    # (it telegraphs your disinterest and floods one market). Since the league's
    # deepest positions (WR 1.0 / RB 0.99) are near-tied bleed targets, interleave
    # them so the card surfaces the best WR bleed alongside the best RB bleed rather
    # than letting a marginal price edge crowd one position out. Greedy round-robin
    # by position, best-scoring first within each.
    if len(out) > n_top:
        from collections import defaultdict as _dd
        _by = _dd(list)
        for d in out:
            _by[d["position"]].append(d)
        _pos_order = sorted(_by.keys(), key=lambda p: _by[p][0]["score"], reverse=True)
        _diverse, _i = [], 0
        while len(_diverse) < n_top and any(_by.values()):
            p = _pos_order[_i % len(_pos_order)]
            if _by[p]:
                _diverse.append(_by[p].pop(0))
            _i += 1
            if _i > 200:
                break
        return _diverse[:n_top]
    return out[:n_top]
