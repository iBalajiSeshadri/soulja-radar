"""
sleeper_live.py — live-draft resolution + pick reconciliation for soulja-radar.

Pure, testable (no Streamlit). The app hands us a LEAGUE ID (what the user
actually has); we:
  1. resolve the current draft for that league,
  2. report its format (auction/snake) so the UI can auto-detect,
  3. map draft slots -> the user's named managers,
  4. reconcile the FULL /picks list into a {clean_name: pick} dict on every poll
     (burst-safe: catches multiple picks landing between polls).

Keeping this here means the poll loop is a cheap "did pick_count change?" check,
and the heavy redraw only happens on change.
"""

import requests

SLEEPER = "https://api.sleeper.app/v1"
UA = {"User-Agent": "Mozilla/5.0"}


def _get(url, timeout=5):
    r = requests.get(url, headers=UA, timeout=timeout)
    r.raise_for_status()
    return r.json()


def resolve_draft(league_or_draft_id):
    """Accept a LEAGUE id (preferred) or a DRAFT id. Return draft metadata:
    {draft_id, type ('auction'|'snake'), status, teams, budget, rounds,
     slot_to_roster_id, ok, error}.
    """
    lid = str(league_or_draft_id).strip()
    out = {"ok": False, "error": None, "draft_id": None, "type": None,
           "status": None, "teams": None, "budget": None, "rounds": None,
           "slot_to_roster_id": {}, "league_id": None}
    if not lid:
        out["error"] = "empty id"
        return out
    try:
        # try as a league id first
        drafts = None
        try:
            drafts = _get(f"{SLEEPER}/league/{lid}/drafts")
        except Exception:
            drafts = None
        draft = None
        if drafts:
            # newest draft (highest season / most recent) — usually only one
            draft = sorted(drafts, key=lambda d: str(d.get("season", "")), reverse=True)[0]
            out["league_id"] = lid
        else:
            # maybe they pasted a draft id directly
            draft = _get(f"{SLEEPER}/draft/{lid}")
            out["league_id"] = draft.get("league_id")
        st = draft.get("settings", {}) or {}
        out.update({
            "ok": True,
            "draft_id": draft.get("draft_id"),
            "type": draft.get("type"),                       # 'auction' or 'snake'
            "status": draft.get("status"),                   # pre_draft/drafting/complete
            "teams": st.get("teams"),
            "budget": st.get("budget"),
            "rounds": st.get("rounds"),
            "slot_to_roster_id": draft.get("slot_to_roster_id") or {},
        })
    except Exception as e:
        out["error"] = str(e)
    return out


def slot_manager_map(league_id):
    """Return {draft_slot(int): display_name} by joining draft slot -> roster ->
    owner -> user display_name. Best-effort; empty on failure."""
    result = {}
    try:
        drafts = _get(f"{SLEEPER}/league/{league_id}/drafts")
        draft = sorted(drafts, key=lambda d: str(d.get("season", "")), reverse=True)[0]
        s2r = draft.get("slot_to_roster_id") or {}
        rosters = _get(f"{SLEEPER}/league/{league_id}/rosters")
        roster_owner = {r["roster_id"]: r.get("owner_id") for r in rosters}
        users = _get(f"{SLEEPER}/league/{league_id}/users")
        owner_name = {u["user_id"]: (u.get("display_name")
                      or (u.get("metadata", {}) or {}).get("team_name")) for u in users}
        for slot, rid in s2r.items():
            nm = owner_name.get(roster_owner.get(rid))
            if nm:
                result[int(slot)] = nm
    except Exception:
        pass
    return result


def fetch_picks(draft_id):
    """Return the raw picks list (may be empty pre-draft)."""
    try:
        return _get(f"{SLEEPER}/draft/{draft_id}/picks")
    except Exception:
        return []


# ─────────────────────── League config (scoring + roster) ─────────────────────

