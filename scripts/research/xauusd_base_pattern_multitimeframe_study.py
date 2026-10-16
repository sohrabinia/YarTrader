import pandas as pd, numpy as np, json
from pathlib import Path

ROOT=Path(r"C:\Projects\YarTrader\runtime_logs\mt5_gold_history_full")
OUT=ROOT/"xauusd_base_pattern_multitimeframe_study_20261010.json"
FILES=["H4.csv","H1.csv","M15.csv","M5.csv","D1.csv","W1.csv","MN1.csv","M1.csv"]
MAX_FWD=12
RETEST_H=48
MIN_BARS=500

def event_outcome(c, hi, lo, atr, i, direction, horizon=MAX_FWD):
    if i+horizon >= len(c) or not np.isfinite(atr[i]) or atr[i] <= 0: return None
    up=np.flatnonzero(hi[i+1:i+horizon+1]-c[i] >= atr[i])
    dn=np.flatnonzero(c[i]-lo[i+1:i+horizon+1] >= atr[i])
    u=int(up[0]) if len(up) else 999999
    d=int(dn[0]) if len(dn) else 999999
    cont=u if direction>0 else d
    rev=d if direction>0 else u
    outcome="continuation" if cont<rev else ("reversal" if rev<cont else "unresolved")
    fav=(np.max(hi[i+1:i+horizon+1])-c[i])/atr[i] if direction>0 else (c[i]-np.min(lo[i+1:i+horizon+1]))/atr[i]
    adv=(c[i]-np.min(lo[i+1:i+horizon+1]))/atr[i] if direction>0 else (np.max(hi[i+1:i+horizon+1])-c[i])/atr[i]
    return {"outcome":outcome,"fav":float(fav),"adv":float(adv),"cont_bars":int(cont) if cont<999999 else None,"rev_bars":int(rev) if rev<999999 else None}

def summarize(events):
    n=len(events)
    if not n: return {"n":0}
    cont=sum(x["outcome"]=="continuation" for x in events)
    rev=sum(x["outcome"]=="reversal" for x in events)
    un=n-cont-rev
    return {"n":n,"continuation_first_pct":round(100*cont/n,2),"reversal_first_pct":round(100*rev/n,2),"unresolved_pct":round(100*un/n,2),
            "mean_favorable_atr":round(float(np.mean([x["fav"] for x in events])),3),
            "mean_adverse_atr":round(float(np.mean([x["adv"] for x in events])),3),
            "barrier_proxy_R":round((cont-rev)/n,4)}

