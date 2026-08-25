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
