import pandas as pd, numpy as np, json
from pathlib import Path
ROOT=Path(r"C:\Projects\YarTrader\runtime_logs\mt5_gold_history_full")
OUT=ROOT/"trend_pullback_volatility_regime_study_20261010.json"
FILES=["MN1.csv","W1.csv","D1.csv","H4.csv","H1.csv","M15.csv","M5.csv","M1.csv"]
H=24
def decluster(ids,gap):
    out=[]; last=-10**12
    for i in ids:
        if int(i)-last>=gap: out.append(int(i)); last=int(i)
    return out
def event_metrics(df, atr, ids, dirs):
    c=df.close.to_numpy(); hi=df.high.to_numpy(); lo=df.low.to_numpy(); av=atr.to_numpy(); out=[]
    for i in ids:
        if i+H>=len(df) or not np.isfinite(av[i]) or av[i]<=0: continue
        fh=hi[i+1:i+H+1]; fl=lo[i+1:i+H+1]
        up=np.flatnonzero(fh-c[i]>=av[i]); dn=np.flatnonzero(c[i]-fl>=av[i])
        uh=int(up[0]) if len(up) else 999999; dh=int(dn[0]) if len(dn) else 999999
        d=dirs[i]; cont=uh if d>0 else dh; rev=dh if d>0 else uh
        outcome="continuation" if cont<rev else ("reversal" if rev<cont else "none")
        fav=float(np.max(fh-c[i])/av[i]) if d>0 else float(np.max(c[i]-fl)/av[i])
        adv=float(np.max(c[i]-fl)/av[i]) if d>0 else float(np.max(fh-c[i])/av[i])
        out.append((outcome,fav,adv))
    if not out: return {"events":0}
    n=len(out); cont=sum(e[0]=="continuation" for e in out); rev=sum(e[0]=="reversal" for e in out); none=n-cont-rev
    return {"events":n,"continuation_first_rate":round(cont/n,4),"reversal_first_rate":round(rev/n,4),"no_barrier_rate":round(none/n,4),"mean_favorable_atr":round(float(np.mean([e[1] for e in out])),3),"mean_adverse_atr":round(float(np.mean([e[2] for e in out])),3),"barrier_proxy_R":round((cont-rev)/n,4)}
res={"meta":{"symbol":"XAUUSD","source":"Alpari-MT5-Demo CSV history; broker-specific","split":"chronological 70% calibration / final 30% evaluation","event":"impulse from close[i-12] to close[i-4] >=1.5 ATR at i-4; pullback 25-60% of impulse observed by close[i], trend direction still intact","regimes":"ATR(14)/rolling median ATR(100), low/mid/high terciles determined from training data only","outcome":"first touch +/-1 ATR from signal close within next 24 bars; same-bar dual touch unresolved","limitations":"12-bar declustering, overlapping future horizons remain possible; no costs, not a trading backtest"},"timeframes":{}}
for fn in FILES:
 p=ROOT/fn
 if not p.exists(): continue
 df=pd.read_csv(p).dropna(subset=["time","open","high","low","close"]).drop_duplicates("time").sort_values("time").reset_index(drop=True)
 for col in ["time","open","high","low","close"]: df[col]=pd.to_numeric(df[col],errors="coerce")
 df=df.dropna(subset=["time","open","high","low","close"]).reset_index(drop=True)
 n=len(df); split=int(n*.70)
 if n<200 or split<=H+150: continue
 prev=df.close.shift(1)
 tr=pd.concat([df.high-df.low,(df.high-prev).abs(),(df.low-prev).abs()],axis=1).max(axis=1)
 atr=tr.rolling(14,min_periods=14).mean()
 av=atr.to_numpy(); c=df.close.to_numpy()
 volratio=(atr/atr.rolling(100,min_periods=50).median()).to_numpy()
 train_v=volratio[150:split]; train_v=train_v[np.isfinite(train_v)]
 vq1=float(np.quantile(train_v,1/3)); vq2=float(np.quantile(train_v,2/3))
 # Vectorized causal event selection.
 ids=np.arange(max(split,150),n-H-1)
 j=ids-4; k=ids-12
 disp=c[j]-c[k]; mag=np.abs(disp); a_j=av[j]
 valid=np.isfinite(a_j)&(a_j>0)&np.isfinite(av[ids])&(av[ids]>0)&np.isfinite(volratio[ids])
 strong=valid&(mag>=1.5*a_j)
 direction=np.sign(disp)
 retr=np.full(len(ids),np.nan)
 retr[direction>0]=(c[j[direction>0]]-c[ids[direction>0]])/mag[direction>0]
 retr[direction<0]=(c[ids[direction<0]]-c[j[direction<0]])/mag[direction<0]
 intact=((c[ids]-c[k])*direction)>0
 pullmask=strong&(retr>=.25)&(retr<=.60)&intact
 pullids=decluster(ids[pullmask],12)
 baseids=decluster(ids[strong],12)
 def reg_name(i):
  v=volratio[i]
  return "low" if v<=vq1 else ("high" if v>=vq2 else "mid")
 regs={i:reg_name(i) for i in pullids}
 dirs={i:int(np.sign(c[i-4]-c[i-12])) for i in pullids}
 bdirs={i:int(np.sign(c[i-4]-c[i-12])) for i in baseids}
 tf={}
 for reg in ["all","low","mid","high"]:
  pids=[i for i in pullids if reg=="all" or regs[i]==reg]
  bids=[i for i in baseids if reg=="all" or reg_name(i)==reg]
  tf[reg]={"pullback":event_metrics(df,atr,pids,dirs),"impulse_baseline":event_metrics(df,atr,bids,bdirs)}
 train_ids=np.arange(150,split)
 trmag=np.abs(c[train_ids-4]-c[train_ids-12])/av[train_ids-4]
 trmag=trmag[np.isfinite(trmag)&np.isfinite(av[train_ids-4])&(av[train_ids-4]>0)]
 q75=float(np.quantile(trmag,.75))
 strongpull=[i for i in pullids if abs(c[i-4]-c[i-12])/av[i-4]>=q75]
 tf["stronger_impulse_q75"]={"train_impulse_atr_threshold":round(q75,3),"pullback":event_metrics(df,atr,strongpull,dirs)}
 res["timeframes"][fn[:-4]]={"bars":n,"start_utc":pd.to_datetime(df.time.iloc[0],unit="s",utc=True).isoformat(),"end_utc":pd.to_datetime(df.time.iloc[-1],unit="s",utc=True).isoformat(),"train_bars":split,"test_bars":n-split,"volatility_ratio_thresholds_train":{"low_max":round(vq1,4),"high_min":round(vq2,4)},"events_total":len(pullids),"results":tf}
 print(fn,"pullback events",len(pullids),"all",tf["all"]["pullback"],"low",tf["low"]["pullback"],"mid",tf["mid"]["pullback"],"high",tf["high"]["pullback"],flush=True)
OUT.write_text(json.dumps(res,indent=2),encoding="utf-8")
print("OUTPUT",str(OUT))
