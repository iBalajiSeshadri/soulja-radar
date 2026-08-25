"""
_vorp_compare.py — COMPARISON ONLY. Does not touch the live board.

Pulls FFToday raw stat projections (a 2nd independent source), scores them with
the LEAGUE's own SCORING_WEIGHTS, blends 50/50 with the current board's proj_fpts,
recomputes VORP, and prints a side-by-side vs the current board so we can decide
whether the blend is worth adopting BEFORE changing anything.
"""
import re
import requests
import pandas as pd
from bs4 import BeautifulSoup
from config import SCORING_WEIGHTS as W

UA = {"User-Agent": "Mozilla/5.0"}

def cn(s):
    s = (s or "").lower().strip(); s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\b(jr|sr|iii|ii|iv|v)\b", "", s); return " ".join(s.split())

def _num(x):
    try: return float(str(x).replace(",", ""))
    except: return 0.0

def fetch_fftoday_stats():
    """Return {clean_name: fftoday_fantasy_points_scored_by_OUR_rules} for QB/RB/WR/TE."""
    # PosID: QB=10 RB=20 WR=30 TE=40. Columns differ per position.
    out = {}
    cfgs = {
        10: "QB", 20: "RB", 30: "WR", 40: "TE",
    }
    for posid, pos in cfgs.items():
        for page in range(0, 2):
            url = f"https://www.fftoday.com/rankings/playerproj.php?PosID={posid}&cur_page={page}"
            try:
                soup = BeautifulSoup(requests.get(url, headers=UA, timeout=12).text, "html.parser")
            except Exception:
                continue
            for tr in soup.find_all("tr"):
                link = tr.find("a")
                cells = [c.get_text().strip() for c in tr.find_all("td")]
                if not link or len(cells) < 6:
                    continue
                name = link.get_text().strip()
                c = cn(name)
                if len(c) < 4:
                    continue
                nums = [_num(x) for x in cells if re.match(r"^[\d,]+\.?\d*$", x.strip())]
                # score by OUR rules using the position's stat layout
                pts = _score_row(pos, cells)
                if pts > 0:
                    out[c] = pts
    return out

def _score_row(pos, cells):
    # extract trailing numeric columns (stats) — layout per FFToday position table
    nums = [_num(x) for x in cells if re.match(r"^-?[\d,]+\.?\d*$", x.strip())]
    if len(nums) < 5:
        return 0.0
    try:
        if pos == "QB":
            # ... Cmp Att PassYds PassTD INT RushAtt RushYds RushTD FPts
            cmp_, att, pyd, ptd, inte, ratt, ryd, rtd = nums[-9:-1]
            inc = max(0, att - cmp_)
            return (pyd*W['pass_yd'] + ptd*W['pass_td'] + inte*W['pass_int'] + inc*W['pass_inc']
                    + ratt*W['rush_att'] + ryd*W['rush_yd'] + rtd*W['rush_td']
                    + (W['bonus_pass_300'] if pyd>=4000 else 0))
        if pos in ("RB",):
            # ... RushAtt RushYds RushTD Rec RecYds RecTD FPts
            ratt, ryd, rtd, rec, recyd, rectd = nums[-7:-1]
            return (ratt*W['rush_att'] + ryd*W['rush_yd'] + rtd*W['rush_td'] + rec*W['rec']
                    + recyd*W['rec_yd'] + rectd*W['rec_td'] + (W['bonus_rush_100'] if ryd>=1000 else 0))
        if pos in ("WR", "TE"):
            rec, recyd, rectd = nums[-4:-1]
            teb = (W['bonus_rec_te'] if pos == 'TE' else 0)
            return (rec*(W['rec']+teb) + recyd*W['rec_yd'] + rectd*W['rec_td']
                    + (W['bonus_rec_100'] if recyd>=1000 else 0))
    except Exception:
        return 0.0
    return 0.0

def fetch_cbs_stats():
    """CBS Sports projections — raw stats, scored by OUR rules. {clean_name: pts}."""
    out = {}
    pos_map = {"QB": "QB", "RB": "RB", "WR": "WR", "TE": "TE"}
    for pos in pos_map:
        url = f"https://www.cbssports.com/fantasy/football/stats/{pos}/2026/season/projections/nonppr/"
        try:
            soup = BeautifulSoup(requests.get(url, headers=UA, timeout=12).text, "html.parser")
        except Exception:
            continue
        for tr in soup.select("table tr"):
            cells = [c.get_text().strip() for c in tr.find_all("td")]
            if len(cells) < 8:
                continue
            # first cell holds the full name (last token block); extract "First Last"
            head = cells[0].split("\n")
            toks = [t.strip() for t in head if t.strip() and len(t.strip()) > 3 and " " in t.strip()]
            name = toks[-1] if toks else head[0]
            c = cn(name)
            if len(c) < 4:
                continue
            nums = [_num(x) for x in cells[1:] if re.match(r"^-?[\d,]+\.?\d*$", x.strip())]
            pts = _score_cbs(pos, nums)
            if pts > 0:
                out[c] = pts
    return out

