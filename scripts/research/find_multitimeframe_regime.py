import csv,json,statistics,datetime
from pathlib import Path
p=Path(r'C:\Projects\YarTrader\runtime_logs\mt5_gold_history_full\D1.csv')
r=[]
with p.open(newline='',encoding='utf-8-sig') as f:
 for x in csv.DictReader(f):
  try:r.append((int(float(x['time'])),float(x['open']),float(x['high']),float(x['low']),float(x['close'])))
  except:pass
r.sort()
def dt(t):return datetime.datetime.fromtimestamp(t,datetime.timezone.utc).strftime('%Y-%m-%d')
events=[]
for i in range(252,len(r)-60):
 w=r[i-251:i+1]; hi=max(x[2] for x in w);lo=min(x[3] for x in w);c=r[i][4]
 pos=(c-lo)/(hi-lo) if hi>lo else .5
 s=r[max(0,i-19):i+1];shi=max(x[2] for x in s);slo=min(x[3] for x in s);spos=(c-slo)/(shi-slo) if shi>slo else .5
 if pos<=.20 and spos>=.75:
  ev={'date':dt(r[i][0]),'close':c,'long_range_pos':round(pos*100,1),'20d_range_pos':round(spos*100,1)}
  for h in (5,20,60):
   f=r[i+h][4]; ev[f'ret_{h}d_pct']=round((f/c-1)*100,2)
   fw=r[i+1:i+h+1];ev[f'up_{h}d']=max(x[2] for x in fw)>shi
   ev[f'down_{h}d']=min(x[3] for x in fw)<slo
  events.append(ev)
# decluster overlapping events, retain first then require >=20 trading days apart
cluster=[]
for e in events:
 if not cluster or (datetime.datetime.strptime(e['date'],'%Y-%m-%d')-datetime.datetime.strptime(cluster[-1]['date'],'%Y-%m-%d')).days>=25:cluster.append(e)
def stats(es):
 out={'n':len(es)}
 for h in (5,20,60):
  vals=[e[f'ret_{h}d_pct'] for e in es]
  out[str(h)+'d']={'mean_pct':round(statistics.mean(vals),2) if vals else None,'median_pct':round(statistics.median(vals),2) if vals else None,'positive_pct':round(sum(v>0 for v in vals)/len(vals)*100,1) if vals else None}
 return out
print(json.dumps({'raw_n':len(events),'declustered':stats(cluster),'examples':cluster[-30:]},indent=2))