def main():
    result={"meta":{
      "symbol":"XAUUSD","source":"Alpari-MT5-Demo historical OHLC CSV; broker-specific",
      "definition":"Base is 2-6 consecutive candles with total high-low range <= 1.5 ATR and mean absolute candle body <= 0.55 ATR; incoming leg is 4-bar close displacement >= 0.8 ATR; departure confirms within next 1-3 bars by closing beyond base extreme by >= 0.15 ATR and closing >= 1.0 ATR from base midpoint.",
      "types":{"RBR":"incoming up, departure up","DBD":"incoming down, departure down","DBR":"incoming down, departure up","RBD":"incoming up, departure down"},
      "outcome":"from departure confirmation close, which +/-1 ATR barrier is touched first within next 12 bars; OHLC same-bar ambiguity unresolved",
      "retest":"after confirmation, first return into base range within 48 bars; measure first +/-1 ATR barrier after retest within 12 bars, using ATR at retest",
      "anti_leakage":"base and departure are known only after departure confirmation; forward outcome starts after confirmation. Thresholds are fixed, no outcome-based tuning.",
      "limitations":"event study, not trading PnL; no spread/slippage; overlapping base candidates deduplicated by confirmation index; H4/H1 scan uses stride 3, M15/M5 stride 10 and M1 stride 20 for runtime, so some bases may be missed; no claim that zones represent institutional orders."
    },"timeframes":{}}
    if OUT.exists():
      try: result=json.loads(OUT.read_text(encoding="utf-8"))
      except Exception: pass
    for fn in FILES:
      if fn[:-4] in result["timeframes"]: continue
      p=ROOT/fn
      if not p.exists(): continue
      df=pd.read_csv(p)
      df=df.dropna(subset=["time","open","high","low","close"]).drop_duplicates("time").sort_values("time").reset_index(drop=True)
      for col in ["time","open","high","low","close"]: df[col]=pd.to_numeric(df[col],errors="coerce")
      df=df.dropna(subset=["time","open","high","low","close"]).reset_index(drop=True)
      if len(df)<MIN_BARS: continue
      o=df.open.to_numpy(float); h=df.high.to_numpy(float); l=df.low.to_numpy(float); c=df.close.to_numpy(float); t=df.time.to_numpy(np.int64)
      prev=np.r_[np.nan,c[:-1]]
      tr=np.maximum(h-l,np.maximum(np.abs(h-prev),np.abs(l-prev)))
      atr=pd.Series(tr).rolling(14,min_periods=14).mean().to_numpy()
      n=len(df)
      # For each departure confirmation index, consider candidate base lengths and confirmation delays.
      raw={}
      # Restrict to bars with enough history and future.
      last_raw_conf=-1000000000
      scan_step=20 if fn=="M1.csv" else (10 if fn in ("M5.csv","M15.csv") else (3 if fn in ("H1.csv","H4.csv") else 1))
      for conf in range(30,n-MAX_FWD-2,scan_step):
        if not np.isfinite(atr[conf]) or atr[conf]<=0: continue
        best=None
        # A confirmation can occur 1-3 bars after the base ends.
        for delay in (1,2):
          bend=conf-delay
          for L in (2,3,4):
            bs=bend-L+1
            if bs<10: continue
            base_hi=float(np.max(h[bs:bend+1])); base_lo=float(np.min(l[bs:bend+1]))
            abase=float(np.nanmedian(atr[bs:bend+1]))
            if not np.isfinite(abase) or abase<=0: continue
            if (base_hi-base_lo)>1.5*abase: continue
            if float(np.mean(np.abs(c[bs:bend+1]-o[bs:bend+1])))>0.55*abase: continue
            incoming=(c[bs-1]-c[bs-5])/atr[bs-1] if atr[bs-1]>0 and np.isfinite(atr[bs-1]) else 0
            if abs(incoming)<0.8: continue
            # departure must close outside base and create displacement from base midpoint
            mid=(base_hi+base_lo)/2
            dist=(c[conf]-mid)/abase
            if abs(dist)<1.0: continue
            if c[conf]>base_hi+0.15*abase: outdir=1
            elif c[conf]<base_lo-0.15*abase: outdir=-1
            else: continue
            # Check the exit was actually developing in the last 1-3 bars, and no prior close had already exited.
            prior=c[bend:conf]
            if outdir>0 and np.any(prior>base_hi+0.15*abase): continue
            if outdir<0 and np.any(prior<base_lo-0.15*abase): continue
            score=abs(dist) + abs(incoming)*0.01 - L*0.0001
            if best is None or score>best[0]:
              best=(score,bs,bend,base_hi,base_lo,abase,1 if incoming>0 else -1,outdir,L,delay)
        if best is not None:
          _,bs,bend,bhi,blo,abase,indir,outdir,L,delay=best
          typ=("R" if indir>0 else "D")+"B"+("R" if outdir>0 else "D")
          # Deduplicate close confirmation events to avoid counting several nearby exits as separate zones.
          if conf-last_raw_conf<3: continue
          raw[conf]={"conf":conf,"base_start":bs,"base_end":bend,"base_hi":bhi,"base_lo":blo,"base_atr":abase,
                     "incoming_dir":indir,"out_dir":outdir,"type":typ,"base_len":L,"departure_delay":delay,
                     "departure_size_atr":round(abs(c[conf]-(bhi+blo)/2)/abase,3),
                     "base_width_atr":round((bhi-blo)/abase,3)}
          last_raw_conf=conf
      events=list(raw.values())
      # Decluster events by 12 bars per type-independent, for cleaner outcome stats.
      chosen=[]; last=-10**9
      for e in events:
        if e["conf"]-last>=MAX_FWD:
          chosen.append(e); last=e["conf"]
      all_metrics=[]
      type_results={}
      for typ in ("RBR","DBD","DBR","RBD"):
        te=[e for e in chosen if e["type"]==typ]
        outcomes=[]
        for e in te:
          out=event_outcome(c,h,l,atr,e["conf"],e["out_dir"])
          if out: outcomes.append(out)
        type_results[typ]={"count":len(te),"departure":summarize(outcomes),
                           "mean_base_width_atr":round(float(np.mean([e["base_width_atr"] for e in te])),3) if te else None,
                           "mean_departure_size_atr":round(float(np.mean([e["departure_size_atr"] for e in te])),3) if te else None}
      # retests: first re-entry into the base range after confirmation, not counting immediate overlap
      retest_by_type={}
      for typ in ("RBR","DBD","DBR","RBD"):
        tre=[]
        for e in chosen:
          if e["type"]!=typ: continue
          i=e["conf"]
          end=min(n-1,i+RETEST_H)
          if i+2>=end: continue
          future_lo=l[i+1:end+1]; future_hi=h[i+1:end+1]
          # Require a new touch into zone after price is at least briefly outside it.
          outside=np.flatnonzero((future_lo>e["base_hi"]) | (future_hi<e["base_lo"]))
          if len(outside)==0: continue
          start=int(outside[0])+1
          if start>=len(future_lo): continue
          hit=np.flatnonzero((future_lo[start:]<=e["base_hi"]) & (future_hi[start:]>=e["base_lo"]))
          if len(hit)==0: continue
          ri=i+1+start+int(hit[0])
          if ri+MAX_FWD>=n or not np.isfinite(atr[ri]) or atr[ri]<=0: continue
          # Reaction direction is expected zone response: demand up, supply down.
          expdir=1 if typ in ("RBR","DBR") else -1
          ro=event_outcome(c,h,l,atr,ri,expdir)
          if ro: tre.append(ro)
        retest_by_type[typ]={"n_retests":len(tre),"reaction":summarize(tre)}
      # chronological split of detected events to show stability, not used for selecting thresholds
      split=int(n*.7)
      periods={}
      for label,subset in (("first_70pct",[e for e in chosen if e["conf"]<split]),("last_30pct",[e for e in chosen if e["conf"]>=split])):
        periods[label]={}
        for typ in ("RBR","DBD","DBR","RBD"):
          es=[e for e in subset if e["type"]==typ]
          outs=[x for x in (event_outcome(c,h,l,atr,e["conf"],e["out_dir"]) for e in es) if x]
          periods[label][typ]={"count":len(es),"departure":summarize(outs)}
      result["timeframes"][fn[:-4]]={"bars":n,"start_utc":pd.to_datetime(t[0],unit="s",utc=True).isoformat(),
        "end_utc":pd.to_datetime(t[-1],unit="s",utc=True).isoformat(),"detected_raw":len(events),"detected_declustered":len(chosen),
        "patterns":type_results,"first_retest":retest_by_type,"chronological_stability":periods}
      print(fn,"bars",n,"events",len(chosen),"types",{k:v["count"] for k,v in type_results.items()},flush=True)
      OUT.write_text(json.dumps(result,indent=2),encoding="utf-8")
    OUT.write_text(json.dumps(result,indent=2),encoding="utf-8")
    print("OUTPUT",str(OUT),flush=True)

if __name__=="__main__": main()
