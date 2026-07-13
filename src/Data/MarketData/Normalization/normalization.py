from typing import Any, List, Dict, Optional
from datetime import datetime
from src.Data.MarketData.Interfaces.interfaces import IMarketDataNormalizer
from src.Data.MarketData.Models.models import MarketDataPoint

class MarketDataNormalizer(IMarketDataNormalizer):
    """
    Standardizes external third-party market data formats (e.g., dict payloads from MetaTrader or REST APIs)
    into standard RG_V3 MarketDataPoint objects.
    """
    def normalize_external_data(self, external_data: Any, asset_id: str) -> List[MarketDataPoint]:
        normalized_points: List[MarketDataPoint] = []

        # Handle dictionary input
        if isinstance(external_data, dict):
            # Check for standard bar list
            bars = external_data.get("bars") or external_data.get("candles")
            if isinstance(bars, list):
                for bar in bars:
                    point = self._normalize_single_bar(bar, asset_id)
                    if point:
                        normalized_points.append(point)
            else:
                # Try to normalize direct single dictionary
                point = self._normalize_single_bar(external_data, asset_id)
                if point:
                    normalized_points.append(point)

        # Handle list of items
        elif isinstance(external_data, list):
            for item in external_data:
                point = self._normalize_single_bar(item, asset_id)
                if point:
                    normalized_points.append(point)

        return normalized_points

    def _normalize_single_bar(self, bar: Any, asset_id: str) -> Optional[MarketDataPoint]:
        """Helper to safely map keys from a variety of external schemas."""
        if not isinstance(bar, dict):
            return None

        try:
            # 1. Resolve Timestamp
            ts_raw = bar.get("Timestamp") or bar.get("timestamp") or bar.get("time") or bar.get("t")
            if isinstance(ts_raw, str):
                try:
                    ts = datetime.fromisoformat(ts_raw)
                except ValueError:
                    ts = datetime.now()
            elif isinstance(ts_raw, (int, float)):
                ts = datetime.fromtimestamp(ts_raw)
            elif isinstance(ts_raw, datetime):
                ts = ts_raw
            else:
                ts = datetime.now()

            # 2. Resolve OHLCV with common mappings
            o = float(bar.get("Open") or bar.get("open") or bar.get("o") or 0.0)
            h = float(bar.get("High") or bar.get("high") or bar.get("h") or 0.0)
            l = float(bar.get("Low") or bar.get("low") or bar.get("l") or 0.0)
            c = float(bar.get("Close") or bar.get("close") or bar.get("c") or 0.0)
            v = float(bar.get("Volume") or bar.get("volume") or bar.get("v") or 0.0)

            return MarketDataPoint(
                AssetId=asset_id,
                Timestamp=ts,
                Open=o,
                High=h,
                Low=l,
                Close=c,
                Volume=v
            )
        except Exception:
            return None
