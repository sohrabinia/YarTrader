import csv, json, os
from collections import deque
root=r'C:\Projects\YarTrader\runtime_logs\mt5_gold_history_full'
files={'MN1':('MN1.csv',12),'W1':('W1.csv',52),'D1':('D1.csv',252),'H4':('H4.csv',1512),'H1':('H1.csv',6048),'M15':('M15.csv',20160),'M5':('M5.csv',60480),'M1':('M1.csv',362880)}
def rolling_extreme(vals,w,maximum):
 q=deque(); out=[None]*len(vals)
 for i,v in enumerate(vals):
  while q and q[0] <= i-w: q.popleft()
  while q and ((vals[q[-1]] <= v) if maximum else (vals[q[-1]] >= v)): q.pop()
  q.append(i)
  if i>=w-1: out[i]=vals[q[0]]
 return out
results=[]
for tf,(fn,annual0) in files.items():
 highs=[]; lows=[]; closes=[]
 with open(os.path.join(root,fn),newline='') as f:
  for r in csv.DictReader(f):
   try: highs.append(float(r['high'])); lows.append(float(r['low'])); closes.append(float(r['close']))
   except: pass
 n=len(closes); annual=min(annual0,n-1); short=max(3,round(annual/12))
 ah=rolling_extreme(highs,annual,True); al=rolling_extreme(lows,annual,False)
 sh=rolling_extreme(highs,short,True); sl=rolling_extreme(lows,short,False)
 sig=[]; base=[]
 for i,c in enumerate(closes):
  if ah[i] is None or al[i] is None or ah[i]==al[i] or sh[i] is None or sh[i]==sl[i]: continue
  p=(c-al[i])/(ah[i]-al[i]); sp=(c-sl[i])/(sh[i]-sl[i])
  if p<=.20: base.append(i)
  if p<=.20 and sp>=.75: sig.append(i)
 kept=[]; last=-10**12
 for i in sig:
  if i-last>=short: kept.append(i); last=i
 horizons=sorted(set(max(1,round(annual*x)) for x in [1/12,1/4,1/2]))
 row={'tf':tf,'bars':n,'annual_window':annual,'short_window':short,'raw_signals':len(sig),'events':len(kept)}
 for h in horizons:
  ev=[(closes[i+h]/closes[i]-1)*100 for i in kept if i+h<n]
  br=[(closes[i+h]/closes[i]-1)*100 for i in base if i+h<n]
  row['h'+str(h)]={'event_n':len(ev),'event_mean_pct':round(sum(ev)/len(ev),3) if ev else None,'event_median_pct':round(sorted(ev)[len(ev)//2],3) if ev else None,'event_win_pct':round(sum(x>0 for x in ev)/len(ev)*100,1) if ev else None,'lowrange_n':len(br),'lowrange_mean_pct':round(sum(br)/len(br),3) if br else None,'lowrange_win_pct':round(sum(x>0 for x in br)/len(br)*100,1) if br else None}
 results.append(row); print(tf, 'bars',n,'events',len(kept), flush=True)
out={'description':'Signal: annual range position <=20% and recent range position >=75%; recent window=max(3 bars, annual/12). Events declustered by short window. Forward close-to-close returns gross of costs. Baseline all bars with annual position <=20%, overlapping. Horizons approximately 1, 3, 6 annual fractions. Descriptive only.','results':results}
p=os.path.join(root,'multiscale_annual_low_recent_rebound_20261010.json')
with open(p,'w') as f: json.dump(out,f,indent=2)
print(json.dumps(out,indent=2))
