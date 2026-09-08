import logging
from typing import Dict, Any, Optional

from src.Application.Services.backtest_service import BacktestService
from src.Application.Backtest.backtest_engine import (
    BacktestEngine,
    BacktestConfig,
    BacktestStrategyType,
    BacktestResult
)
from src.Application.Learning.learning_engine import (
    LearningEngine,
    LearningConfig,
    LearningDataset,
    LearningInsight
)
from src.Infrastructure.exceptions import ValidationException

logger = logging.getLogger(__name__)


class LearningService:
    """
    Application service that coordinates historical backtest evaluations via BacktestService
    and extracts deterministic statistical LearningInsights using LearningEngine.
    """
    def __init__(
        self,
        backtest_service: Optional[BacktestService] = None,
        engine: Optional[LearningEngine] = None
    ) -> None:
        self.backtest_service = backtest_service or BacktestService()
        self.engine = engine or LearningEngine()

    def analyze_historical_learning(
        self,
        symbol: str = "XAUUSD",
        interval: str = "M15",
        strategy: str = "TREND",
        limit: int = 100,
        min_sample_threshold: int = 10
    ) -> Dict[str, Any]:
        """
        Coordinates historical backtest evaluation retrieval, dataset extraction,
        and statistical insight aggregation for specified symbol, interval, and strategy.
        """
        if limit <= 0 or limit > 1000:
            raise ValidationException("limit must be between 1 and 1000 records.")

        strat_upper = strategy.strip().upper()
        try:
            strat_type = BacktestStrategyType(strat_upper)
        except ValueError:
            raise ValidationException(
                f"Invalid strategy type: '{strategy}'. Supported: {[s.value for s in BacktestStrategyType]}"
            )

        learning_config = LearningConfig(
            symbol=symbol,
            interval=interval,
            strategy_type=strat_type.value,
            min_sample_threshold=min_sample_threshold
        )
        learning_config.validate()

        bt_config = BacktestConfig(
            symbol=symbol,
            interval=interval,
            strategy_type=strat_type,
            min_history_bars=21
        )
        bt_config.validate()

        candles_hist = self.backtest_service.market_data_service.get_historical_candles(
            symbol=symbol,
            interval=interval,
            limit=limit
        )
        raw_candles = candles_hist.get("candles", [])

        from src.Data.MarketData.Models.models import MarketDataPoint
        from datetime import datetime

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
                AssetId=symbol,
                Timestamp=ts_obj,
                Open=float(c["open"]),
                High=float(c["high"]),
                Low=float(c["low"]),
                Close=float(c["close"]),
                Volume=float(c.get("volume", 0.0))
            )
            points.append(pt)

        bt_result: BacktestResult = self.backtest_service.engine.run_backtest(
            symbol=symbol,
            interval=interval,
            candles=points,
            config=bt_config
        )

        dataset: LearningDataset = self.engine.extract_dataset(bt_result)
        insight: LearningInsight = self.engine.generate_insight(dataset, learning_config)

        return insight.to_dict()
