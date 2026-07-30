import sys
from unittest.mock import MagicMock

# Setup global mock for MetaTrader5 if not available, so that all tests can run and import it cleanly
try:
    import MetaTrader5
except ImportError:
    mock_mt5 = MagicMock()
    mock_mt5.initialize.return_value = True

    mock_term_info = MagicMock()
    mock_term_info.connected = True
    mock_mt5.terminal_info.return_value = mock_term_info

    mock_mt5.symbols_get.return_value = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY"]

    def mock_symbol_info(symbol):
        if symbol in ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY"]:
            mock_info = MagicMock()
            mock_info.name = symbol
            return mock_info
        return None
    mock_mt5.symbol_info.side_effect = mock_symbol_info

    mock_mt5.account_info.return_value = None
    mock_mt5.last_error.return_value = (0, "Success")

    mock_mt5.TIMEFRAME_M1 = 1
    mock_mt5.TIMEFRAME_M5 = 5
    mock_mt5.TIMEFRAME_M15 = 15
    mock_mt5.TIMEFRAME_M30 = 30
    mock_mt5.TIMEFRAME_H1 = 16385
    mock_mt5.TIMEFRAME_H4 = 16388
    mock_mt5.TIMEFRAME_D1 = 16408

    def mock_copy_rates_range(symbol, timeframe, date_from, date_to):
        from datetime import timedelta
        base_price = 1.1000 if "JPY" not in symbol else 145.0
        if "XAU" in symbol:
            base_price = 1800.0
        increment = 0.0001 if "JPY" not in symbol and "XAU" not in symbol else 0.01

        rates = []
        curr = date_from
        for i in range(10):
            if curr > date_to:
                break
            rates.append({
                "time": int(curr.timestamp()),
                "open": base_price + i * increment,
                "high": base_price + (i + 2) * increment,
                "low": base_price + (i - 1) * increment,
                "close": base_price + (i + 1) * increment,
                "tick_volume": 150.0 + i * 10
            })
            curr += timedelta(minutes=15)
        return rates

    mock_mt5.copy_rates_range.side_effect = mock_copy_rates_range
    sys.modules["MetaTrader5"] = mock_mt5
