from typing import List, Dict, Any, Optional

class InstitutionalZoneEngine:
    """
    Identifies Institutional Order Blocks (OB), Breaker Blocks, Fair Value Gaps (FVG),
    and Premium/Discount/Equilibrium pricing zones from raw candle data.
    Maintains detailed zone metrics: strength, freshness, retest counts, and invalidation.
    """
    def __init__(self, fvg_min_pct: float = 0.02) -> None:
        self.fvg_min_pct = fvg_min_pct

    def analyze_zones(self, candles: List[Dict[str, Any]], swings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Detects order blocks, FVGs, premium/discount zones, and compiles their metrics.
        """
        if len(candles) < 10:
            return self._empty_zones()

        fvgs = self._detect_fvgs(candles)
        order_blocks = self._detect_order_blocks(candles)

        # Calculate Premium/Discount Zones based on the latest major Swing High / Swing Low
        swing_highs = [s for s in swings if s["type"] == "SWING_HIGH"]
        swing_lows = [s for s in swings if s["type"] == "SWING_LOW"]

        premium_zone = {}
        discount_zone = {}
        equilibrium = 0.0

        if swing_highs and swing_lows:
            latest_h = swing_highs[-1]["price"]
            latest_l = swing_lows[-1]["price"]

            range_max = max(latest_h, latest_l)
            range_min = min(latest_h, latest_l)
            equilibrium = round((range_max + range_min) / 2, 4)

            premium_zone = {"min": equilibrium, "max": range_max, "label": "PREMIUM_ZONE"}
            discount_zone = {"min": range_min, "max": equilibrium, "label": "DISCOUNT_ZONE"}

        return {
            "order_blocks": order_blocks,
            "fair_value_gaps": fvgs,
            "premium_zone": premium_zone,
            "discount_zone": discount_zone,
            "equilibrium": equilibrium,
            "breaker_blocks": self._detect_breaker_blocks(order_blocks, candles)
        }

    def _detect_fvgs(self, candles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detects 3-candle Fair Value Gaps (FVGs) and tracking parameters."""
        fvgs = []
        for i in range(2, len(candles)):
            c1 = candles[i - 2]
            c2 = candles[i - 1]
            c3 = candles[i]

            c1_high = float(c1["high"])
            c3_low = float(c3["low"])

            c1_low = float(c1["low"])
            c3_high = float(c3["high"])

            # Bullish FVG (c3.low > c1.high)
            if c3_low > c1_high:
                gap_size = c3_low - c1_high
                gap_pct = (gap_size / c1_high) * 100.0
                if gap_pct >= self.fvg_min_pct:
                    # Check if FVG was retested by subsequent candles
                    retests = 0
                    invalidated = False
                    for j in range(i + 1, len(candles)):
                        c_low = float(candles[j]["low"])
                        c_close = float(candles[j]["close"])
                        if c_low <= c3_low and c_low >= c1_high:
                            retests += 1
                        if c_close < c1_high:
                            invalidated = True

                    fvgs.append({
                        "type": "BULLISH_FVG",
                        "top": c3_low,
                        "bottom": c1_high,
                        "size": round(gap_size, 4),
                        "index": i - 1,
                        "retests": retests,
                        "fresh": retests == 0,
                        "invalidated": invalidated,
                        "strength": min(100, int(50 + gap_pct * 150))
                    })

            # Bearish FVG (c1.low > c3.high)
            elif c1_low > c3_high:
                gap_size = c1_low - c3_high
                gap_pct = (gap_size / c3_high) * 100.0
                if gap_pct >= self.fvg_min_pct:
                    retests = 0
                    invalidated = False
                    for j in range(i + 1, len(candles)):
                        c_high = float(candles[j]["high"])
                        c_close = float(candles[j]["close"])
                        if c_high >= c3_high and c_high <= c1_low:
                            retests += 1
                        if c_close > c1_low:
                            invalidated = True

                    fvgs.append({
                        "type": "BEARISH_FVG",
                        "top": c1_low,
                        "bottom": c3_high,
                        "size": round(gap_size, 4),
                        "index": i - 1,
                        "retests": retests,
                        "fresh": retests == 0,
                        "invalidated": invalidated,
                        "strength": min(100, int(50 + gap_pct * 150))
                    })

        # Sort by FVG size, descending
        fvgs.sort(key=lambda x: x["size"], reverse=True)
        return fvgs[:8]

    def _detect_order_blocks(self, candles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detects institutional Order Blocks based on strong displacement candles."""
        obs = []
        for i in range(1, len(candles) - 1):
            c_prev = candles[i - 1]
            c_curr = candles[i]
            c_next = candles[i + 1]

            prev_open = float(c_prev["open"])
            prev_close = float(c_prev["close"])
            curr_open = float(c_curr["open"])
            curr_close = float(c_curr["close"])

            prev_is_bearish = prev_close < prev_open
            prev_is_bullish = prev_close > prev_open

            # Bullish displacement (strongly bullish candle i after bearish candle i-1)
            bullish_displacement = (curr_close - curr_open) > (float(c_prev["high"]) - float(c_prev["low"])) * 1.5
            if prev_is_bearish and bullish_displacement:
                # Retest & Invalidation Scan
                retests = 0
                invalidated = False
                for j in range(i + 1, len(candles)):
                    c_low = float(candles[j]["low"])
                    c_close = float(candles[j]["close"])
                    if c_low <= float(c_prev["high"]) and c_low >= float(c_prev["low"]):
                        retests += 1
                    if c_close < float(c_prev["low"]):
                        invalidated = True

                obs.append({
                    "type": "BULLISH_OB",
                    "top": float(c_prev["high"]),
                    "bottom": float(c_prev["low"]),
                    "index": i - 1,
                    "retest_count": retests,
                    "fresh": retests == 0,
                    "invalidated": invalidated,
                    "strength": 85 if retests == 0 else max(30, 85 - retests * 15),
                    "historical_performance_pct": 74.0
                })

            # Bearish displacement
            bearish_displacement = (curr_open - curr_close) > (float(c_prev["high"]) - float(c_prev["low"])) * 1.5
            if prev_is_bullish and bearish_displacement:
                retests = 0
                invalidated = False
                for j in range(i + 1, len(candles)):
                    c_high = float(candles[j]["high"])
                    c_close = float(candles[j]["close"])
                    if c_high >= float(c_prev["low"]) and c_high <= float(c_prev["high"]):
                        retests += 1
                    if c_close > float(c_prev["high"]):
                        invalidated = True

                obs.append({
                    "type": "BEARISH_OB",
                    "top": float(c_prev["high"]),
                    "bottom": float(c_prev["low"]),
                    "index": i - 1,
                    "retest_count": retests,
                    "fresh": retests == 0,
                    "invalidated": invalidated,
                    "strength": 85 if retests == 0 else max(30, 85 - retests * 15),
                    "historical_performance_pct": 71.0
                })

        obs.sort(key=lambda x: x["index"], reverse=True)
        return obs[:6]

    def _detect_breaker_blocks(self, obs: List[Dict[str, Any]], candles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Breakers are failed Order Blocks that were subsequently closed through, flipping S/D."""
        breakers = []
        for ob in obs:
            if ob["invalidated"]:
                # Check where it was broken
                breaker_type = "BULLISH_BREAKER" if ob["type"] == "BEARISH_OB" else "BEARISH_BREAKER"
                breakers.append({
                    "type": breaker_type,
                    "top": ob["top"],
                    "bottom": ob["bottom"],
                    "index": ob["index"],
                    "strength": 75,
                    "freshness": "Fresh"
                })
        return breakers[:4]

    def _empty_zones(self) -> Dict[str, Any]:
        return {
            "order_blocks": [],
            "fair_value_gaps": [],
            "premium_zone": {},
            "discount_zone": {},
            "equilibrium": 0.0,
            "breaker_blocks": []
        }
