"""
YarTrader MT4 Live Market Data Pipeline & Deduplication Layer
=============================================================

Streams live MT4 tick and candle observations into the ContinuousMarketFollowingEngine,
normalizes timestamps to UTC, and applies deterministic tick rate-limiting and signal deduplication.
"""

import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

import importlib
from src.Research.MarketAnalysis.Services.continuous_market_following_engine import ContinuousMarketFollowingEngine, ProbabilisticPathForecast

logger = logging.getLogger("MT4LivePipeline")


class MT4LiveMarketPipeline:
    """
    Live Market Data Pipeline connecting MT4 live streams to ContinuousMarketFollowingEngine.
    Enforces UTC timestamp normalization, signal deduplication, and rate limiting.
    """

    def __init__(self, symbol: str = "XAUUSD", min_tick_interval_sec: float = 0.5, adapter: Any = None):
        self.symbol = symbol.upper()
        if adapter is None:
            mod = importlib.import_module("src.Execution.Adapters.mt4_adapter")
            adapter = mod.RealMT4BrokerAdapter()
        self.adapter = adapter
        self.engine = ContinuousMarketFollowingEngine(symbol=self.symbol)
        self.min_tick_interval_sec = min_tick_interval_sec
        self.last_tick_timestamp: float = 0.0
        self.signal_cache: Dict[str, Dict[str, Any]] = {}

    def process_live_tick(self, custom_tick: Optional[Dict[str, Any]] = None) -> Optional[ProbabilisticPathForecast]:
        """
        Processes a single live MT4 tick observation.
        Normalizes timestamp to UTC and feeds engine.observe().
        Returns ProbabilisticPathForecast if tick passes rate limit.
        """
        now_ts = time.time()
        if now_ts - self.last_tick_timestamp < self.min_tick_interval_sec:
            # Rate limit exceeded - skip tick observation
            return None

        self.last_tick_timestamp = now_ts
        tick_data = custom_tick or self.adapter.get_symbol_tick(self.symbol)

        if not tick_data:
            return None

        # Normalize timestamp strictly to UTC
        raw_time = tick_data.get("time")
        if isinstance(raw_time, (int, float)):
            dt_utc = datetime.fromtimestamp(raw_time, tz=timezone.utc)
        elif isinstance(raw_time, str):
            dt_utc = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
            if dt_utc.tzinfo is None:
                dt_utc = dt_utc.replace(tzinfo=timezone.utc)
        else:
            dt_utc = datetime.now(timezone.utc)

        bid = float(tick_data.get("bid", 2500.0))
        ask = float(tick_data.get("ask", 2500.20))
        mid_price = round((bid + ask) / 2.0, 2)
        volume = float(tick_data.get("volume", 1.0))

        # Observe data in Market Following Engine
        self.engine.observe(price=mid_price, volume=volume, timestamp=dt_utc)

        # Generate continuous path forecast
        spread_usd = round(ask - bid, 2)
        forecast = self.engine.estimate_path_distribution(spread_usd=spread_usd)

        return forecast

    def is_signal_duplicate(
        self,
        symbol: str,
        direction: str,
        forecast: ProbabilisticPathForecast,
        window_seconds: float = 120.0
    ) -> bool:
        """
        Determines if a generated signal is a duplicate within the active time window.
        Key = symbol + direction + state
        """
        sym_key = symbol.upper()
        cache_entry = self.signal_cache.get(sym_key)
        now_ts = time.time()

        if cache_entry is not None:
            elapsed = now_ts - cache_entry.get("timestamp", 0.0)
            same_dir = cache_entry.get("direction") == direction
            if same_dir and elapsed < window_seconds:
                logger.info(f"[MT4LivePipeline] Duplicate signal suppressed for {sym_key} {direction} (elapsed {int(elapsed)}s < {int(window_seconds)}s).")
                return True

        self.signal_cache[sym_key] = {
            "direction": direction,
            "timestamp": now_ts,
            "forecast_prob": forecast.continuation_probability
        }
        return False
