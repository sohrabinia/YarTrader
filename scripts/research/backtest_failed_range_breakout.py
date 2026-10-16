"""Fixed-rule XAUUSD M1 failed-breakout / rejection event study. Research only."""
import csv, json, time
from array import array
from collections import deque
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "runtime_logs" / "mt5_gold_history_full"
SOURCE = DATA / "M1.csv"
OUT = DATA / "xauusd_failed_breakout_event_backtest_20261010.json"
LOOKBACK = 24
ATR_LENGTH = 24
MAX_GAP_SECONDS = 90
BUFFER_ATR = 0.10
TARGET_R = 1.5
MAX_HOLD = 24
POINT_SIZE = 0.01  # Explicit assumption; verify broker symbol metadata.


def load():
    cols = [array("q"), array("d"), array("d"), array("d"), array("d"), array("d")]
    with SOURCE.open("r", newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            try:
                vals = (int(float(r["time"])), float(r["open"]), float(r["high"]),
                        float(r["low"]), float(r["close"]), max(0.0, float(r.get("spread") or 0)))
            except (ValueError, TypeError, KeyError):
                continue
            t,o,h,l,c,s = vals
            if t > 0 and min(o,h,l,c) > 0 and h >= max(o,c,l) and l <= min(o,c,h):
                for a,v in zip(cols, vals): a.append(v)
    return tuple(np.frombuffer(a, dtype=np.int64 if a.typecode == "q" else np.float64) for a in cols)


def features(t,o,h,l,c):
    n=len(t); atr=np.full(n,np.nan); ph=np.full(n,np.nan); pl=np.full(n,np.nan)
    segments=[]; gaps=np.flatnonzero(np.diff(t)>MAX_GAP_SECONDS)+1
    bounds=[0,*gaps.tolist(),n]
    for a,b in zip(bounds[:-1],bounds[1:]):
        if b-a <= LOOKBACK+MAX_HOLD+2: continue
        segments.append((a,b))
        tr=h[a:b]-l[a:b]
        if b-a>1:
            tr[1:]=np.maximum.reduce([h[a+1:b]-l[a+1:b],np.abs(h[a+1:b]-c[a:b-1]),np.abs(l[a+1:b]-c[a:b-1])])
        cs=np.concatenate(([0.],np.cumsum(tr)))
        hq=deque(); lq=deque()
        for i in range(a+1,b):
            add=i-1
            while hq and h[hq[-1]]<=h[add]: hq.pop()
            hq.append(add)
            while lq and l[lq[-1]]>=l[add]: lq.pop()
            lq.append(add)
            oldest=i-LOOKBACK
            while hq and hq[0]<oldest: hq.popleft()
            while lq and lq[0]<oldest: lq.popleft()
            if i-a<LOOKBACK: continue
            local=i-a
            av=(cs[local]-cs[local-ATR_LENGTH])/ATR_LENGTH
            if av<=0 or not np.isfinite(av): continue
            atr[i]=av; ph[i]=h[hq[0]]; pl[i]=l[lq[0]]
    return atr,ph,pl,segments


def run(t,o,h,l,c,sp,atr,ph,pl,segments,test_start,side_mode):
    trades=[]; event_count={"upper":0,"lower":0}
    for a,b in segments:
        i=max(a+LOOKBACK,test_start); free=i
        while i<b-1:
            if i<free or not np.isfinite(atr[i]): i+=1; continue
            # Failed break: wick breaches prior range by buffer, but close returns inside.
            upper=(h[i]>ph[i]+BUFFER_ATR*atr[i] and c[i]<ph[i])
            lower=(l[i]<pl[i]-BUFFER_ATR*atr[i] and c[i]>pl[i])
            if upper == lower: i+=1; continue
            event_count["upper" if upper else "lower"]+=1
            # Fade rejection. Stop outside the sweep extreme plus a small ATR buffer.
            direction=-1 if upper else 1
            entry_i=i+1; entry=o[entry_i]
            stop=(h[i]+BUFFER_ATR*atr[i]) if upper else (l[i]-BUFFER_ATR*atr[i])
            risk=abs(stop-entry)
            if risk < 0.10*atr[i] or risk > 3.0*atr[i]: i+=1; continue
            target=entry+direction*TARGET_R*risk
            last=min(b-1,entry_i+MAX_HOLD-1)
            exit_i=last; exit_price=c[last]; reason="time"
            for j in range(entry_i,last+1):
                stop_hit=(h[j]>=stop) if direction<0 else (l[j]<=stop)
                target_hit=(l[j]<=target) if direction<0 else (h[j]>=target)
                if stop_hit:
                    exit_i=j
                    exit_price=max(o[j],stop) if direction<0 and o[j]>stop else (min(o[j],stop) if direction>0 and o[j]<stop else stop)
                    reason="both_stop_first" if target_hit else "stop"; break
                if target_hit:
                    exit_i=j; exit_price=target; reason="target"; break
            gross=direction*(exit_price-entry)/risk
            # spread column in broker points; conservative entry + exit spread cost approximation.
            spread_r=(sp[entry_i]+sp[exit_i])*POINT_SIZE/(2*risk)
            trades.append({"time":int(t[i]),"side":"fade_upper" if upper else "fade_lower",
                           "gross_r":float(gross),"spread_cost_r":float(spread_r),
                           "hold_bars":int(exit_i-entry_i+1),"exit_reason":reason,
                           "risk_atr":float(risk/atr[i])})
            free=exit_i+1; i=free
    return trades,event_count


def stats(trades,mult=1.0):
    if not trades:return {"trades":0}
    gross=np.array([x["gross_r"] for x in trades])
    net=np.array([x["gross_r"]-mult*x["spread_cost_r"]-0.05 for x in trades])
    gp=float(net[net>0].sum()); gl=float(-net[net<0].sum())
    eq=np.cumsum(net); peak=np.maximum.accumulate(np.r_[0.,eq])[1:]
    return {"trades":len(trades),"gross_mean_r":float(gross.mean()),"gross_total_r":float(gross.sum()),
            "net_mean_r":float(net.mean()),"net_total_r":float(net.sum()),
            "profit_factor_net":gp/gl if gl else None,"net_win_rate":float((net>0).mean()),
            "max_drawdown_r":float((peak-eq).max()),"target_rate":float(np.mean([x["exit_reason"]=="target" for x in trades])),
            "stop_rate":float(np.mean([x["exit_reason"] in ("stop","both_stop_first") for x in trades])),
            "mean_spread_cost_r":float(np.mean([x["spread_cost_r"] for x in trades])),
            "median_hold_bars":float(np.median([x["hold_bars"] for x in trades])),
            "slippage_assumption_r":0.05,"spread_multiplier":mult}


def main():
    started=time.time()
    t,o,h,l,c,sp=load()
    atr,ph,pl,segs=features(t,o,h,l,c)
    split=len(t)//2
    # Fixed definition; no threshold fitting on test. Only later half used for evaluation.
    trades,events=run(t,o,h,l,c,sp,atr,ph,pl,segs,split,"fade")
    report={"status":"RESEARCH_ONLY_NO_ORDER_ROUTING","symbol":"XAUUSD","timeframe":"M1",
      "source":str(SOURCE),"data":{"bars":len(t),"segments":len(segs),"first_time":int(t[0]),"last_time":int(t[-1]),
      "test_start_index":split,"test_bars":len(t)-split},
      "rule":{"event":"prior 24-bar high/low swept by >0.10 ATR intrabar, but close returns inside prior range",
      "entry":"next bar open, fade rejection","stop":"beyond event-bar extreme by 0.10 ATR",
      "target":"1.5R","max_hold_bars":MAX_HOLD,"one_position_at_a_time":True,
      "same_bar_stop_target":"stop first","gap_split_seconds":MAX_GAP_SECONDS,
      "costs":"MT5 spread column converted with assumed 0.01 point size plus 0.05R round-trip slippage",
      "point_size_warning":"0.01 is unverified; confirm broker symbol metadata"},
      "test_period":"later half of history only; no parameter tuning",
      "events_detected":events,
      "results":{"spread_1x":stats(trades,1.0),"spread_2x":stats(trades,2.0),
                 "by_side":{s:stats([x for x in trades if x["side"]==s],1.0) for s in ("fade_upper","fade_lower")}},
      "limitations":["OHLC cannot establish exact intrabar order; ambiguous stop/target resolved stop-first",
      "point size assumption unverified","not account-currency PnL; commission not separately available",
      "fixed candidate only; no live trading"],
      "sample_trades":trades[:15],"elapsed_seconds":round(time.time()-started,2)}
    OUT.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps({"output":str(OUT),"data":report["data"],"events":events,"results":report["results"],
                      "elapsed_seconds":report["elapsed_seconds"]},indent=2))

if __name__=="__main__": main()
