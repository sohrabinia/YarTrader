from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger("TimeframeAggregator")

class TimeframeAggregator:
    """
    Deterministic M1 Timeframe Aggregation Utility for YarTrader.
    Aggregates authentic M1 OHLCV candles into higher target timeframes:
      - M5  = 5 x M1
      - M15 = 15 x M1
      - M30 = 30 x M1
      - H1  = 60 x M1
      - H4  = 240 x M1
      - D1  = 1440 x M1

    Rules:
      Open   = first M1 open
      High   = max M1 high
      Low    = min M1 low
      Close  = last M1 close
      Volume = sum of constituent M1 volume
      Time   = timestamp of the first M1 candle in the bucket
    """

    TIMEFRAME_RATIOS = {
        "M1": 1,
        "M5": 5,
        "M15": 15,
        "M30": 30,
        "H1": 60,
        "H4": 240,
        "D1": 1440,
    }

    @classmethod
    def aggregate_m1_candles(
        cls,
        m1_candles: List[Dict[str, Any]],
        target_timeframe: str = "H1"
    ) -> List[Dict[str, Any]]:
        """
        Aggregates M1 candles into target timeframe candles.
        Fails closed with empty list if M1 candles are insufficient.
        """
        tf_upper = target_timeframe.upper().strip()
        ratio = cls.TIMEFRAME_RATIOS.get(tf_upper, 60)

        if not m1_candles or len(m1_candles) < ratio:
            logger.warning(
                f"[TimeframeAggregator] Insufficient M1 candles ({len(m1_candles) if m1_candles else 0}) "
                f"for target timeframe {tf_upper} (requires at least {ratio} M1 bars)."
            )
            return []

        aggregated_candles = []
        num_m1 = len(m1_candles)

        # Slice M1 candles into buckets of size `ratio`
        for i in range(0, num_m1, ratio):
            bucket = m1_candles[i:i + ratio]
            if not bucket:
                continue

            open_price = float(bucket[0].get("open", bucket[0].get("Open", 0.0)))
            close_price = float(bucket[-1].get("close", bucket[-1].get("Close", 0.0)))
            high_price = max(float(c.get("high", c.get("High", 0.0))) for c in bucket)
            low_price = min(float(c.get("low", c.get("Low", 0.0))) for c in bucket)
            volume = sum(float(c.get("volume", c.get("Volume", c.get("tick_volume", 0.0)))) for c in bucket)
            timestamp = bucket[0].get("time", bucket[0].get("timestamp", bucket[0].get("Timestamp", 0)))

            aggregated_candles.append({
                "time": timestamp,
                "timestamp": str(timestamp),
                "open": round(open_price, 4),
                "high": round(high_price, 4),
                "low": round(low_price, 4),
                "close": round(close_price, 4),
                "volume": round(volume, 2),
                "tick_volume": int(volume)
            })

        return aggregated_candles
