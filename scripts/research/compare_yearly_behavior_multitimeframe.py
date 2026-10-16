import csv,json,datetime
from pathlib import Path
ROOT=Path(r'C:\Projects\YarTrader'); DATA=ROOT/'runtime_logs'/'mt5_gold_history_full'
TFS={'M1':100800,'M5':20160,'M15':6720,'M30':3360,'H1':1680,'H4':420,'D1':252,'W1':52,'MN1':12}
def dt(ts): return datetime.datetime.fromtimestamp(ts,datetime.timezone.utc)
def read(tf):
 rows=[]
 with (DATA/f'{tf}.csv').open('r',newline='',encoding='utf-8-sig') as f:
  for r in csv.DictReader(f):
   try:
    t=int(float(r['time']));o=float(r['open']);h=float(r['high']);l=float(r['low']);c=float(r['close'])
    if t>0 and min(o,h,l,c)>0 and h>=max(o,l,c) and l<=min(o,h,c):rows.append((t,o,h,l,c))
   except:pass
 rows.sort(key=lambda x:x[0]);return list({r[0]:r for r in rows}.values())
report={'status':'DESCRIPTIVE_ONLY','method':'Annual close position; month-end close position within trailing ~1-year range; quarter close position within quarter range.','timeframes':{}};summary={}
for tf,lb in TFS.items():
 rows=read(tf);years={}
 for y in sorted(set(dt(r[0]).year for r in rows)):
  a=[r for r in rows if dt(r[0]).year==y]
  if len(a)<20:continue
  hi=max(r[2] for r in a);lo=min(r[3] for r in a);cl=a[-1][4];op=a[0][1]
  years[str(y)]={'bars':len(a),'open':round(op,2),'high':round(hi,2),'low':round(lo,2),'close':round(cl,2),'return_pct':round((cl/op-1)*100,2),'close_pos_pct':round((cl-lo)/(hi-lo)*100,1) if hi>lo else None}
 groups={}
 for i,r in enumerate(rows):
  d=dt(r[0]);groups.setdefault((d.year,d.month),[]).append(i)
 monthly=[]
 for (y,m),ix in groups.items():
  i=ix[-1]
  if i+1<lb:continue
  w=rows[max(0,i-lb+1):i+1];hi=max(x[2] for x in w);lo=min(x[3] for x in w);cl=rows[i][4]
  if hi>lo:monthly.append({'date':f'{y}-{m:02d}','close':round(cl,2),'trailing_1y_pos_pct':round((cl-lo)/(hi-lo)*100,1),'high':round(hi,2),'low':round(lo,2)})
 qgroups={}
 for i,r in enumerate(rows):
  d=dt(r[0]);q=(d.month-1)//3+1;qgroups.setdefault((d.year,q),[]).append(i)
 quarterly=[]
 for (y,q),ix in qgroups.items():
  a=[rows[i] for i in ix]
  if len(a)<3:continue
  hi=max(x[2] for x in a);lo=min(x[3] for x in a);cl=a[-1][4]
  quarterly.append({'quarter':f'{y}-Q{q}','close':round(cl,2),'quarter_range_pos_pct':round((cl-lo)/(hi-lo)*100,1) if hi>lo else None,'high':round(hi,2),'low':round(lo,2)})
 info={'bars':len(rows),'start':dt(rows[0][0]).isoformat() if rows else None,'end':dt(rows[-1][0]).isoformat() if rows else None,'annual':{y:v for y,v in years.items() if int(y)>=2017},'month_end_trailing_1y_position':monthly[-60:],'quarter_range_position':quarterly[-24:]}
 report['timeframes'][tf]=info
 summary[tf]={'bars':len(rows),'start':info['start'],'end':info['end'],'2025_annual':years.get('2025'),'2026_annual_partial':years.get('2026'),'recent_monthly_1y_pos':[x for x in monthly if x['date']>='2025-10'][-8:]}
report['summary']=summary
out=DATA/'multitimeframe_yearly_behavior_comparison_20261010.json';out.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'output':str(out),'summary':summary},indent=2))

