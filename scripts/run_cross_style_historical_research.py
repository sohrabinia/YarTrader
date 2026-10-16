"""Isolated cross-style XAUUSD research; no broker orders or production memory writes.

Uses M15 OHLCV/spread CSV. First half calibrates only the volatility/compression
threshold; second half is chronological holdout. All styles share execution,
barrier, gap, and cost assumptions. Results are research-only, not promotion.
"""
from __future__ import annotations
import argparse, hashlib, json, math, time
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / 'runtime_logs' / 'mt5_gold_history_full' / 'M15.csv'
DEFAULT_OUT = ROOT / 'runtime_logs' / 'cross_style_research'


def metrics(trades):
    if not trades:
        return {'trades':0,'net_total_r':0.0,'net_mean_r':None,'profit_factor':None,'win_rate':None,'max_drawdown_r':0.0,'median_hold_bars':None}
    r=np.asarray([x['net_r'] for x in trades],dtype=float); gross=np.asarray([x['gross_r'] for x in trades],dtype=float)
    eq=np.cumsum(r); peak=np.maximum.accumulate(np.r_[0.0,eq])[1:]
    gains=float(r[r>0].sum()); losses=float(-r[r<0].sum())
    return {'trades':len(r),'net_total_r':round(float(r.sum()),4),'net_mean_r':round(float(r.mean()),6),
      'gross_mean_r':round(float(gross.mean()),6),'gross_total_r':round(float(gross.sum()),4),
      'mean_cost_r':round(float(np.mean([x['cost_r'] for x in trades])),6),
      'profit_factor':round(gains/losses,4) if losses else None,'win_rate':round(float((r>0).mean()),4),
      'max_drawdown_r':round(float(np.max(peak-eq)),4),'median_hold_bars':float(np.median([x['hold'] for x in trades]))}


def load_data(path):
    df=pd.read_csv(path)
    needed={'time','open','high','low','close','spread'}
    if not needed.issubset(df.columns): raise ValueError(f'Missing columns: {sorted(needed-set(df.columns))}')
    df=df.sort_values('time').drop_duplicates('time').reset_index(drop=True)
    for c in ['time','open','high','low','close','spread']: df[c]=pd.to_numeric(df[c],errors='coerce')
    df=df.dropna(subset=['time','open','high','low','close','spread']).reset_index(drop=True)
    df=df[(df['high']>=df[['open','close','low']].max(axis=1)) & (df['low']<=df[['open','close','high']].min(axis=1))].reset_index(drop=True)
    return df


def prepare(df):
    c,h,l=df.close,df.high,df.low
    prev=c.shift(1)
    tr=pd.concat([h-l,(h-prev).abs(),(l-prev).abs()],axis=1).max(axis=1)
    df['atr']=tr.rolling(14,min_periods=14).mean()
    df['ema20']=c.ewm(span=20,adjust=False,min_periods=20).mean()
    df['ema50']=c.ewm(span=50,adjust=False,min_periods=50).mean()
    df['ema100']=c.ewm(span=100,adjust=False,min_periods=100).mean()
    df['hi20']=h.shift(1).rolling(20,min_periods=20).max(); df['lo20']=l.shift(1).rolling(20,min_periods=20).min()
    df['hi24']=h.shift(1).rolling(24,min_periods=24).max(); df['lo24']=l.shift(1).rolling(24,min_periods=24).min()
    df['hi48']=h.shift(1).rolling(48,min_periods=48).max(); df['lo48']=l.shift(1).rolling(48,min_periods=48).min()
    df['ret20']=(c-c.shift(20))/df.atr
    df['compression']=(df.hi24-df.lo24)/df.atr
    return df


