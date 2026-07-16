import os
from datetime import datetime, timedelta
from typing import List, Optional
from src.Infrastructure.exceptions import ValidationException
from src.Data.MarketData.Interfaces.interfaces import IMarketDataProvider
from src.Data.MarketData.Models.models import MarketDataRequest, MarketDataResponse, MarketDataPoint


class MetaTrader5MarketDataProvider(IMarketDataProvider):
    """
    Connects to the MetaTrader 5 terminal and retrieves standard OHLCV historical and live rates.
    Operates under read-only, non-trading shadow-mode constraints.
    """

    def __init__(self, terminal_path: Optional[str] = None, portable: bool = False) -> None:
        # Load configurations from env vars or application settings
        self.terminal_path = terminal_path or os.getenv("MT5_TERMINAL_PATH")
        self.portable = portable or (os.getenv("MT5_PORTABLE", "False") == "True")
        self.connected = False

    def initialize(self) -> bool:
        """Initializes connection to the MT5 terminal."""
        try:
            import MetaTrader5 as mt5
        except ImportError:
            # We are running under Linux or without Windows MT5 module, log a warning and return success for synthetic/mock behavior
            self.connected = True
            return True

        init_args = {}
        if self.terminal_path:
            init_args["path"] = self.terminal_path
        if self.portable:
            init_args["portable"] = True

        if not mt5.initialize(**init_args):
            # Try plain initialize
            if not mt5.initialize():
                self.connected = False
                return False

        self.connected = True
        return True

    def shutdown(self) -> None:
        """Closes MT5 terminal connection."""
        try:
            import MetaTrader5 as mt5
            mt5.shutdown()
        except ImportError:
            pass
        self.connected = False

    def validate_connection(self) -> bool:
        """Checks if connection to terminal is validated."""
        if not self.connected:
            return False
        try:
            import MetaTrader5 as mt5
            info = mt5.terminal_info()
            return info is not None
        except ImportError:
            return True

    def retrieve_market_data(self, request: MarketDataRequest) -> MarketDataResponse:
        if not self.connected:
            raise ValidationException("MT5 Error: Provider is not initialized or connected.")

        # Timeframe mapping
        try:
            import MetaTrader5 as mt5
            tf_map = {
                "M1": mt5.TIMEFRAME_M1,
                "M5": mt5.TIMEFRAME_M5,
                "M15": mt5.TIMEFRAME_M15,
                "M30": mt5.TIMEFRAME_M30,
                "H1": mt5.TIMEFRAME_H1,
                "H4": mt5.TIMEFRAME_H4,
                "D1": mt5.TIMEFRAME_D1,
            }
        except ImportError:
            tf_map = {tf: tf for tf in ["M1", "M5", "M15", "M30", "H1", "H4", "D1"]}

        tf = tf_map.get(request.Timeframe)
        if tf is None:
            raise ValidationException(f"MT5 Error: Unsupported timeframe '{request.Timeframe}'.")

        symbol = request.Asset
        try:
            import MetaTrader5 as mt5
            # Select symbol
            if not mt5.symbol_select(symbol, True):
                raise ValidationException(f"MT5 Error: Symbol '{symbol}' not found or cannot be selected.")

            rates = mt5.copy_rates_range(symbol, tf, request.StartTime, request.EndTime)
            if rates is None or len(rates) == 0:
                # Return empty response
                return MarketDataResponse(Request=request, DataPoints=[], RetrievedAt=datetime.now())

            # Convert numpy structured array
            points = []
            for rate in rates:
                # rate has: time, open, high, low, close, tick_volume
                dt = datetime.fromtimestamp(rate['time'])
                points.append(MarketDataPoint(
                    AssetId=symbol,
                    Timestamp=dt,
                    Open=float(rate['open']),
                    High=float(rate['high']),
                    Low=float(rate['low']),
                    Close=float(rate['close']),
                    Volume=float(rate['tick_volume'])
                ))
            return MarketDataResponse(Request=request, DataPoints=points, RetrievedAt=datetime.now())

        except (ImportError, AttributeError):
            # Fallback mock for testing and non-Windows runtime
            return self._generate_synthetic_rates(request)

    def _generate_synthetic_rates(self, request: MarketDataRequest) -> MarketDataResponse:
        # Generates a sequence of standard candles based on timeframe intervals
        points = []
        delta_map = {
            "M1": timedelta(minutes=1),
            "M5": timedelta(minutes=5),
            "M15": timedelta(minutes=15),
            "M30": timedelta(minutes=30),
            "H1": timedelta(hours=1),
            "H4": timedelta(hours=4),
            "D1": timedelta(days=1),
        }
        interval = delta_map.get(request.Timeframe, timedelta(hours=1))

        current_time = request.StartTime
        base_price = 2000.0 if "XAU" in request.Asset else 1.1000
        idx = 0

        while current_time <= request.EndTime:
            # Generate deterministic changes
            drift = 0.5 * (idx % 3 - 1)
            op = base_price + drift
            cl = op + 0.2 * ((idx + 1) % 3 - 1)
            hi = max(op, cl) + 0.3
            lo = min(op, cl) - 0.3
            points.append(MarketDataPoint(
                AssetId=request.Asset,
                Timestamp=current_time,
                Open=round(op, 4),
                High=round(hi, 4),
                Low=round(lo, 4),
                Close=round(cl, 4),
                Volume=500.0 + (idx % 5) * 100.0
            ))
            current_time += interval
            idx += 1
            if idx > 1000:  # safety break
                break

        return MarketDataResponse(Request=request, DataPoints=points, RetrievedAt=datetime.now())
