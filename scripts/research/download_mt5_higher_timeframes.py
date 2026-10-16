from datetime import datetime, timezone
from pathlib import Path
import csv, json
import MetaTrader5 as mt5

ROOT = Path(r'C:\Projects\YarTrader')
OUT = ROOT / 'runtime_logs' / 'mt5_gold_history_full' / 'higher_timeframe_2010'
OUT.mkdir(parents=True, exist_ok=True)
start = datetime(2010, 1, 1, tzinfo=timezone.utc)
end = datetime.now(timezone.utc)
frames = [('D1', mt5.TIMEFRAME_D1), ('W1', mt5.TIMEFRAME_W1), ('MN1', mt5.TIMEFRAME_MN1)]
report = {'symbol': 'XAUUSD', 'requested_from_utc': start.isoformat(), 'requested_to_utc': end.isoformat(), 'results': []}
if not mt5.initialize():
    raise SystemExit(f'MT5 initialize failed: {mt5.last_error()}')
try:
    if not mt5.symbol_select('XAUUSD', True):
        raise SystemExit(f'Could not select XAUUSD: {mt5.last_error()}')
    for label, timeframe in frames:
        rates = mt5.copy_rates_range('XAUUSD', timeframe, start, end)
        item = {'timeframe': label, 'count': 0, 'file': None, 'first_utc': None, 'last_utc': None, 'error': None}
        if rates is None:
            item['error'] = str(mt5.last_error())
        elif len(rates) == 0:
            item['error'] = 'No bars returned'
        else:
            path = OUT / f'XAUUSD_{label}_from_2010.csv'
            names = list(rates.dtype.names)
            with path.open('w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(names + ['time_utc'])
                for rate in rates:
                    writer.writerow([rate[name].item() if hasattr(rate[name], 'item') else rate[name] for name in names] + [datetime.fromtimestamp(int(rate['time']), timezone.utc).isoformat()])
            item.update({'count': int(len(rates)), 'file': str(path), 'first_utc': datetime.fromtimestamp(int(rates[0]['time']), timezone.utc).isoformat(), 'last_utc': datetime.fromtimestamp(int(rates[-1]['time']), timezone.utc).isoformat()})
        report['results'].append(item)
finally:
    mt5.shutdown()
report_path = OUT / 'download_report.json'
report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
