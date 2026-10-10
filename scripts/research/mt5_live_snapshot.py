from datetime import datetime, timezone
import MetaTrader5 as mt5, json
if not mt5.initialize():
 print(json.dumps({'initialize':False,'error':mt5.last_error()})); raise SystemExit
try:
 ti=mt5.terminal_info(); ai=mt5.account_info(); si=mt5.symbol_info('XAUUSD'); tick=mt5.symbol_info_tick('XAUUSD')
 out={'initialize':True,'terminal':{'company':ti.company,'name':ti.name,'connected':ti.connected,'path':ti.path,'data_path':ti.data_path,'maxbars':ti.maxbars},'account':None if ai is None else {'server':ai.server,'company':ai.company,'currency':ai.currency,'trade_mode':ai.trade_mode},'symbol':None if si is None else {'name':si.name,'digits':si.digits,'point':si.point,'spread':si.spread,'trade_mode':si.trade_mode},'tick':None if tick is None else {'time_utc':datetime.fromtimestamp(tick.time,timezone.utc).isoformat(),'bid':tick.bid,'ask':tick.ask,'last':tick.last},'bars':{}}
 for name,tf in [('M1',mt5.TIMEFRAME_M1),('M15',mt5.TIMEFRAME_M15),('H1',mt5.TIMEFRAME_H1),('D1',mt5.TIMEFRAME_D1),('W1',mt5.TIMEFRAME_W1),('MN1',mt5.TIMEFRAME_MN1)]:
  rates=mt5.copy_rates_from_pos('XAUUSD',tf,0,3)
  out['bars'][name]=[] if rates is None else [{'time_utc':datetime.fromtimestamp(int(r['time']),timezone.utc).isoformat(),'open':float(r['open']),'high':float(r['high']),'low':float(r['low']),'close':float(r['close']),'tick_volume':int(r['tick_volume'])} for r in rates]
 print(json.dumps(out,indent=2))
finally: mt5.shutdown()
