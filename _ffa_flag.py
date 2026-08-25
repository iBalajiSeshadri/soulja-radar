"""
_ffa_flag.py — Build a SCORING-AGNOSTIC second-opinion flag from FFA robust projections.

Problem: FFA points (base 0.4 PPR) and our board points (with TE premium, incompletion tax,
etc.) are in DIFFERENT units, so raw point deltas are misleading (every TE looks "overvalued"
just because of our TE premium). Solution: compare WITHIN-POSITION Z-SCORES. A player's z-score
(how many SD above his positional mean) is scoring-unit-independent — it captures "how good is
he RELATIVE to his position" in each source. A real disagreement = the two sources rank/space
him very differently; a scoring artifact (uniform TE premium) shifts everyone equally and
cancels out in the z-score. This isolates GENUINE projection disagreements.

Writes ffa_second_opinion.csv (clean_name -> flag + note) for the app to join. Nothing live.
"""
import pandas as pd, numpy as np, re

def cn(s):
    s=(s or "").lower().strip(); s=re.sub(r"[^\w\s]","",s)
    s=re.sub(r"\b(jr|sr|iii|ii|iv|v)\b","",s); return " ".join(s.split())

ffa=pd.read_csv("projections_ffa.csv"); ffa["clean"]=ffa["player_name"].map(cn)
ffa=ffa[ffa["position"].isin(["QB","RB","WR","TE"])].copy()
b=pd.read_csv("top_150_draft_board.csv"); b["clean"]=b["clean_name"].map(cn)

# CRITICAL: compute z-scores on the SAME shared player pool, else pool-size differs
# (board ~125 elite vs FFA 565) and squashes board z-scores — a false artifact.
# Restrict FFA to the players actually on our board, then z-score both on that identical set.
shared=set(b["clean"]) & set(ffa["clean"])
b=b[b["clean"].isin(shared)].copy()
ffa=ffa[ffa["clean"].isin(shared)].copy()

def zby_pos(df, col, posc):
    df=df.copy(); df["z"]=np.nan
    for pos in ["QB","RB","WR","TE"]:
        mask=df[posc]==pos; vals=df.loc[mask,col]
        if vals.notna().sum()>=3 and vals.std()>0:
            df.loc[mask,"z"]=(vals-vals.mean())/vals.std()
    return df

ffa=zby_pos(ffa,"points","position").rename(columns={"z":"ffa_z"})
b=zby_pos(b,"proj_fpts","position").rename(columns={"z":"board_z"})

m=b.merge(ffa[["clean","ffa_z","points"]],on="clean",how="left")
m["z_gap"]=(m["ffa_z"]-m["board_z"]).round(2)   # + = FFA higher on him relative to peers

# Flag when the two sources disagree by a meaningful z-gap (>= ~0.6 SD = real, not noise).
THR=0.6
def note(r):
    if pd.isna(r["z_gap"]): return ""
    g=r["z_gap"]
    if g>=THR:
        return f"📈 Multi-source consensus is HIGHER on {r['player_name']} than your board (relative to {r['position']} peers) — possible value / your board may be light."
    if g<=-THR:
        return f"📉 Multi-source consensus is LOWER on {r['player_name']} than your board — possible reach / your board may be rich here."
    return ""
m["ffa_flag"]=m.apply(note,axis=1)

out=m[m["ffa_flag"]!=""][["clean","player_name","position","board_z","ffa_z","z_gap","ffa_flag"]].copy()
out=out.reindex(out["z_gap"].abs().sort_values(ascending=False).index)
out.to_csv("ffa_second_opinion.csv",index=False)

print(f"Scoring-AGNOSTIC (z-score) comparison. Flagged {len(out)} genuine disagreements (|z_gap|>= {THR}).\n")
print(f"{'Player':22}{'Pos':4}{'boardZ':>7}{'ffaZ':>7}{'gap':>6}  note")
for _,r in out.head(20).iterrows():
    tag="📈higher" if r["z_gap"]>0 else "📉lower"
    print(f"{str(r['player_name'])[:21]:22}{r['position']:4}{r['board_z']:>7.2f}{r['ffa_z']:>7.2f}{r['z_gap']:>+6.2f}  {tag}")
# sanity: is Bowers still flagged after removing the scoring-unit artifact?
bw=m[m["clean"]=="brock bowers"]
if not bw.empty:
    r=bw.iloc[0]
    print(f"\nBowers check: boardZ {r['board_z']:.2f}, ffaZ {r['ffa_z']:.2f}, z_gap {r['z_gap']:+.2f} -> "
          f"{'FLAGGED' if abs(r['z_gap'])>=THR else 'NOT flagged (gap was mostly the TE-premium scoring artifact)'}")