def make_signals(df, train_end):
    # Only fit this threshold on the training half; freeze it for holdout.
    threshold=float(df.loc[:train_end,'compression'].replace([np.inf,-np.inf],np.nan).dropna().quantile(.25))
    valid=df.atr.notna() & (df.atr>0)
    trend_long=valid & (df.ema20>df.ema50) & (df.close>df.ema20) & (df.ret20>0.8)
    trend_short=valid & (df.ema20<df.ema50) & (df.close<df.ema20) & (df.ret20<-.8)
    mr_long=valid & (df.close<df.lo20+.05*df.atr) & (df.close<df.ema50-.8*df.atr)
    mr_short=valid & (df.close>df.hi20-.05*df.atr) & (df.close>df.ema50+.8*df.atr)
    # Trigger only on entry into a condition, avoiding repeated re-entries on every bar.
    signals={
      'trend_following': np.where(trend_long & ~trend_long.shift(1,fill_value=False),1,
                         np.where(trend_short & ~trend_short.shift(1,fill_value=False),-1,0)),
      'range_breakout': np.where(valid & (df.close>df.hi20+.10*df.atr),1,np.where(valid & (df.close<df.lo20-.10*df.atr),-1,0)),
      'mean_reversion': np.where(mr_long & ~mr_long.shift(1,fill_value=False),1,
                          np.where(mr_short & ~mr_short.shift(1,fill_value=False),-1,0)),
      'trend_pullback': np.where(valid & (df.ema50>df.ema100) & (df.low<=df.ema20) & (df.close>df.ema20) & (df.close>df.open),1,
                          np.where(valid & (df.ema50<df.ema100) & (df.high>=df.ema20) & (df.close<df.ema20) & (df.close<df.open),-1,0)),
      'compression_breakout': np.where(valid & (df.compression<=threshold) & (df.close>df.hi24+.10*df.atr),1,
                                np.where(valid & (df.compression<=threshold) & (df.close<df.lo24-.10*df.atr),-1,0)),
      'momentum': np.where(valid & (df.ema20>df.ema50) & (df.ema20.shift(1)<=df.ema50.shift(1)),1,
                  np.where(valid & (df.ema20<df.ema50) & (df.ema20.shift(1)>=df.ema50.shift(1)),-1,0)),
    }
    # A derived consensus hypothesis: at least two non-mean-reversion styles agree.
    # This is deliberately tested as a candidate, not treated as a discovered edge.
    vote_names=['trend_following','range_breakout','trend_pullback','compression_breakout','momentum']
    votes=np.vstack([signals[k] for k in vote_names])
    long_votes=(votes==1).sum(axis=0); short_votes=(votes==-1).sum(axis=0)
    signals['consensus_hybrid']=np.where(long_votes>=2,1,np.where(short_votes>=2,-1,0))
    return signals,threshold


