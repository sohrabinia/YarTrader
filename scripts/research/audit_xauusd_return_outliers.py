import csv, math, json
from collections import deque
from pathlib import Path
p=Path(r"C:\Projects\YarTrader\runtime_logs\mt5_gold_history_full\M1.csv")
rows=deque(maxlen=250000)
with p.open("r",newline="",encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        try: rows.append((int(float(r["time"])),float(r["close"])))
        except (ValueError,TypeError,KeyError): pass
a=list(rows); changes=[]
for i in range(1,len(a)):
    ret=math.log(a[i][1]/a[i-1][1])
    changes.append((abs(ret),ret,a[i-1][0],a[i][0],a[i-1][1],a[i][1]))
changes.sort(reverse=True)
absr=sorted(x[0] for x in changes)
def q(pct): return absr[min(len(absr)-1,int(pct*len(absr)))]
print(json.dumps({"n":len(changes),"abs_return_quantiles":{"p99":q(.99),"p999":q(.999),"p9999":q(.9999)},
"largest_10":[{"abs_log_return":x[0],"log_return":x[1],"previous_time":x[2],"time":x[3],"previous_close":x[4],"close":x[5],"simple_pct":(x[5]/x[4]-1)*100} for x in changes[:10]]},indent=2))
