from typing import List, Dict, Any, Optional

class LiquidityIntelligenceEngine:
    """
    Detects market liquidity pools, sweeps, and stop hunts by analyzing OHLCV candle streams.
    Identifies Equal Highs (EQH), Equal Lows (EQL), Buy-Side/Sell-Side Liquidity (BSL/SSL),
    and Liquidity Sweeps where price briefly spikes past a high/low but closes inside.
    """
    def __init__(self, tolerance_pct: float = 0.08) -> None:
        self.tolerance_pct = tolerance_pct

    def analyze_liquidity(self, candles: List[Dict[str, Any]], swings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Processes candles and swing high/low points to locate liquidity pools and sweep events.
        """
        if len(candles) < 10:
            return self._empty_liquidity()

        # Find Equal Highs (EQH) and Equal Lows (EQL)
        eqhs = []
        eqls = []

        swing_highs = [s for s in swings if s["type"] == "SWING_HIGH"]
        swing_lows = [s for s in swings if s["type"] == "SWING_LOW"]

        # 1. Detect EQH
        for i in range(len(swing_highs)):
            for j in range(i + 1, len(swing_highs)):
                p1 = swing_highs[i]["price"]
                p2 = swing_highs[j]["price"]
                diff = abs(p1 - p2) / max(p1, p2) * 100.0
                if diff <= self.tolerance_pct:
                    eqhs.append({
                        "level": round((p1 + p2) / 2, 4),
                        "swings": [swing_highs[i], swing_highs[j]],
                        "strength": max(50, int(100 - diff * 400))
                    })

        # 2. Detect EQL
        for i in range(len(swing_lows)):
            for j in range(i + 1, len(swing_lows)):
                p1 = swing_lows[i]["price"]
                p2 = swing_lows[j]["price"]
                diff = abs(p1 - p2) / max(p1, p2) * 100.0
                if diff <= self.tolerance_pct:
                    eqls.append({
                        "level": round((p1 + p2) / 2, 4),
                        "swings": [swing_lows[i], swing_lows[j]],
                        "strength": max(50, int(100 - diff * 400))
                    })

        # 3. Detect Sweeps / Stop Hunts
        sweeps = []
        for eqh in eqhs:
            lvl = eqh["level"]
            max_idx = max(s["index"] for s in eqh["swings"])
            # Scan candles after the second swing point for a sweep
            for idx in range(max_idx + 1, len(candles)):
                c = candles[idx]
                # High pierced the level, but close is below it (wick rejection)
                if float(c["high"]) > lvl and float(c["close"]) < lvl:
                    sweeps.append({
                        "index": idx,
                        "type": "BUY_SIDE_SWEEP",
                        "level": lvl,
                        "pierced_price": float(c["high"]),
                        "strength": eqh["strength"],
                        "description": f"Price swept Buy-Side Liquidity pool at {lvl} with high of {c['high']}"
                    })

        for eql in eqls:
            lvl = eql["level"]
            max_idx = max(s["index"] for s in eql["swings"])
            for idx in range(max_idx + 1, len(candles)):
                c = candles[idx]
                if float(c["low"]) < lvl and float(c["close"]) > lvl:
                    sweeps.append({
                        "index": idx,
                        "type": "SELL_SIDE_SWEEP",
                        "level": lvl,
                        "pierced_price": float(c["low"]),
                        "strength": eql["strength"],
                        "description": f"Price swept Sell-Side Liquidity pool at {lvl} with low of {c['low']}"
                    })

        # 4. Map active liquidity levels (resting BSL and SSL)
        bsl_levels = [{"level": eq["level"], "strength": eq["strength"]} for eq in eqhs]
        ssl_levels = [{"level": eq["level"], "strength": eq["strength"]} for eq in eqls]

        # Add major un-swept swings as generic liquidity
        for s in swing_highs[-3:]:
            # if no candle closed above it yet, it has resting BSL
            swept = False
            for c in candles[s["index"] + 1:]:
                if float(c["close"]) > s["price"]:
                    swept = True
                    break
            if not swept:
                bsl_levels.append({"level": s["price"], "strength": 70})

        for s in swing_lows[-3:]:
            swept = False
            for c in candles[s["index"] + 1:]:
                if float(c["close"]) < s["price"]:
                    swept = True
                    break
            if not swept:
                ssl_levels.append({"level": s["price"], "strength": 70})

        # Sort BSL descending, SSL ascending
        bsl_levels.sort(key=lambda x: x["level"], reverse=True)
        ssl_levels.sort(key=lambda x: x["level"])

        latest_sweep = sweeps[-1] if sweeps else None

        return {
            "equal_highs": eqhs,
            "equal_lows": eqls,
            "sweeps": sweeps,
            "latest_sweep": latest_sweep,
            "resting_bsl": bsl_levels,
            "resting_ssl": ssl_levels,
            "voids": self._detect_voids(candles)
        }

    def _detect_voids(self, candles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detects high-momentum candles forming a Liquidity Void/Imbalance."""
        voids = []
        for i in range(2, len(candles)):
            c1 = candles[i - 2]
            c2 = candles[i - 1]
            c3 = candles[i]

            # High momentum bullish bar causing void between c1.high and c3.low
            if float(c3["low"]) > float(c1["high"]):
                voids.append({
                    "type": "LIQUIDITY_VOID_BULLISH",
                    "start": float(c1["high"]),
                    "end": float(c3["low"]),
                    "range": round(float(c3["low"]) - float(c1["high"]), 4),
                    "rebalanced": False
                })
            # Bullish fill/rebalance check: has a subsequent candle low breached the void?
            elif float(c3["high"]) < float(c1["low"]):
                voids.append({
                    "type": "LIQUIDITY_VOID_BEARISH",
                    "start": float(c3["high"]),
                    "end": float(c1["low"]),
                    "range": round(float(c1["low"]) - float(c3["high"]), 4),
                    "rebalanced": False
                })

        return voids[:5]  # limit to top 5 voids

    def _empty_liquidity(self) -> Dict[str, Any]:
        return {
            "equal_highs": [],
            "equal_lows": [],
            "sweeps": [],
            "latest_sweep": None,
            "resting_bsl": [],
            "resting_ssl": [],
            "voids": []
        }