def backtest(df, signal, start, end, *, spread_mult=1.0, slippage_r=.05, stop_atr=1.0, target_r=1.5, max_hold=32):
    # Signals are observed at bar close; entries occur next bar open. Stop-first on ambiguous bars.
    t=[]; i=max(start,110)
    times=df.time.to_numpy(); o=df.open.to_numpy(); h=df.high.to_numpy(); l=df.low.to_numpy(); c=df.close.to_numpy(); a=df.atr.to_numpy(); spr=df.spread.to_numpy()
    sig=np.asarray(signal)
    while i<end-1:
        if not np.isfinite(a[i]) or a[i]<=0 or sig[i]==0 or times[i+1]-times[i]>1800:
            i+=1; continue
        side=int(sig[i]); entry_i=i+1; entry=float(o[entry_i]); risk=float(a[i]*stop_atr)
        if risk<=0 or not math.isfinite(risk): i+=1; continue
        stop=entry-side*risk; target=entry+side*risk*target_r
        exit_i=min(end-1,entry_i+max_hold); exit_px=float(c[exit_i]); reason='timeout'
        for j in range(entry_i,exit_i+1):
            if times[j]-times[j-1]>1800:
                exit_i=j-1; exit_px=float(c[exit_i]); reason='gap_exit'; break
            stop_hit=(l[j]<=stop) if side>0 else (h[j]>=stop)
            target_hit=(h[j]>=target) if side>0 else (l[j]<=target)
            if stop_hit:
                exit_i=j; exit_px=stop; reason='stop'; break
            if target_hit:
                exit_i=j; exit_px=target; reason='target'; break
        gross=side*(exit_px-entry)/risk
        # CSV spread is in broker points; point-size 0.01 is provisional and must be verified.
        cost_price=max(0.0,float(spr[entry_i]))*.01*spread_mult + max(0.0,float(spr[exit_i]))*.01*spread_mult
        cost_r=cost_price/risk + slippage_r
        t.append({'entry_i':entry_i,'exit_i':exit_i,'side':side,'gross_r':gross,'cost_r':cost_r,'net_r':gross-cost_r,'hold':max(1,exit_i-entry_i),'reason':reason})
        i=max(entry_i+1,exit_i+1)
    return t


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--data',type=Path,default=DEFAULT_DATA); ap.add_argument('--out',type=Path,default=DEFAULT_OUT); ap.add_argument('--spread-mult',type=float,default=1.0); args=ap.parse_args()
    started=time.time(); raw_hash=hashlib.sha256()
    with args.data.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): raw_hash.update(chunk)
    df=prepare(load_data(args.data)); n=len(df); split=n//2
    signals,compression_cut=make_signals(df,split)
    # Holdout is the latter half. Train and holdout are evaluated independently; no shared positions.
    report={'status':'RESEARCH_ONLY_NO_ORDER_ROUTING','symbol':'XAUUSD','timeframe':'M15','source':str(args.data),
      'source_sha256':raw_hash.hexdigest(),'bars_after_validation':n,'first_utc':pd.to_datetime(df.time.iloc[0],unit='s',utc=True).isoformat(),
      'last_utc':pd.to_datetime(df.time.iloc[-1],unit='s',utc=True).isoformat(),'split_index':split,
      'train_period':{'start':pd.to_datetime(df.time.iloc[0],unit='s',utc=True).isoformat(),'end':pd.to_datetime(df.time.iloc[split-1],unit='s',utc=True).isoformat()},
      'holdout_period':{'start':pd.to_datetime(df.time.iloc[split],unit='s',utc=True).isoformat(),'end':pd.to_datetime(df.time.iloc[-1],unit='s',utc=True).isoformat()},
      'assumptions':{'signal_at_close_entry_next_open':True,'stop_atr':1.0,'target_r':1.5,'max_hold_bars':32,'ambiguous_bar_stop_first':True,'gap_policy':'exit at previous close when timestamp gap > 30 minutes','spread_column_point_size_assumption':0.01,'point_size_verified':False,'spread_multiplier':args.spread_mult,'slippage_round_trip_r':0.05,'commission_included':False,'one_position_at_a_time_per_style':True,'overlapping_trades_within_style':False,'styles_are_fixed_proxies_not_production_implementations':True},
      'training_compression_q25':compression_cut,'styles':{},'cross_style_commonality':{},'limitations':['M15 style proxies, not a faithful reimplementation of every production strategy','broker point size 0.01 is unverified; cost conclusions are provisional','OHLC intrabar path unknown; stop-first convention is conservative','commission and swaps unavailable','holdout is one chronological split; multiple comparisons still risk overfit','no orders sent; no production memory or journal writes']}
    for name,sig in signals.items():
        tr=backtest(df,sig,110,split,spread_mult=args.spread_mult); ho=backtest(df,sig,split,n-1,spread_mult=args.spread_mult)
        report['styles'][name]={'train':metrics(tr),'holdout':metrics(ho),'holdout_exit_reasons':{k:sum(x['reason']==k for x in ho) for k in ['target','stop','timeout','gap_exit']}}
    # Compare whether a trade taken by multiple style rules has more robust outcomes; descriptive only.
    names=list(signals); counts=np.zeros(n,dtype=int)
    for s in signals.values(): counts += (np.asarray(s)!=0).astype(int)
    report['cross_style_commonality']={'bars_with_any_signal_holdout':int(np.sum(counts[split:] > 0)),
      'bars_with_two_or_more_styles_holdout':int(np.sum(counts[split:] >= 2)),
      'style_signal_agreement_holdout':{},
      'interpretation':'Signal overlap is a hypothesis generator, not evidence of profitability; do not deploy without separate validation.'}
    for a_name in names:
      report['cross_style_commonality']['style_signal_agreement_holdout'][a_name]={}
      for b_name in names:
        if names.index(b_name)<=names.index(a_name): continue
        a=np.asarray(signals[a_name])[split:]; b=np.asarray(signals[b_name])[split:]; both=(a!=0)&(b!=0)
        report['cross_style_commonality']['style_signal_agreement_holdout'][a_name][b_name]={'overlap_bars':int(both.sum()),'same_direction_pct':round(float((a[both]==b[both]).mean()),4) if both.any() else None}
    report['elapsed_seconds']=round(time.time()-started,2)
    args.out.mkdir(parents=True,exist_ok=True); stamp=pd.Timestamp.now('UTC').strftime('%Y%m%dT%H%M%SZ')
    out=args.out/f'cross_style_xauusd_m15_{stamp}.json'; out.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    summary={'report_path':str(out),'status':report['status'],'bars':n,'compression_q25_train':compression_cut,'styles':{k:{'train':v['train'],'holdout':v['holdout']} for k,v in report['styles'].items()},'commonality':report['cross_style_commonality'],'elapsed_seconds':report['elapsed_seconds'],'cost_assumption_warning':'point size 0.01 unverified'}
    (args.out/'latest_summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__': main()