def league_config(league_id):
    """Pull a league's scoring_settings + roster structure and normalize into the
    shape the engine consumes. Makes the app work for ANY Sleeper league.

    Returns {ok, scoring{...}, superflex(bool), include_idp(bool), teams, budget,
    roster_slots(int), start_slots{POS:count}, error}.
    """
    out = {"ok": False, "error": None, "scoring": {}, "superflex": False,
           "include_idp": False, "teams": 10, "budget": 200, "roster_slots": 16,
           "start_slots": {}}
    try:
        lg = _get(f"{SLEEPER}/league/{league_id}")
    except Exception as e:
        out["error"] = str(e)
        return out
    ss = lg.get("scoring_settings", {}) or {}
    # map Sleeper scoring keys -> our SCORING_WEIGHTS shape (defaults when absent)
    def g(k, d=0.0):
        v = ss.get(k)
        return float(v) if v is not None else d
    out["scoring"] = {
        "pass_yd": g("pass_yd", 0.04), "pass_td": g("pass_td", 4.0),
        "pass_int": g("pass_int", -2.0), "pass_inc": g("pass_inc", 0.0),
        "pass_sack": g("pass_sack", 0.0), "bonus_pass_300": g("bonus_pass_yd_300", 0.0),
        "rush_att": g("rush_att", 0.0), "rush_yd": g("rush_yd", 0.1),
        "rush_td": g("rush_td", 6.0), "bonus_rush_100": g("bonus_rush_yd_100", 0.0),
        "rec": g("rec", 0.0), "rec_yd": g("rec_yd", 0.1), "rec_td": g("rec_td", 6.0),
        "bonus_rec_te": g("bonus_rec_te", 0.0), "bonus_fd_te": g("bonus_fd_te", 0.0),
        "bonus_rec_100": g("bonus_rec_yd_100", 0.0),
        # IDP
        "idp_tkl_solo": g("idp_tkl_solo", 0.0), "idp_tkl_ast": g("idp_tkl_ast", 0.0),
        "idp_sack": g("idp_sack", 0.0), "idp_int": g("idp_int", 0.0),
        "idp_ff": g("idp_ff", 0.0), "idp_fr": g("idp_fr", 0.0),
        "idp_pass_def": g("idp_pass_def", 0.0), "idp_tkl_loss": g("idp_tkl_loss", 0.0),
        "idp_safety": g("idp_safety", 0.0), "idp_def_td": g("idp_def_td", 6.0),
        "def_pts": 220.0,
    }
    rp = lg.get("roster_positions", []) or []
    from collections import Counter
    rc = Counter(rp)
    out["superflex"] = ("SUPER_FLEX" in rc) or (rc.get("QB", 0) >= 2)
    out["include_idp"] = any(p in rc for p in ("DB", "LB", "DL", "IDP_FLEX", "IDP"))
    out["roster_slots"] = sum(v for k, v in rc.items() if k != "BN") + rc.get("BN", 0)
    out["start_slots"] = {k: v for k, v in rc.items() if k != "BN"}
    st = lg.get("settings", {}) or {}
    out["teams"] = st.get("num_teams", lg.get("total_rosters", 10))
    # budget lives on the draft settings
    try:
        drafts = _get(f"{SLEEPER}/league/{league_id}/drafts")
        if drafts:
            out["budget"] = (drafts[0].get("settings", {}) or {}).get("budget", 200)
    except Exception:
        pass
    out["ok"] = True
    return out


# ─────────────────── Live behavioral fit (auction AND snake) ──────────────────

def _league_chain(league_id, max_back=4):
    """Return [league_id, prev, prev...] walking previous_league_id."""
    chain, cur, seen = [], str(league_id), set()
    for _ in range(max_back + 1):
        if not cur or cur in seen:
            break
        seen.add(cur)
        try:
            lg = _get(f"{SLEEPER}/league/{cur}")
        except Exception:
            break
        chain.append(cur)
        cur = lg.get("previous_league_id")
    return chain