def _score_cbs(pos, n):
    # column order per CBS header captured above
    try:
        if pos == "QB":
            # gp att cmp pyd yds/g ptd int rate ratt ryd avg rtd fl
            att, cmp_, pyd, _, ptd, inte = n[1], n[2], n[3], n[4], n[5], n[6]
            ratt, ryd, rtd = n[8], n[9], n[11]
            inc = max(0, att - cmp_)
            return (pyd*W['pass_yd'] + ptd*W['pass_td'] + inte*W['pass_int'] + inc*W['pass_inc']
                    + ratt*W['rush_att'] + ryd*W['rush_yd'] + rtd*W['rush_td']
                    + (W['bonus_pass_300'] if pyd>=4000 else 0))
        if pos == "RB":
            # gp ratt ryd avg rtd tgt rec recyd rectd ...
            ratt, ryd, rtd = n[1], n[2], n[4]
            rec, recyd, rectd = n[6], n[7], n[8]
            return (ratt*W['rush_att'] + ryd*W['rush_yd'] + rtd*W['rush_td'] + rec*W['rec']
                    + recyd*W['rec_yd'] + rectd*W['rec_td'] + (W['bonus_rush_100'] if ryd>=1000 else 0))
        if pos in ("WR", "TE"):
            # gp tgt rec recyd avg rectd ...
            rec, recyd, rectd = n[2], n[3], n[5]
            teb = (W['bonus_rec_te'] if pos == 'TE' else 0)
            return (rec*(W['rec']+teb) + recyd*W['rec_yd'] + rectd*W['rec_td']
                    + (W['bonus_rec_100'] if recyd>=1000 else 0))
    except Exception:
        return 0.0
    return 0.0

def main():
    print("Fetching FFToday + CBS stat projections, scoring both by OUR rules...")
    ff = fetch_fftoday_stats()
    cbs = fetch_cbs_stats()
    print(f"  FFToday scored {len(ff)} | CBS scored {len(cbs)} offense players.\n")
    b = pd.read_csv("top_150_draft_board.csv")
    off = b[b['position'].isin(['QB','RB','WR','TE'])].copy()
    off['ff_pts'] = off['clean_name'].map(ff)
    off['cbs_pts'] = off['clean_name'].map(cbs)
    def _blend(r):
        # average whichever sources exist (Sleeper always; FFToday/CBS when matched)
        vals = [r['proj_fpts']]
        if pd.notna(r['ff_pts']) and r['ff_pts'] > 0: vals.append(r['ff_pts'])
        if pd.notna(r['cbs_pts']) and r['cbs_pts'] > 0: vals.append(r['cbs_pts'])
        return round(sum(vals)/len(vals), 1)
    off['blended'] = off.apply(_blend, axis=1)
    off['n_src'] = off.apply(lambda r: 1 + (1 if r.get('ff_pts',0)>0 else 0) + (1 if r.get('cbs_pts',0)>0 else 0), axis=1)
    # recompute VORP both ways using realistic starter demand
    demand = {'QB':20, 'RB':40, 'WR':40, 'TE':20}
    def vorp(col):
        v = {}
        for pos, dem in demand.items():
            pool = off[off['position']==pos].sort_values(col, ascending=False).reset_index(drop=True)
            if pool.empty: continue
            repl = pool.iloc[min(dem-1, len(pool)-1)][col]
            for _, r in pool.iterrows():
                v[r['clean_name']] = r[col] - repl
        return v
    v_cur, v_new = vorp('proj_fpts'), vorp('blended')
    off['vorp_cur'] = off['clean_name'].map(v_cur)
    off['vorp_new'] = off['clean_name'].map(v_new)
    off['delta'] = (off['vorp_new'] - off['vorp_cur']).round(0)
    print("=== BIGGEST VORP SHIFTS (current Sleeper-only vs multi-source blend) ===")
    show = off[off['n_src'] > 1].copy()
    show = show.reindex(show['delta'].abs().sort_values(ascending=False).index)
    print(f"{'Player':22}{'Pos':4}{'slp':>6}{'ff':>6}{'cbs':>6}{'blend':>7}{'#src':>5}{'Vcur':>7}{'Vnew':>7}{'Δ':>6}")
    for _, r in show.head(24).iterrows():
        ff = f"{r['ff_pts']:.0f}" if pd.notna(r['ff_pts']) and r['ff_pts']>0 else "-"
        cb = f"{r['cbs_pts']:.0f}" if pd.notna(r['cbs_pts']) and r['cbs_pts']>0 else "-"
        print(f"{r['player_name'][:21]:22}{r['position']:4}{r['proj_fpts']:>6.0f}{ff:>6}{cb:>6}"
              f"{r['blended']:>7.0f}{r['n_src']:>5.0f}{r['vorp_cur']:>7.0f}{r['vorp_new']:>7.0f}{r['delta']:>+6.0f}")
    print(f"\nCoverage: {len(show)} players with 2+ sources. "
          f"Mean |Δ VORP|: {show['delta'].abs().mean():.1f} | Max |Δ|: {show['delta'].abs().max():.0f}")

if __name__ == "__main__":
    main()
