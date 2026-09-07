import logging
from typing import Dict, Any, Optional
from datetime import datetime
from src.Application.Services.market_data_service import MarketDataService
from src.Application.Strategy.range_strategy import RangeStrategyEngine, RangeConfig, RangeSignalType, RangeStrategyResult
from src.Data.MarketData.Models.models import MarketDataPoint
from src.Infrastructure.exceptions import ValidationException

logger = logging.getLogger(__name__)

class RangeStrategyService:
    """
    Application service wrapping RangeStrategyEngine. Coordinates provider-independent
    market data retrieval via MarketDataService and evaluates deterministic range signals.
    """
    def __init__(
        self,
        market_data_service: Optional[MarketDataService] = None,
        engine: Optional[RangeStrategyEngine] = None
    ) -> None:
        self.market_data_service = market_data_service or MarketDataService()
        self.engine = engine or RangeStrategyEngine()

    def evaluate_symbol_range(
        self,
        symbol: str = "XAUUSD",
        interval: str = "M15",
        lookback_period: int = 20,
        max_normalized_range: float = 4.5,
        min_range_width: float = 0.5
    ) -> Dict[str, Any]:
        """
        Retrieves historical market data for symbol/interval, maps data points, and computes range strategy result.
        """
        config = RangeConfig(
            lookback_period=lookback_period,
            max_normalized_range=max_normalized_range,
            min_range_width=min_range_width
        )
        config.validate()

        limit = config.lookback_period + 10
        hist = self.market_data_service.get_historical_candles(
            symbol=symbol,
            interval=interval,
            limit=limit
        )

        raw_candles = hist.get("candles", [])
        clean_symbol = hist.get("symbol", symbol)
        clean_interval = hist.get("interval", interval)

        points = []
        for c in raw_candles:
            ts_val = c["timestamp"]
            if isinstance(ts_val, str):
                try:
                    ts_obj = datetime.fromisoformat(ts_val.replace("Z", "+00:00"))
                except Exception:
                    ts_obj = datetime.now()
            else:
                ts_obj = ts_val

            pt = MarketDataPoint(
                AssetId=clean_symbol,
                Timestamp=ts_obj,
                Open=float(c["open"]),
                High=float(c["high"]),
                Low=float(c["low"]),
                Close=float(c["close"]),
                Volume=float(c.get("volume", 0.0))
            )
            points.append(pt)

        eval_res: RangeStrategyResult = self.engine.evaluate(
            symbol=clean_symbol,
            interval=clean_interval,
            candles=points,
            config=config
        )

        return eval_res.to_dict()