def fit_league_behavior(league_id, clean_name_fn, max_seasons=3):
    """Walk a league's history and fit per-manager draft behavior for whatever
    format(s) they've played. Works for ANY league (no CSV, no hardcodes).

    Returns {ok, by_handle{handle: profile}, position_depth, stud_premium,
    n_auction_seasons, n_snake_seasons, error}. Profiles carry both auction fields
    (aggression, top3_pct, pos_lean, nominates_early) and snake fields
    (snake_pos_lean_by_round, avg_reach) as available.
    """
    out = {"ok": False, "error": None, "by_handle": {}, "position_depth": {},
           "stud_premium": 1.0, "n_auction_seasons": 0, "n_snake_seasons": 0}
    try:
        chain = _league_chain(league_id, max_back=max_seasons + 1)
        # collect completed drafts across the chain (most recent first, cap seasons)
        rows = []          # each: {season, pick_no, amount, position, handle, is_auction}
        seasons_used = 0
        for lid in chain:
            if seasons_used >= max_seasons:
                break
            try:
                drafts = _get(f"{SLEEPER}/league/{lid}/drafts")
            except Exception:
                continue
            comp = [d for d in drafts if d.get("status") == "complete"]
            if not comp:
                continue
            users = {u["user_id"]: u.get("display_name") for u in _get(f"{SLEEPER}/league/{lid}/users")}
            rosters = {r["roster_id"]: r.get("owner_id") for r in _get(f"{SLEEPER}/league/{lid}/rosters")}
            for d in comp:
                is_auc = d.get("type") == "auction"
                picks = fetch_picks(d["draft_id"])
                for p in picks:
                    meta = p.get("metadata", {}) or {}
                    handle = users.get(p.get("picked_by")) or users.get(rosters.get(p.get("roster_id")))
                    if not handle:
                        continue
                    rows.append({
                        "season": d.get("season"), "pick_no": p.get("pick_no", 0),
                        "amount": int(meta.get("amount")) if meta.get("amount") else None,
                        "position": meta.get("position", ""), "handle": handle,
                        "is_auction": is_auc,
                    })
                seasons_used += 1
                if is_auc:
                    out["n_auction_seasons"] += 1
                else:
                    out["n_snake_seasons"] += 1
        if not rows:
            out["error"] = "no completed draft history"
            return out

        import statistics
        handles = set(r["handle"] for r in rows)
        # league-wide top3 mean for aggression normalization (auction only)
        auc_rows = [r for r in rows if r["is_auction"] and r["amount"] is not None]
        t3_by_h = {}
        for h in handles:
            hr = [r for r in auc_rows if r["handle"] == h]
            if not hr:
                continue
            by_season = {}
            for r in hr:
                by_season.setdefault(r["season"], []).append(r["amount"])
            tot = sum(sum(v) for v in by_season.values()) / max(1, len(by_season))
            top3 = sum(sum(sorted(v, reverse=True)[:3]) for v in by_season.values()) / max(1, len(by_season))
            t3_by_h[h] = (top3 / tot) if tot else 0.0
        mean_t3 = statistics.mean(t3_by_h.values()) if t3_by_h else 0.6
        std_t3 = (statistics.pstdev(t3_by_h.values()) if len(t3_by_h) > 1 else 0.1) or 0.1

        for h in handles:
            hr = [r for r in rows if r["handle"] == h]
            prof = {"handle": h}
            # auction fields
            ha = [r for r in hr if r["is_auction"] and r["amount"] is not None]
            if ha:
                tot = sum(r["amount"] for r in ha)
                pos_spend = {}
                for r in ha:
                    pos_spend[r["position"]] = pos_spend.get(r["position"], 0) + r["amount"]
                lean = sorted(pos_spend.items(), key=lambda kv: -kv[1])
                t3pct = t3_by_h.get(h, mean_t3)
                z = (t3pct - mean_t3) / std_t3
                prof["aggression"] = round(min(1.55, max(0.80, 1.0 + 0.22 * z)), 3)
                prof["top3_pct"] = round(t3pct, 3)
                prof["pos_lean"] = {p: round(s / max(1, tot), 3) for p, s in pos_spend.items()}
                prof["top_positions"] = [p for p, _ in lean[:2]]
                prof["max_bid"] = max(r["amount"] for r in ha)
                early = [r for r in ha if r["pick_no"] <= 40]
                if early:
                    prof["nominates_early"] = statistics.mode([r["position"] for r in early]) if early else ""
            # snake fields
            hs = [r for r in hr if not r["is_auction"]]
            if hs:
                by_round = {}
                for r in hs:
                    rnd = (r["pick_no"] - 1) // max(1, out.get("teams", 10) or 10) + 1
                    by_round.setdefault(rnd, []).append(r["position"])
                # early-round positional lean (rounds 1-4)
                early_pos = [p for r in hs if (r["pick_no"] <= 40) for p in [r["position"]]]
                if early_pos:
                    prof["snake_early_lean"] = statistics.mode(early_pos)
            if "aggression" not in prof:
                prof["aggression"] = 1.0  # neutral when no auction history
            out["by_handle"][h] = prof

        # position depth (auction) for nomination bleeding — league-specific
        if auc_rows:
            import collections
            depth = {}
            # rank within season+position by amount
            season_pos = collections.defaultdict(list)
            for r in auc_rows:
                season_pos[(r["season"], r["position"])].append(r["amount"])
            for pos in ["QB", "RB", "WR", "TE"]:
                pr = [r for r in auc_rows if r["position"] == pos]
                if not pr:
                    continue
                # depth $ = spend beyond the top-3 at that position per season
                per_season = collections.defaultdict(list)
                for r in pr:
                    per_season[r["season"]].append(r["amount"])
                depth_spend = sum(sum(sorted(v, reverse=True)[3:]) for v in per_season.values()) / max(1, len(per_season))
                depth[pos] = {"depth_spend_per_yr": round(depth_spend, 0)}
            mx = max((v["depth_spend_per_yr"] for v in depth.values()), default=1.0) or 1.0
            for pos in depth:
                depth[pos]["depth_index"] = round(depth[pos]["depth_spend_per_yr"] / mx, 3)
                # marginal price ~ avg of ranks 6-12
                pr = sorted((r["amount"] for r in auc_rows if r["position"] == pos), reverse=True)
                mid = pr[5:12] if len(pr) > 5 else pr[-3:]
                depth[pos]["marginal_price"] = round(sum(mid) / max(1, len(mid)), 1) if mid else 1.0
            out["position_depth"] = depth

        out["ok"] = True
    except Exception as e:
        out["error"] = str(e)
    return out


