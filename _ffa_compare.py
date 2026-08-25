"""_ffa_compare.py — COMPARISON ONLY. Diffs FFA robust projections vs current board. Writes nothing live."""
import pandas as pd, re

def cn(s):
    s=(s or "").lower().strip(); s=re.sub(r"[^\w\s]","",s)
    s=re.sub(r"\b(jr|sr|iii|ii|iv|v)\b","",s); return " ".join(s.split())

ffa=pd.read_csv("projections_ffa.csv")
ffa["clean"]=ffa["player_name"].map(cn)
ffa=ffa[ffa["position"].isin(["QB","RB","WR","TE"])]

b=pd.read_csv("top_150_draft_board.csv")
b["clean"]=b["clean_name"].map(cn)
b=b[b["position"].isin(["QB","RB","WR","TE"])].copy()

m=b.merge(ffa[["clean","points"]], on="clean", how="left").rename(columns={"points":"ffa_pts"})
cov=m["ffa_pts"].notna().sum()

# VORP both ways at realistic demand
demand={"QB":20,"RB":40,"WR":40,"TE":20}
def vorp(df,col):
    v={}
    for pos,dem in demand.items():
        p=df[df["position"]==pos].sort_values(col,ascending=False).reset_index(drop=True)
        p=p[p[col].notna()]
        if p.empty: continue
        repl=p.iloc[min(dem-1,len(p)-1)][col]
        for _,r in p.iterrows(): v[r["clean"]]=r[col]-repl
    return v
vc=vorp(m,"proj_fpts"); vf=vorp(m[m["ffa_pts"].notna()],"ffa_pts")
m["vorp_cur"]=m["clean"].map(vc); m["vorp_ffa"]=m["clean"].map(vf)
m["dpts"]=(m["ffa_pts"]-m["proj_fpts"]).round(0)
m["dvorp"]=(m["vorp_ffa"]-m["vorp_cur"]).round(0)

show=m[m["ffa_pts"].notna()].copy()
show=show.reindex(show["dvorp"].abs().sort_values(ascending=False).index)
print(f"Coverage: {cov}/{len(b)} board players matched to FFA robust projections.\n")
print(f"{'Player':22}{'Pos':4}{'cur':>6}{'ffa':>6}{'Δpts':>6}{'Vcur':>7}{'Vffa':>7}{'ΔVORP':>7}")
for _,r in show.head(22).iterrows():
    print(f"{str(r['player_name'])[:21]:22}{r['position']:4}{r['proj_fpts']:>6.0f}{r['ffa_pts']:>6.0f}"
          f"{r['dpts']:>+6.0f}{r['vorp_cur']:>7.0f}{r['vorp_ffa']:>7.0f}{r['dvorp']:>+7.0f}")
print(f"\nMean |Δpts|: {show['dpts'].abs().mean():.0f} | Mean |ΔVORP|: {show['dvorp'].abs().mean():.0f} | corr(cur,ffa pts): {show['proj_fpts'].corr(show['ffa_pts']):.3f}")
# how often does the SIGN of VORP flip or ranking materially change per position?
for pos in ["QB","RB","WR","TE"]:
    p=show[show["position"]==pos]
    if len(p)<3: continue
    rc=p.sort_values("proj_fpts",ascending=False)["clean"].tolist()
    rf=p.sort_values("ffa_pts",ascending=False)["clean"].tolist()
    top10_same=len(set(rc[:10])&set(rf[:10]))
    print(f"  {pos}: top-10 overlap cur-vs-ffa = {top10_same}/10")
