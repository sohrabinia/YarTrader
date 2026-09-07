import logging
from typing import Dict, Any, Optional
from datetime import datetime
from src.Application.Services.market_data_service import MarketDataService
from src.Application.Strategy.trend_strategy import TrendStrategyEngine, TrendConfig, TrendSignalType, TrendStrategyResult
from src.Data.MarketData.Models.models import MarketDataPoint
from src.Infrastructure.exceptions import ValidationException

logger = logging.getLogger(__name__)

class TrendStrategyService:
    """
    Application service wrapping TrendStrategyEngine. Coordinates provider-independent
    market data retrieval via MarketDataService and evaluates deterministic trend signals.
    """
    def __init__(
        self,
        market_data_service: Optional[MarketDataService] = None,
        engine: Optional[TrendStrategyEngine] = None
    ) -> None:
        self.market_data_service = market_data_service or MarketDataService()
        self.engine = engine or TrendStrategyEngine()

    def evaluate_symbol_trend(
        self,
        symbol: str = "XAUUSD",
        interval: str = "M15",
        fast_period: int = 5,
        slow_period: int = 20,
        minimum_trend_strength: float = 0.5
    ) -> Dict[str, Any]:
        """
        Retrieves historical market data for symbol/interval, maps data points, and computes trend strategy result.
        """
        config = TrendConfig(
            fast_period=fast_period,
            slow_period=slow_period,
            minimum_trend_strength=minimum_trend_strength
        )
        config.validate()

        limit = config.slow_period + 10
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

        eval_res: TrendStrategyResult = self.engine.evaluate(
            symbol=clean_symbol,
            interval=clean_interval,
            candles=points,
            config=config
        )

        return eval_res.to_dict()
