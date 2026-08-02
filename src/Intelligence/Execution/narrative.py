from typing import List, Dict, Any, Optional

class MarketNarrativeEngine:
    """
    Analyzes pure chronological OHLCV candle streams to reconstruct structural market narratives.
    No lagging indicators are used. Implements Swing High/Low detection, Higher High, Higher Low,
    Lower High, Lower Low, Break of Structure (BoS), Change of Character (CHoCH), and Market State.
    """
    def __init__(self, swing_window: int = 2) -> None:
        self.swing_window = swing_window

    def analyze_narrative(self, candles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Processes candles to reconstruct a structured market narrative.
        """
        if len(candles) < 10:
            return self._empty_narrative()

        highs = [float(c["high"]) for c in candles]
        lows = [float(c["low"]) for c in candles]
        closes = [float(c["close"]) for c in candles]

        swing_highs = []
        swing_lows = []

        # 1. Detect Swing Highs and Lows
        for i in range(self.swing_window, len(candles) - self.swing_window):
            is_high = True
            is_low = True
            for w in range(1, self.swing_window + 1):
                if highs[i] <= highs[i - w] or highs[i] <= highs[i + w]:
                    is_high = False
                if lows[i] >= lows[i - w] or lows[i] >= lows[i + w]:
                    is_low = False

            if is_high:
                swing_highs.append({"index": i, "price": highs[i], "type": "SWING_HIGH"})
            if is_low:
                swing_lows.append({"index": i, "price": lows[i], "type": "SWING_LOW"})

        # 2. Reconstruct Structure Legs (HH, HL, LH, LL)
        structure_nodes = []
        all_swings = sorted(swing_highs + swing_lows, key=lambda x: x["index"])

        last_high = None
        last_low = None

        for swing in all_swings:
            node_type = "UNKNOWN"
            price = swing["price"]
            idx = swing["index"]

            if swing["type"] == "SWING_HIGH":
                if last_high is None:
                    node_type = "HIGH"
                elif price > last_high["price"]:
                    node_type = "HH"
                else:
                    node_type = "LH"
                last_high = {"price": price, "index": idx, "label": node_type}
            else:  # SWING_LOW
                if last_low is None:
                    node_type = "LOW"
                elif price < last_low["price"]:
                    node_type = "LL"
                else:
                    node_type = "HL"
                last_low = {"price": price, "index": idx, "label": node_type}

            structure_nodes.append({
                "index": idx,
                "price": price,
                "type": swing["type"],
                "label": node_type
            })

        # 3. Detect BoS (Break of Structure) & CHoCH (Change of Character) & MSS
        events = []
        trend = "NEUTRAL"
        # Analyze breaks
        for idx in range(1, len(all_swings)):
            prev = all_swings[idx - 1]
            curr = all_swings[idx]

            # If a High is broken by a subsequent close
            if prev["type"] == "SWING_HIGH":
                # Check closes after prev high
                for j in range(prev["index"] + 1, len(candles)):
                    if closes[j] > prev["price"]:
                        # Break confirmed
                        event_type = "BOS_UP" if trend == "BULLISH" else "CHOCH_UP"
                        events.append({
                            "index": j,
                            "type": event_type,
                            "price": closes[j],
                            "broken_level": prev["price"],
                            "description": f"Market closed above Swing High of {prev['price']}"
                        })
                        trend = "BULLISH"
                        break
            elif prev["type"] == "SWING_LOW":
                for j in range(prev["index"] + 1, len(candles)):
                    if closes[j] < prev["price"]:
                        event_type = "BOS_DOWN" if trend == "BEARISH" else "CHOCH_DOWN"
                        events.append({
                            "index": j,
                            "type": event_type,
                            "price": closes[j],
                            "broken_level": prev["price"],
                            "description": f"Market closed below Swing Low of {prev['price']}"
                        })
                        trend = "BEARISH"
                        break

        # 4. Market State (Compression, Expansion, Range, Accumulation, Distribution, Exhaustion)
        state = "RANGE"
        if len(structure_nodes) >= 4:
            labels = [n["label"] for n in structure_nodes[-4:]]
            if "HH" in labels and "HL" in labels:
                state = "EXPANSION_UP"
            elif "LH" in labels and "LL" in labels:
                state = "EXPANSION_DOWN"
            elif "LH" in labels and "HL" in labels:
                state = "COMPRESSION"
            elif "HH" in labels and "LL" in labels:
                state = "EXHAUSTION"

        latest_swing = all_swings[-1] if all_swings else {"price": closes[-1], "type": "NONE"}

        return {
            "state": state,
            "trend": trend,
            "swings": all_swings,
            "structure_nodes": structure_nodes,
            "events": events,
            "latest_swing": latest_swing,
            "summary": f"Market state detected as {state} with {trend} trend narrative."
        }

    def _empty_narrative(self) -> Dict[str, Any]:
        return {
            "state": "UNKNOWN",
            "trend": "NEUTRAL",
            "swings": [],
            "structure_nodes": [],
            "events": [],
            "latest_swing": {},
            "summary": "Insufficient candles to reconstruct narrative."
        }
