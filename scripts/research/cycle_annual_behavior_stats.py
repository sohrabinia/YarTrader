from pathlib import Path
import csv, json
from collections import defaultdict
p=Path(r'C:\Projects\YarTrader\runtime_logs\mt5_gold_history_full\higher_timeframe_2010\XAUUSD_D1_from_2010.csv')
with p.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
by=defaultdict(list)
for r in rows: by[int(r['time_utc'][:4])].append(r)
out=[]
for y in range(2010,2027):
 d=by.get(y,[])
 if not d: continue
 hi=max(d,key=lambda r:float(r['high'])); lo=min(d,key=lambda r:float(r['low']))
 op=float(d[0]['open']); close=float(d[-1]['close']); high=float(hi['high']); low=float(lo['low'])
 cycle='C1' if y<2016 else ('C2' if y<2022 else 'C3')
 out.append({'year':y,'cycle':cycle,'range_pct':round((high-low)/low*100,1),'close_position_pct':round((close-low)/(high-low)*100,1),'return_pct':round((close/op-1)*100,1),'high_date':hi['time_utc'][:10],'low_date':lo['time_utc'][:10]})
print('YEARLY',json.dumps(out))
for c in ['C1','C2','C3']:
 ds=[r for r in out if r['cycle']==c]
 print(c,json.dumps({'years':[r['year'] for r in ds],'mean_range_pct':round(sum(r['range_pct'] for r in ds)/len(ds),1),'mean_close_pos_pct':round(sum(r['close_position_pct'] for r in ds)/len(ds),1),'up_years':sum(r['return_pct']>0 for r in ds),'down_years':sum(r['return_pct']<0 for r in ds)}))
