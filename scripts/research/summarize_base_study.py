import json
from pathlib import Path
p=Path(r"C:\Projects\YarTrader\runtime_logs\mt5_gold_history_full\xauusd_base_pattern_multitimeframe_study_20261010.json")
x=json.loads(p.read_text(encoding="utf-8"))
for tf,v in x["timeframes"].items():
 print("\n",tf,"bars",v["bars"],"events",v["detected_declustered"])
 for typ,z in v["patterns"].items():
  a=z["departure"]
  rt=v["first_retest"][typ]["reaction"]
  nlast=v["chronological_stability"]["last_30pct"][typ]["departure"]
  print(typ,"n",a["n"],"dep C/R",a["continuation_first_pct"],a["reversal_first_pct"],"proxy",a["barrier_proxy_R"],"| retest",rt["n"],rt["continuation_first_pct"],rt["reversal_first_pct"],rt["barrier_proxy_R"],"| last30 n",nlast.get("n"),"C/R",nlast.get("continuation_first_pct"),nlast.get("reversal_first_pct"),"proxy",nlast.get("barrier_proxy_R"))
