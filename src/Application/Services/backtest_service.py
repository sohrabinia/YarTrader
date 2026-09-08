import logging
from typing import Dict, Any, Optional
from datetime import datetime
from src.Application.Services.market_data_service import MarketDataService
from src.Application.Backtest.backtest_engine import (
    BacktestEngine,
    BacktestConfig,
    BacktestStrategyType,
    BacktestResult
)
from src.Data.MarketData.Models.models import MarketDataPoint
from src.Infrastructure.exceptions import ValidationException

logger = logging.getLogger(__name__)


class BacktestService:
    """
    Application service that coordinates provider-independent market data retrieval
    via MarketDataService and executes walk-forward historical strategy backtests
    using BacktestEngine.
    """
    def __init__(
        self,
        market_data_service: Optional[MarketDataService] = None,
        engine: Optional[BacktestEngine] = None
    ) -> None:
        self.market_data_service = market_data_service or MarketDataService()
        self.engine = engine or BacktestEngine()

    def run_historical_backtest(
        self,
        symbol: str = "XAUUSD",
        interval: str = "M15",
        strategy: str = "TREND",
        limit: int = 100,
        min_history_bars: int = 21
    ) -> Dict[str, Any]:
        """
        Retrieves historical market data, maps data points, validates parameter boundaries,
        and executes deterministic walk-forward backtest simulation.
        """
        if limit <= 0 or limit > 1000:
            raise ValidationException("limit must be between 1 and 1000 records.")

        strat_upper = strategy.strip().upper()
        try:
            strat_type = BacktestStrategyType(strat_upper)
        except ValueError:
            raise ValidationException(f"Invalid backtest strategy type: '{strategy}'. Supported: {[s.value for s in BacktestStrategyType]}")

        config = BacktestConfig(
            symbol=symbol,
            interval=interval,
            strategy_type=strat_type,
            min_history_bars=min_history_bars
        )
        config.validate()

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

        result: BacktestResult = self.engine.run_backtest(
            symbol=clean_symbol,
            interval=clean_interval,
            candles=points,
            config=config
        )

        return result.to_dict()
