from pathlib import Path
import csv, json
from datetime import datetime
base=Path(r'C:\Projects\YarTrader\runtime_logs\mt5_gold_history_full\higher_timeframe_2010')
for fn in ['XAUUSD_MN1_from_2010.csv','XAUUSD_W1_from_2010.csv','XAUUSD_D1_from_2010.csv']:
 p=base/fn
 with p.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
 print('\nFILE',fn,'rows',len(rows),'columns',list(rows[0]) if rows else [])
 for label,a,b in [('2010-2028','2010-01-01','2028-01-01'),('2010-2016','2010-01-01','2016-01-01'),('2016-2022','2016-01-01','2022-01-01'),('2022-2028 observed','2022-01-01','2028-01-01')]:
  d=[r for r in rows if a<=r['time_utc'][:10]<b]
  if not d: print(label,'NO DATA'); continue
  hirow=max(d,key=lambda r:float(r['high'])); lorow=min(d,key=lambda r:float(r['low']))
  hi=float(hirow['high']); lo=float(lorow['low'])
  print(json.dumps({'period':label,'n':len(d),'first':d[0]['time_utc'],'last':d[-1]['time_utc'],'high':hi,'high_date':hirow['time_utc'],'low':lo,'low_date':lorow['time_utc'],'range_abs':hi-lo,'last_close':float(d[-1]['close'])},ensure_ascii=False))
