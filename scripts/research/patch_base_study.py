from pathlib import Path
p=Path(r"C:\Projects\YarTrader\scripts\research\xauusd_base_pattern_multitimeframe_study.py")
s=p.read_text(encoding="utf-8-sig")
s=s.replace('    for fn in FILES:\n      p=ROOT/fn', '    if OUT.exists():\n      try: result=json.loads(OUT.read_text(encoding="utf-8"))\n      except Exception: pass\n    for fn in FILES:\n      if fn[:-4] in result["timeframes"]: continue\n      p=ROOT/fn')
s=s.replace('scan_step=10 if fn=="M1.csv" else (5 if fn=="M5.csv" else (3 if fn in ("M15.csv","H1.csv","H4.csv") else 1))','scan_step=20 if fn=="M1.csv" else (10 if fn in ("M5.csv","M15.csv") else (3 if fn in ("H1.csv","H4.csv") else 1))')
s=s.replace('H4/H1/M15 scan uses stride 3, M5 stride 5 and M1 stride 10','H4/H1 scan uses stride 3, M15/M5 stride 10 and M1 stride 20')
p.write_text(s,encoding="utf-8")
print("patched resumable scan", 'if OUT.exists()' in s, 'scan_step=20' in s)
