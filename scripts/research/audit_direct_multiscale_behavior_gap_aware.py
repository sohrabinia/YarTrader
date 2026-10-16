"""Gap-aware descriptive multiscale audit of real MT5 XAUUSD OHLC bars.
Descriptive research only: no trading signals, orders, or live integration.
"""
import csv,json,math,statistics
from collections import deque
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/"runtime_logs"/"mt5_gold_history_full"
OUT=DATA/"direct_multiscale_behavior_audit_gap_aware_20261010.json"
TFS=("M1","M5","M15","M30","H1","H4","D1","W1","MN1")
LAGS=(1,2,4,8,16,32,64,128,256,512,1024)
CAPS={"M1":250000,"M5":250000,"M15":200000,"M30":150000,"H1":100000,"H4":50000,"D1":10000,"W1":3000,"MN1":1000}
# Gaps typical of trading-session closures should not be bridged for intraday bars.
GAP_LIMIT={"M1":90,"M5":450,"M15":1350,"M30":2700,"H1":5400,"H4":64800,"D1":345600,"W1":1209600,"MN1":3888000}

def read_bars(path,cap):
    out=deque(maxlen=cap or None)
    with path.open("r",newline="",encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            try:
                t=int(float(r["time"]));o=float(r["open"]);h=float(r["high"]);l=float(r["low"]);c=float(r["close"])
                if t>0 and min(o,h,l,c)>0 and h>=max(o,c,l) and l<=min(o,c,h):out.append((t,o,h,l,c))
            except (ValueError,TypeError,KeyError):pass
    rows=list(out)
    if any(rows[i][0]>=rows[i+1][0] for i in range(len(rows)-1)):
        rows=sorted({r[0]:r for r in rows}.values(),key=lambda r:r[0])
    return rows

def split_segments(rows,tf):
    segs=[];cur=[];limit=GAP_LIMIT[tf]
    for r in rows:
        if cur and r[0]-cur[-1][0]>limit:
            if len(cur)>=20:segs.append(cur)
            cur=[]
        cur.append(r)
    if len(cur)>=20:segs.append(cur)
    return segs

def pair_corr(xs,ys):
    n=min(len(xs),len(ys))
    if n<3:return None
    xs=xs[:n];ys=ys[:n];mx=sum(xs)/n;my=sum(ys)/n
    vx=sum((x-mx)**2 for x in xs);vy=sum((y-my)**2 for y in ys)
    return sum((xs[i]-mx)*(ys[i]-my) for i in range(n))/math.sqrt(vx*vy) if vx>0 and vy>0 else None

def segment_corr(arrays,lag):
    xs=[];ys=[]
    for a in arrays:
        if len(a)>lag:
            xs.extend(a[:-lag]);ys.extend(a[lag:])
    return pair_corr(xs,ys)

def scaling(log_segments,lags):
    rows=[]
    for k in lags:
        chunks=[]
        for lp in log_segments:
            if len(lp)<=k:continue
            step=max(1,k//4)
            chunks.extend(lp[i+k]-lp[i] for i in range(0,len(lp)-k,step))
        if len(chunks)<30:continue
        m=sum(chunks)/len(chunks)
        sd=math.sqrt(sum((x-m)**2 for x in chunks)/len(chunks))
        if sd>0:rows.append({"lag_bars":k,"increment_sd_log":sd,"n":len(chunks)})
    if len(rows)<3:return None,rows
    x=[math.log(v["lag_bars"]) for v in rows];y=[math.log(v["increment_sd_log"]) for v in rows]
    mx=sum(x)/len(x);my=sum(y)/len(y)
    h=sum((a-mx)*(b-my) for a,b in zip(x,y))/sum((a-mx)**2 for a in x)
    return h,rows

def describe(rows,tf):
    segs=split_segments(rows,tf)
    if not segs:return {"status":"INSUFFICIENT_DATA","bars":len(rows),"segments":0}
    logsegs=[[math.log(r[4]) for r in s] for s in segs]
    retsegs=[[lp[i]-lp[i-1] for i in range(1,len(lp))] for lp in logsegs]
    retsegs=[x for x in retsegs if len(x)>10]
    rets=[x for s in retsegs for x in s]
    if len(rets)<100:return {"status":"INSUFFICIENT_DATA","bars":len(rows),"segments":len(segs)}
    mu=sum(rets)/len(rets);var=sum((x-mu)**2 for x in rets)/len(rets);sd=math.sqrt(var)
    kurt=sum(((x-mu)/sd)**4 for x in rets)/len(rets)-3 if sd else None
    abssegs=[[abs(x) for x in s] for s in retsegs]
    ac_r={str(k):segment_corr(retsegs,k) for k in (1,2,5,10,20,50)}
    ac_a={str(k):segment_corr(abssegs,k) for k in (1,2,5,10,20,50,100)}
    H,sc=scaling(logsegs,LAGS)
    trs=[]
    for seg in segs:
        for i,r in enumerate(seg):
            trs.append(max(r[2]-r[3],abs(r[2]-seg[i-1][4]),abs(r[3]-seg[i-1][4])) if i else r[2]-r[3])
    base=statistics.median(trs) if trs else 0
    ranges=[]
    for k in (4,8,16,32,64,128,256,512):
        vals=[]
        for seg in segs:
            if len(seg)<k:continue
            step=max(k,math.ceil(len(seg)/500))
            for end in range(k-1,len(seg),step):
                w=seg[end-k+1:end+1];vals.append(max(x[2] for x in w)-min(x[3] for x in w))
        if vals:ranges.append({"window_bars":k,"median_high_low_range":statistics.median(vals),
            "median_range_in_singlebar_TR":statistics.median(vals)/base if base else None,"n_windows":len(vals)})
    # Time thirds, each independently segmented so no returns bridge gaps.
    ordered=rows; thirds=[]; n=len(ordered)
    for name,part in (("early",ordered[:n//3]),("middle",ordered[n//3:2*n//3]),("recent",ordered[2*n//3:])):
        sub=split_segments(part,tf)
        lp=[[math.log(r[4]) for r in s] for s in sub]
        h,_=scaling(lp,(1,4,16,64,256))
        thirds.append({"period":name,"bars":len(part),"segments":len(sub),"scaling_exponent":h})
    return {"status":"EVALUATED","bars":len(rows),"segments":len(segs),"start_time":rows[0][0],"end_time":rows[-1][0],
      "return_mean_log":mu,"return_sd_log":sd,"excess_kurtosis":kurt,
      "return_autocorrelation":ac_r,"absolute_return_autocorrelation":ac_a,
      "increment_scaling":sc,"estimated_scaling_exponent_H":H,"range_growth":ranges,
      "subperiod_scaling_exponents":thirds,
      "interpretation":"Gap-aware descriptive scaling only. H near 0.5 is compatible with random-walk-like scaling and does not establish a fractal process or predictive edge."}

report={"status":"RESEARCH_DIAGNOSTIC_ONLY","asset":"XAUUSD",
 "method":"Gap-aware log-return dependence, log-increment scaling, rolling high-low range growth and split-period stability.",
 "configuration":{"bar_caps":CAPS,"gap_limits_seconds":GAP_LIMIT,"scaling_lags_bars":LAGS},
 "caveats":["Cross-session gaps are not treated as one-bar returns for intraday timeframes.","Scaling alone does not prove fractality or predictability.","Different timeframes overlap in calendar time and are not independent replicates.","Broker history and session conventions constrain conclusions.","No orders or live inference."],"timeframes":{}}
for tf in TFS:
 p=DATA/f"{tf}.csv"
 report["timeframes"][tf]=describe(read_bars(p,CAPS[tf]),tf) if p.exists() else {"status":"MISSING_FILE"}
OUT.write_text(json.dumps(report,indent=2),encoding="utf-8")
summary={tf:{"bars":v.get("bars"),"segments":v.get("segments"),"H":v.get("estimated_scaling_exponent_H"),
 "kurtosis":v.get("excess_kurtosis"),"ac1_return":v.get("return_autocorrelation",{}).get("1"),
 "ac1_abs_return":v.get("absolute_return_autocorrelation",{}).get("1"),
 "period_H":[x.get("scaling_exponent") for x in v.get("subperiod_scaling_exponents",[])]}
 for tf,v in report["timeframes"].items()}
print(json.dumps({"output":str(OUT),"summary":summary},indent=2))
