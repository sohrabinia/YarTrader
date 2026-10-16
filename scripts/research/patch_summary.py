from pathlib import Path
p=Path(r"C:\Projects\YarTrader\scripts\research\summarize_base_study.py")
s=p.read_text(encoding="utf-8-sig")
s=s.replace('print(typ,"n",a["n"],"dep C/R",a["continuation_first_pct"],a["reversal_first_pct"],"proxy",a["barrier_proxy_R"],"| retest",rt["n"],rt["continuation_first_pct"],rt["reversal_first_pct"],rt["barrier_proxy_R"],"| last30",nlast.get("continuation_first_pct"),nlast.get("reversal_first_pct"),nlast.get("barrier_proxy_R"))','print(typ,"n",a["n"],"dep C/R",a["continuation_first_pct"],a["reversal_first_pct"],"proxy",a["barrier_proxy_R"],"| retest",rt["n"],rt["continuation_first_pct"],rt["reversal_first_pct"],rt["barrier_proxy_R"],"| last30 n",nlast.get("n"),"C/R",nlast.get("continuation_first_pct"),nlast.get("reversal_first_pct"),"proxy",nlast.get("barrier_proxy_R"))')
p.write_text(s,encoding="utf-8")
print("patched")