def reconcile_picks(raw_picks, clean_name_fn, pos_map=None, display_map=None,
                    is_auction=True):
    """Turn the full raw /picks list into an ordered dict-ready list of pick
    records. Burst-safe: we always rebuild from the complete list, so multiple
    picks landing between polls can't desync us.

    Returns (records, count) where records is a list of
    {clean_name, player_name, position, team(slot), price, pick_no} in pick order.
    """
    pos_map = pos_map or {}
    display_map = display_map or {}
    records = []
    for p in sorted(raw_picks, key=lambda x: x.get("pick_no", 0)):
        meta = p.get("metadata", {}) or {}
        nm_raw = f"{meta.get('first_name', '')} {meta.get('last_name', '')}".strip()
        cn = clean_name_fn(nm_raw)
        if not cn:
            continue
        pick_no = p.get("pick_no", 0)
        if is_auction:
            price = int(meta.get("amount") or p.get("amount") or 1)
        else:
            price = int(pick_no)          # snake: "price" slot carries pick number
        records.append({
            "clean_name": cn,
            "player_name": display_map.get(cn, nm_raw),
            "position": pos_map.get(cn, meta.get("position", "FLEX")),
            "team": p.get("draft_slot", p.get("roster_id", 1)),
            "price": price,
            "pick_no": pick_no,
        })
    return records, len(records)
