"""
build_dynasty_board.py — OFFLINE generator for the FULL-PPR dynasty board.
Does NOT touch the Soulja board. Rescores OFFENSE at full PPR (1.0 rec, no TE
premium) from FFToday raw stats, keeps IDP/DST from the Soulja board (same IDP
scoring in both leagues), recomputes VORP/tier/rank -> board_dynasty_ppr.csv.

Run: python3 build_dynasty_board.py
"""
import re, requests, pandas as pd, numpy as np
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0"}

def cn(s):
    s = (s or "").lower().strip(); s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\b(jr|sr|iii|ii|iv|v)\b", "", s); return " ".join(s.split())

def _num(x):
    try: return float(str(x).replace(",", ""))
    except: return 0.0

# FULL-PPR dynasty scoring (verified from Sleeper 'Congress'): rec 1.0, rec_yd .1,
# rec_td 6, rush 0.1/6, pass 0.04/4/-2, NO TE premium.
def score_full_ppr(pos, cells):
    nums = [_num(x) for x in cells if re.match(r"^-?[\d,]+\.?\d*$", x.strip())]
    if len(nums) < 5:
        return None
    try:
        if pos == "QB":
            cmp_, att, pyd, ptd, inte, ratt, ryd, rtd = nums[-9:-1]
            return pyd*0.04 + ptd*4 + inte*(-2) + ratt*0.1 + ryd*0.1 + rtd*6
        if pos == "RB":
            ratt, ryd, rtd, rec, recyd, rectd = nums[-7:-1]
            return ratt*0.1 + ryd*0.1 + rtd*6 + rec*1.0 + recyd*0.1 + rectd*6
        if pos in ("WR", "TE"):
            rec, recyd, rectd = nums[-4:-1]
            return rec*1.0 + recyd*0.1 + rectd*6   # full PPR, no TE premium
    except Exception:
        return None
    return None

def fetch_ffday_fullppr():
    out = {}
    for posid, pos in {10: "QB", 20: "RB", 30: "WR", 40: "TE"}.items():
        for page in range(0, 2):
            url = f"https://www.fftoday.com/rankings/playerproj.php?PosID={posid}&cur_page={page}"
            try:
                soup = BeautifulSoup(requests.get(url, headers=UA, timeout=12).text, "html.parser")
            except Exception:
                continue
            for tr in soup.find_all("tr"):
                link = tr.find("a"); cells = [c.get_text().strip() for c in tr.find_all("td")]
                if not link or len(cells) < 6:
                    continue
                c = cn(link.get_text().strip())
                if len(c) < 4:
                    continue
                pts = score_full_ppr(pos, cells)
                if pts and pts > 0:
                    out[c] = pts
    return out

def main():
    print("Building FULL-PPR dynasty board (Soulja board untouched)...")
    ff = fetch_ffday_fullppr()
    print(f"  scored {len(ff)} offense players at full PPR.")
    b = pd.read_csv("top_150_draft_board.csv").copy()
    b["clean"] = b["clean_name"].map(cn)
    off = b["position"].isin(["QB", "RB", "WR", "TE"])
    # rescore offense proj_fpts at full PPR where we have a match; keep Soulja value
    # (scaled) as fallback so unmatched players aren't zeroed.
    matched = 0
    for i, r in b[off].iterrows():
        v = ff.get(r["clean"])
        if v:
            b.at[i, "proj_fpts"] = round(v, 1); matched += 1
    print(f"  rematched {matched}/{off.sum()} offense players to full-PPR points.")
    # recompute VORP per position at realistic superflex demand (10-team dynasty)
    demand = {"QB": 20, "RB": 25, "WR": 30, "TE": 12, "LB": 24, "DL": 18, "DB": 21, "DEF": 10}
    b["vorp"] = 0.0
    for pos, dem in demand.items():
        pm = b["position"] == pos
        pool = b[pm].sort_values("proj_fpts", ascending=False)
        if pool.empty: continue
        repl = pool.iloc[min(dem-1, len(pool)-1)]["proj_fpts"]
        b.loc[pm, "vorp"] = (b.loc[pm, "proj_fpts"] - repl).round(1)
    # simple tiers by VORP gaps within position
    b["tier"] = "Tier 4"
    for pos in b["position"].unique():
        pm = b["position"] == pos
        ps = b[pm].sort_values("vorp", ascending=False)
        n = len(ps)
        for rank, (idx, _) in enumerate(ps.iterrows(), start=1):
            t = 1 if rank <= max(1, n*0.10) else 2 if rank <= max(2, n*0.25) else 3 if rank <= max(3, n*0.5) else 4
            b.at[idx, "tier"] = f"Tier {t}"
    b = b.sort_values("vorp", ascending=False).reset_index(drop=True)
    b["rank"] = b.index + 1
    b = b.drop(columns=["clean"])
    b.to_csv("board_dynasty_ppr.csv", index=False)
    print(f"  wrote board_dynasty_ppr.csv ({len(b)} rows).")
    # show how full PPR reshuffles vs Soulja (WR/pass-catchers should rise)
    top = b[b["position"].isin(["QB","RB","WR","TE"])].head(12)
    print("\nTop 12 offense (FULL PPR):")
    for _, r in top.iterrows():
        print(f"  {r['position']} {r['player_name']:22} {r['proj_fpts']:.0f} pts  VORP {r['vorp']:.0f}")

if __name__ == "__main__":
    main()
