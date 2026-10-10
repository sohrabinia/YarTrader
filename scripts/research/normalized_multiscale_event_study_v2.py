import pandas as pd, numpy as np, json
from pathlib import Path
ROOT=Path(r"C:\Projects\YarTrader\runtime_logs\mt5_gold_history_full")
OUT=ROOT/"normalized_multiscale_event_study_20261010_v2.json"
FILES=["MN1.csv","W1.csv","D1.csv","H4.csv","H1.csv","M15.csv","M5.csv","M1.csv"]
H=24
def decluster(indices,gap):
    chosen=[]; last=-10**12
    for i in indices:
        if i-last>=gap: chosen.append(int(i)); last=int(i)
    return chosen
def summarize(events,pull=False):
    if not events: return {"events":0}
    o=[e[1] for e in events]
    if pull:
        return {"events":len(o),"continuation_first_rate":round(o.count("continuation")/len(o),4),"reversal_first_rate":round(o.count("reversal")/len(o),4),"no_barrier_rate":round(o.count("none")/len(o),4),"mean_favorable_atr":round(float(np.mean([e[2] for e in events])),3),"mean_adverse_atr":round(float(np.mean([e[3] for e in events])),3)}
    return {"events":len(o),"up_first_rate":round(o.count("up")/len(o),4),"down_first_rate":round(o.count("down")/len(o),4),"no_barrier_rate":round(o.count("none")/len(o),4),"mean_up_excursion_atr":round(float(np.mean([e[2] for e in events])),3),"mean_down_excursion_atr":round(float(np.mean([e[3] for e in events])),3)}
def evaluate(df,atr,indices,horizon,dirs=None,pull=False):
    c=df.close.to_numpy(); h=df.high.to_numpy(); l=df.low.to_numpy(); a=atr.to_numpy(); out=[]
    for i in indices:
        if i+horizon>=len(df) or not np.isfinite(a[i]) or a[i]<=0: continue
        up=np.flatnonzero(h[i+1:i+horizon+1]-c[i]>=a[i]); dn=np.flatnonzero(c[i]-l[i+1:i+horizon+1]>=a[i])
        uh=int(up[0]) if len(up) else 999999; dh=int(dn[0]) if len(dn) else 999999
        if pull:
            d=dirs[i]; cont=uh if d>0 else dh; rev=dh if d>0 else uh
            outcome="continuation" if cont<rev else ("reversal" if rev<cont else "none")
            fav=float(np.max(h[i+1:i+horizon+1]-c[i])/a[i]) if d>0 else float(np.max(c[i]-l[i+1:i+horizon+1])/a[i])
            adv=float(np.max(c[i]-l[i+1:i+horizon+1])/a[i]) if d>0 else float(np.max(h[i+1:i+horizon+1]-c[i])/a[i])
        else:
            outcome="up" if uh<dh else ("down" if dh<uh else "none")
            fav=float(np.max(h[i+1:i+horizon+1]-c[i])/a[i]); adv=float(np.max(c[i]-l[i+1:i+horizon+1])/a[i])
        out.append((i,outcome,fav,adv))
    return out
res={"meta":{"symbol":"XAUUSD","source":"MT5 history from Alpari-MT5-Demo; broker-specific","split":"chronological 70% calibration / final 30% test","horizon_bars":H,"barrier":"first touch +/- 1 ATR(14) using future highs/lows; same-bar dual touch unresolved","compression":"12-bar range / ATR, threshold fixed at 20th percentile of training period; event known at close","pullback":"causal: impulse from bars i-12 to i-4, retracement observed by close i; no future bars used to select event","costs":"not applied; event study, not trading backtest"},"timeframes":{}}
for fn in FILES:
    p=ROOT/fn
    if not p.exists(): continue
    df=pd.read_csv(p).dropna(subset=["time","open","high","low","close"]).drop_duplicates("time").sort_values("time").reset_index(drop=True)
    for c in ["time","open","high","low","close"]: df[c]=pd.to_numeric(df[c],errors="coerce")
    df=df.dropna(subset=["time","open","high","low","close"]).reset_index(drop=True)
    prev=df.close.shift(1)
    tr=pd.concat([df.high-df.low,(df.high-prev).abs(),(df.low-prev).abs()],axis=1).max(axis=1)
    atr=tr.rolling(14,min_periods=14).mean()
    n=len(df); split=int(n*.70)
    if n<100 or split<=H+40: continue
    ratio=(df.high.rolling(12).max()-df.low.rolling(12).min())/atr
    threshold=float(ratio.iloc[40:split].quantile(.20))
    candidates=np.flatnonzero((ratio.to_numpy()<=threshold)&np.isfinite(ratio.to_numpy()))
    candidates=decluster([i for i in candidates if i<n-H-1],12)
    train_ev=[i for i in candidates if i<split-H]
    test_ev=[i for i in candidates if i>=split and i<n-H-1]
    comp=evaluate(df,atr,test_ev,H)
    baseidx=decluster([i for i in range(split,n-H-1) if np.isfinite(atr.iloc[i])],12)
    base=evaluate(df,atr,baseidx,H)
    close=df.close.to_numpy(); hi=df.high.to_numpy(); lo=df.low.to_numpy(); av=atr.to_numpy()
    # Causal pullback: impulse ended four bars ago, retracement is known at current close.
    pullcand=[]; dirmap={}
    for i in range(max(split,20),n-H-1):
        j=i-4; k=i-12
        if k<0 or not np.isfinite(av[j]) or av[j]<=0 or not np.isfinite(av[i]) or av[i]<=0: continue
        disp=close[j]-close[k]; mag=abs(disp)
        if mag<1.5*av[j]: continue
        d=1 if disp>0 else -1
        retr=(close[j]-close[i])/mag if d>0 else (close[i]-close[j])/mag
        if .25<=retr<=.60 and (close[i]-close[k])*d>0:
            pullcand.append(i); dirmap[i]=d
    pullidx=decluster(pullcand,12)
    pull=evaluate(df,atr,pullidx,H,dirmap,True)
    # Benchmark: strong 8-bar directional impulse ending at signal close, with no pullback filter.
    imp=np.full(n,np.nan)
    valid=av[8:]>0
    vals=np.full(n-8,np.nan); vals[valid]=(close[8:][valid]-close[:-8][valid])/av[8:][valid]; imp[8:]=vals
    bi=decluster([i for i in range(split,n-H-1) if np.isfinite(imp[i]) and abs(imp[i])>=1.5],12)
    bdirs={i:(1 if imp[i]>0 else -1) for i in bi}
    pullbase=evaluate(df,atr,bi,H,bdirs,True)
    res["timeframes"][fn[:-4]]={"bars":n,"start_utc":pd.to_datetime(df.time.iloc[0],unit="s",utc=True).isoformat(),"end_utc":pd.to_datetime(df.time.iloc[-1],unit="s",utc=True).isoformat(),"train_bars":split,"test_bars":n-split,
      "compression":{"train_events":len(train_ev),"threshold_train_q20_range12_over_atr":round(threshold,4),"test":summarize(comp),"test_baseline":summarize(base)},
      "impulse_pullback":{"test":summarize(pull,True),"impulse_only_baseline":summarize(pullbase,True)}}
    print(fn,"bars",n,"compression",len(comp),"causal pullbacks",len(pull),flush=True)
OUT.write_text(json.dumps(res,indent=2),encoding="utf-8")
print("OUTPUT",str(OUT))
