from pathlib import Path
import csv, json
from collections import defaultdict
p=Path(r'C:\Projects\YarTrader\runtime_logs\mt5_gold_history_full\higher_timeframe_2010\XAUUSD_D1_from_2010.csv')
with p.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
by=defaultdict(list)
for r in rows: by[int(r['time_utc'][:4])].append(r)
out=[]
for y in range(2010,2028):
 d=by.get(y,[])
 if not d: continue
 hi=max(d,key=lambda r:float(r['high'])); lo=min(d,key=lambda r:float(r['low']))
 op=float(d[0]['open']); close=float(d[-1]['close']); high=float(hi['high']); low=float(lo['low'])
 cycle='2010-2016' if y<2016 else ('2016-2022' if y<2022 else '2022-2028')
 out.append({'year':y,'cycle':cycle,'bars':len(d),'open':op,'close':close,'return_pct':round((close/op-1)*100,2),'high':high,'high_date':hi['time_utc'][:10],'low':low,'low_date':lo['time_utc'][:10],'range':round(high-low,2),'range_pct_of_low':round((high-low)/low*100,2),'last_bar':d[-1]['time_utc'][:10]})
print(json.dumps(out,indent=2))
