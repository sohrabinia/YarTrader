"""Direct empirical multiscale behavior audit for MT5 XAUUSD bars. Research only; no orders."""
import csv, json, math, statistics
from collections import deque
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/"runtime_logs"/"mt5_gold_history_full"
OUT=DATA/"direct_multiscale_behavior_audit_20261010.json"
TFS=("M1","M5","M15","M30","H1","H4","D1","W1","MN1")
LAGS=(1,2,4,8,16,32,64,128,256,512,1024)
CAPS={"M1":250000,"M5":250000,"M15":200000,"M30":150000,"H1":100000,"H4":50000,"D1":10000,"W1":3000,"MN1":1000}

def read_bars(path,cap):
    out=deque(maxlen=cap or None)
    with path.open("r",newline="",encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            try:
                t=int(float(r["time"])); o=float(r["open"]); h=float(r["high"]); l=float(r["low"]); c=float(r["close"])
                if t>0 and min(o,h,l,c)>0 and h>=max(o,c,l) and l<=min(o,c,h): out.append((t,o,h,l,c))
            except (ValueError,TypeError,KeyError): pass
    rows=list(out)
    if any(rows[i][0]>=rows[i+1][0] for i in range(len(rows)-1)):
        rows=sorted({r[0]:r for r in rows}.values(),key=lambda r:r[0])
    return rows

def corr(a,b):
    n=min(len(a),len(b))
    if n<3:return None
    a=a[:n];b=b[:n];ma=sum(a)/n;mb=sum(b)/n
    va=sum((x-ma)**2 for x in a);vb=sum((x-mb)**2 for x in b)
    return sum((a[i]-ma)*(b[i]-mb) for i in range(n))/math.sqrt(va*vb) if va>0 and vb>0 else None

def scaling_exp(logp,lags):
    sc=[]
    for k in lags:
        if k>=len(logp)//3:continue
        step=max(1,k//4)
        vals=[logp[i+k]-logp[i] for i in range(0,len(logp)-k,step)]
        m=sum(vals)/len(vals);sd=math.sqrt(sum((v-m)**2 for v in vals)/len(vals))
        if sd>0:sc.append({"lag_bars":k,"increment_sd_log":sd,"n":len(vals)})
    if len(sc)<3:return None,sc
    xs=[math.log(x["lag_bars"]) for x in sc];ys=[math.log(x["increment_sd_log"]) for x in sc]
    xm=sum(xs)/len(xs);ym=sum(ys)/len(ys)
    return sum((x-xm)*(y-ym) for x,y in zip(xs,ys))/sum((x-xm)**2 for x in xs),sc

def describe(rows):
    if len(rows)<100:return {"status":"INSUFFICIENT_DATA","bars":len(rows)}
    lp=[math.log(r[4]) for r in rows];rets=[lp[i]-lp[i-1] for i in range(1,len(lp))];n=len(rets)
    mu=sum(rets)/n;var=sum((x-mu)**2 for x in rets)/n;sd=math.sqrt(var) if var>0 else 0
    kurt=sum(((x-mu)/sd)**4 for x in rets)/n-3 if sd else None
    ar=[abs(x) for x in rets]
    ac_r={str(k):corr(rets[:-k],rets[k:]) for k in (1,2,5,10,20,50) if n>k+3}
    ac_a={str(k):corr(ar[:-k],ar[k:]) for k in (1,2,5,10,20,50,100) if n>k+3}
    H,sc=scaling_exp(lp,LAGS)
    tr=[]
    for i,r in enumerate(rows):
        tr.append(max(r[2]-r[3],abs(r[2]-rows[i-1][4]),abs(r[3]-rows[i-1][4])) if i else r[2]-r[3])
    base=statistics.median(tr) if tr else 0
    ranges=[]
    for k in (4,8,16,32,64,128,256,512):
        if k>=len(rows)//3:continue
        step=max(k,math.ceil(len(rows)/1200));vals=[]
        for end in range(k-1,len(rows),step):
            w=rows[end-k+1:end+1];vals.append(max(x[2] for x in w)-min(x[3] for x in w))
        if vals:ranges.append({"window_bars":k,"median_high_low_range":statistics.median(vals),
                               "median_range_in_singlebar_TR":statistics.median(vals)/base if base else None,"n_windows":len(vals)})
    thirds=[]
    nbar=len(rows)
    for name,part in (("early",rows[:nbar//3]),("middle",rows[nbar//3:2*nbar//3]),("recent",rows[2*nbar//3:])):
        if len(part)<1000:continue
        h,_=scaling_exp([math.log(r[4]) for r in part],(1,4,16,64,256))
        thirds.append({"period":name,"bars":len(part),"scaling_exponent":h})
    return {"status":"EVALUATED","bars":len(rows),"start_time":rows[0][0],"end_time":rows[-1][0],
      "return_mean_log":mu,"return_sd_log":sd,"excess_kurtosis":kurt,
      "return_autocorrelation":ac_r,"absolute_return_autocorrelation":ac_a,
      "increment_scaling":sc,"estimated_scaling_exponent_H":H,"range_growth":ranges,
      "subperiod_scaling_exponents":thirds,
      "interpretation":"Scaling is descriptive, not proof of fractality or predictive edge; H near 0.5 is compatible with random-walk-like scaling."}

report={"status":"RESEARCH_DIAGNOSTIC_ONLY","asset":"XAUUSD",
 "method":"Log-return dependence, increment scaling, rolling high-low range growth, and split-period stability on actual MT5 OHLC bars.",
 "configuration":{"per_timeframe_bar_caps":CAPS,"scaling_lags_bars":LAGS},
 "caveats":["Scaling alone does not prove fractality or predictability.","Different timeframe series overlap in calendar time and are not independent replicates.","MT5 history and broker/session conventions constrain conclusions.","No orders or live inference."],"timeframes":{}}
for tf in TFS:
 p=DATA/f"{tf}.csv"
 report["timeframes"][tf]=describe(read_bars(p,CAPS[tf])) if p.exists() else {"status":"MISSING_FILE"}
OUT.write_text(json.dumps(report,indent=2),encoding="utf-8")
summary={tf:{"bars":v.get("bars"),"H":v.get("estimated_scaling_exponent_H"),"kurtosis":v.get("excess_kurtosis"),
 "ac1_return":v.get("return_autocorrelation",{}).get("1"),"ac1_abs_return":v.get("absolute_return_autocorrelation",{}).get("1"),
 "period_H":[x.get("scaling_exponent") for x in v.get("subperiod_scaling_exponents",[])]}
 for tf,v in report["timeframes"].items()}
print(json.dumps({"output":str(OUT),"summary":summary},indent=2))
