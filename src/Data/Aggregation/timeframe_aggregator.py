import math
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

class StrictTimeframeAggregator:
    """
    Strict Timeframe Aggregator for YarTrader.

    Invariants:
    1. Unknown timeframes are strictly rejected (no default fallback ratio).
    2. Invalid timestamps (None, <= 0, non-finite) cause bar rejection (never converted to 0).
    3. Missing/malformed/NaN/Inf OHLC prices are strictly rejected.
    4. Target bucket aggregation requires complete source bar count (M5=5, M15=15, H1=60, H4=240).
    """

    ALLOWED_TIMEFRAMES: Dict[str, int] = {
        "M1": 1,
        "M5": 5,
        "M15": 15,
        "M30": 30,
        "H1": 60,
        "H4": 240,
        "D1": 1440,
    }

    @classmethod
    def get_timeframe_ratio(cls, source_tf: str, target_tf: str) -> int:
        """Returns exact source-to-target bar ratio. Raises ValueError for unknown timeframes."""
        src_upper = str(source_tf).upper()
        tgt_upper = str(target_tf).upper()

        if src_upper not in cls.ALLOWED_TIMEFRAMES:
            raise ValueError(f"Unknown source timeframe: '{source_tf}'")
        if tgt_upper not in cls.ALLOWED_TIMEFRAMES:
            raise ValueError(f"Unknown target timeframe: '{target_tf}'")

        src_min = cls.ALLOWED_TIMEFRAMES[src_upper]
        tgt_min = cls.ALLOWED_TIMEFRAMES[tgt_upper]

        if tgt_min < src_min or tgt_min % src_min != 0:
            raise ValueError(f"Invalid timeframe aggregation pair: {source_tf} -> {target_tf}")

        return tgt_min // src_min

    @classmethod
    def validate_candle(cls, candle: Dict[str, Any]) -> Tuple[datetime, float, float, float, float, float]:
        """Validates OHLC candle values strictly. Raises ValueError if malformed."""
        if not isinstance(candle, dict):
            raise ValueError("Candle must be a dictionary.")

        ts_raw = candle.get("time") or candle.get("timestamp")
        if ts_raw is None:
            raise ValueError("Candle timestamp is missing.")

        if isinstance(ts_raw, (int, float)):
            ts_val = float(ts_raw)
            if not math.isfinite(ts_val) or ts_val <= 0:
                raise ValueError(f"Invalid timestamp value: {ts_raw}")
            dt = datetime.fromtimestamp(ts_val, tz=timezone.utc)
        elif isinstance(ts_raw, datetime):
            dt = ts_raw if ts_raw.tzinfo else ts_raw.replace(tzinfo=timezone.utc)
        elif isinstance(ts_raw, str):
            try:
                dt = datetime.fromisoformat(ts_raw)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
            except Exception:
                raise ValueError(f"Unparseable ISO timestamp string: {ts_raw}")
        else:
            raise ValueError(f"Unsupported timestamp type: {type(ts_raw)}")

        for key in ["open", "high", "low", "close"]:
            val = candle.get(key)
            if val is None or isinstance(val, bool) or not isinstance(val, (int, float)):
                raise ValueError(f"Candle key '{key}' missing or invalid.")
            f_val = float(val)
            if not math.isfinite(f_val) or f_val <= 0:
                raise ValueError(f"Candle key '{key}' is non-finite or <= 0: {f_val}")

        o = float(candle["open"])
        h = float(candle["high"])
        l = float(candle["low"])
        c = float(candle["close"])
        v = float(candle.get("volume", 0.0))

        if h < l or h < o or h < c or l > o or l > c:
            raise ValueError(f"Invalid OHLC geometry: O={o}, H={h}, L={l}, C={c}")

        return dt, o, h, l, c, v

    @classmethod
    def aggregate_candles(
        cls,
        source_candles: List[Dict[str, Any]],
        source_tf: str = "M1",
        target_tf: str = "M5"
    ) -> List[Dict[str, Any]]:
        """
        Aggregates source candles into target timeframe candles.
        Only complete buckets matching exact ratio are produced.
        """
        ratio = cls.get_timeframe_ratio(source_tf, target_tf)
        valid_source: List[Tuple[datetime, float, float, float, float, float]] = []

        for c in source_candles:
            try:
                valid_source.append(cls.validate_candle(c))
            except ValueError as ve:
                raise ValueError(f"Candle validation failed during aggregation: {ve}")

        aggregated: List[Dict[str, Any]] = []
        n_source = len(valid_source)

        for i in range(0, n_source - ratio + 1, ratio):
            bucket = valid_source[i:i + ratio]
            if len(bucket) < ratio:
                continue

            open_time, b_open, b_high, b_low, _, _ = bucket[0]
            b_close = bucket[-1][4]
            max_h = max(b[2] for b in bucket)
            min_l = min(b[3] for b in bucket)
            tot_v = sum(b[5] for b in bucket)

            aggregated.append({
                "time": int(open_time.timestamp()),
                "timestamp_iso": open_time.isoformat(),
                "open": b_open,
                "high": max_h,
                "low": min_l,
                "close": b_close,
                "volume": tot_v,
                "timeframe": target_tf.upper(),
                "candle_count": ratio
            })

        return aggregated
