"""
YarTrader Timeframe Aggregator
===============================
Aggregates source M1 OHLCV candles strictly into target timeframe buckets:
M1, M5, M15, M30, H1, H4, D1.
Unknown timeframe raises ValueError (NO default fallback ratio).
Emits only complete buckets.
"""

import math
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

logger = logging.getLogger("TimeframeAggregator")


class TimeframeAggregator:
    """
    Strict Timeframe Aggregator for YarTrader.
    """

    SUPPORTED_TIMEFRAMES = {
        "M1": 1,
        "M5": 5,
        "M15": 15,
        "M30": 30,
        "H1": 60,
        "H4": 240,
        "D1": 1440,
    }

    @classmethod
    def get_ratio(cls, target_tf: str) -> int:
        tf_upper = target_tf.upper().strip()
        if tf_upper not in cls.SUPPORTED_TIMEFRAMES:
            raise ValueError(f"[TimeframeAggregator] Unknown or unsupported target timeframe: '{target_tf}'. Supported: {list(cls.SUPPORTED_TIMEFRAMES.keys())}")
        return cls.SUPPORTED_TIMEFRAMES[tf_upper]

    @classmethod
    def validate_candle(cls, c: Dict[str, Any], idx: int) -> Dict[str, Any]:
        if not isinstance(c, dict):
            raise ValueError(f"[TimeframeAggregator] Candle at index {idx} must be a dictionary.")

        ts_raw = c.get("time") or c.get("timestamp") or c.get("Timestamp")
        if ts_raw is None:
            raise ValueError(f"[TimeframeAggregator] Candle at index {idx} is missing timestamp.")

        if isinstance(ts_raw, (int, float)):
            ts_num = float(ts_raw)
            if not math.isfinite(ts_num) or ts_num <= 0:
                raise ValueError(f"[TimeframeAggregator] Candle at index {idx} has invalid timestamp: {ts_raw}")
            ts_val = int(ts_num)
        elif isinstance(ts_raw, str):
            try:
                if ts_raw.isdigit():
                    ts_val = int(ts_raw)
                else:
                    text = ts_raw.replace("Z", "+00:00")
                    ts_val = int(datetime.fromisoformat(text).timestamp())
            except Exception as err:
                raise ValueError(f"[TimeframeAggregator] Candle at index {idx} has unparseable string timestamp '{ts_raw}': {err}")
        elif isinstance(ts_raw, datetime):
            ts_val = int(ts_raw.timestamp())
        else:
            raise ValueError(f"[TimeframeAggregator] Candle at index {idx} has unsupported timestamp type: {type(ts_raw)}")

        open_val = float(c.get("open", c.get("Open", 0.0)))
        high_val = float(c.get("high", c.get("High", 0.0)))
        low_val = float(c.get("low", c.get("Low", 0.0)))
        close_val = float(c.get("close", c.get("Close", 0.0)))

        prices = [open_val, high_val, low_val, close_val]
        for p in prices:
            if p <= 0.0 or math.isnan(p) or math.isinf(p):
                raise ValueError(f"[TimeframeAggregator] Candle at index {idx} has non-positive or non-finite price: {p}")

        if high_val < max(open_val, close_val) or low_val > min(open_val, close_val) or high_val < low_val:
            raise ValueError(f"[TimeframeAggregator] Candle at index {idx} has invalid OHLC geometry (O={open_val}, H={high_val}, L={low_val}, C={close_val}).")

        vol_val = float(c.get("volume", c.get("Volume", c.get("tick_volume", 0.0))))
        if vol_val < 0.0 or math.isnan(vol_val) or math.isinf(vol_val):
            raise ValueError(f"[TimeframeAggregator] Candle at index {idx} has invalid volume: {vol_val}")

        return {
            "time": ts_val,
            "timestamp": str(ts_val),
            "open": open_val,
            "high": high_val,
            "low": low_val,
            "close": close_val,
            "volume": vol_val
        }

    @classmethod
    def aggregate_m1_candles(
        cls,
        m1_candles: List[Dict[str, Any]],
        target_timeframe: str = "H1"
    ) -> List[Dict[str, Any]]:
        """
        Aggregates M1 candles strictly into target_timeframe.
        Raises ValueError if target_timeframe is unknown or source candles are invalid.
        Emits only complete buckets where bucket bar count == ratio.
        """
        ratio = cls.get_ratio(target_timeframe)

        if not m1_candles:
            return []

        clean_candles = []
        for i, c in enumerate(m1_candles):
            validated = cls.validate_candle(c, i)
            clean_candles.append(validated)

        # Ensure candles are strictly sorted and increasing
        clean_candles.sort(key=lambda x: x["time"])
        for i in range(1, len(clean_candles)):
            if clean_candles[i]["time"] <= clean_candles[i - 1]["time"]:
                raise ValueError(f"[TimeframeAggregator] Source candles must be strictly increasing by timestamp ({clean_candles[i]['time']} <= {clean_candles[i-1]['time']}).")

        if len(clean_candles) < ratio:
            return []

        tf_seconds = ratio * 60
        buckets: Dict[int, List[Dict[str, Any]]] = {}

        for candle in clean_candles:
            ts = candle["time"]
            boundary_ts = ts - (ts % tf_seconds)
            if boundary_ts not in buckets:
                buckets[boundary_ts] = []
            buckets[boundary_ts].append(candle)

        aggregated_candles = []
        for boundary_ts in sorted(buckets.keys()):
            bucket = buckets[boundary_ts]

            # Emit ONLY complete buckets matching exact ratio
            if len(bucket) < ratio:
                continue

            open_price = bucket[0]["open"]
            close_price = bucket[-1]["close"]
            high_price = max(c["high"] for c in bucket)
            low_price = min(c["low"] for c in bucket)
            volume = sum(c["volume"] for c in bucket)

            aggregated_candles.append({
                "time": boundary_ts,
                "timestamp": str(boundary_ts),
                "open": round(open_price, 4),
                "high": round(high_price, 4),
                "low": round(low_price, 4),
                "close": round(close_price, 4),
                "volume": round(volume, 2),
                "tick_volume": int(volume)
            })

        return aggregated_candles
