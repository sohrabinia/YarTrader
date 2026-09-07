import logging
from typing import Dict, Any, Optional
from src.Application.Services.market_data_service import MarketDataService
from src.Application.Strategy.spike_strategy import SpikeStrategyEngine, SpikeConfig, SpikeSignalType, SpikeStrategyResult
from src.Data.MarketData.Models.models import MarketDataPoint
from src.Infrastructure.exceptions import ValidationException

logger = logging.getLogger(__name__)

class SpikeStrategyService:
    """
    Application service wrapping SpikeStrategyEngine. Coordinates provider-independent
    market data retrieval via MarketDataService and evaluates deterministic spike signals.
    """
    def __init__(
        self,
        market_data_service: Optional[MarketDataService] = None,
        engine: Optional[SpikeStrategyEngine] = None
    ) -> None:
        self.market_data_service = market_data_service or MarketDataService()
        self.engine = engine or SpikeStrategyEngine()

    def evaluate_symbol_spike(
        self,
        symbol: str = "XAUUSD",
        interval: str = "M15",
        lookback_period: int = 14,
        spike_threshold: float = 2.5,
        min_movement: float = 1.0
    ) -> Dict[str, Any]:
        """
        Retrieves historical market data for symbol/interval, maps data points, and computes spike strategy result.
        """
        config = SpikeConfig(
            lookback_period=lookback_period,
            spike_threshold=spike_threshold,
            min_movement=min_movement
        )
        config.validate()

        # Fetch enough historical candles to cover lookback_period + margin
        limit = config.lookback_period + 10
        hist = self.market_data_service.get_historical_candles(
            symbol=symbol,
            interval=interval,
            limit=limit
        )

        raw_candles = hist.get("candles", [])
        clean_symbol = hist.get("symbol", symbol)
        clean_interval = hist.get("interval", interval)

        # Map dict candles back to MarketDataPoints for engine evaluation
        points = []
        for c in raw_candles:
            from datetime import datetime
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

        eval_res: SpikeStrategyResult = self.engine.evaluate(
            symbol=clean_symbol,
            interval=clean_interval,
            candles=points,
            config=config
        )

        return eval_res.to_dict()
