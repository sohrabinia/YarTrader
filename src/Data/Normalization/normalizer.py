from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from src.Infrastructure.exceptions import ValidationException


@dataclass(frozen=True)
class NormalizedMarketRecord:
    timestamp: datetime
    symbol: str
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume_size: float
    original_source: str
    source_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NormalizationRules:
    symbol_mapping: Dict[str, str] = field(default_factory=dict)  # raw_alias -> std_symbol
    field_mapping: Dict[str, str] = field(default_factory=dict)   # raw_fieldname -> std_field
    default_symbol: str = "UNKNOWN"


class DataNormalizer:
    """Normalizes raw fields, symbols, and dates into structured NormalizedMarketRecords."""
    def normalize_records(
        self,
        raw_records: List[Dict[str, Any]],
        source_id: str,
        rules: Optional[NormalizationRules] = None
    ) -> List[NormalizedMarketRecord]:
        rules = rules or NormalizationRules()
        normalized_list = []

        for r in raw_records:
            # 1. Symbol Normalization
            raw_sym = r.get("symbol", rules.default_symbol)
            std_sym = rules.symbol_mapping.get(raw_sym, raw_sym)

            # 2. Field Normalization
            # Fetch mapped fields or use standard fallbacks
            f_map = rules.field_mapping
            o_key = f_map.get("open", "open")
            h_key = f_map.get("high", "high")
            l_key = f_map.get("low", "low")
            c_key = f_map.get("close", "close")
            v_key = f_map.get("volume", "volume")
            t_key = f_map.get("timestamp", "timestamp")

            # 3. Timestamp Normalization
            if t_key not in r and "time" in r:
                t_key = "time"
            if v_key not in r and "tick_volume" in r:
                v_key = "tick_volume"

            raw_ts = r.get(t_key)
            if raw_ts is None:
                continue

            try:
                if isinstance(raw_ts, (int, float)):
                    std_ts = datetime.fromtimestamp(raw_ts)
                elif isinstance(raw_ts, str):
                    std_ts = datetime.fromisoformat(raw_ts)
                elif isinstance(raw_ts, datetime):
                    std_ts = raw_ts
                else:
                    continue
            except Exception:
                continue

            # Extracted float metrics
            try:
                op = float(r.get(o_key, 0.0))
                hp = float(r.get(h_key, 0.0))
                lp = float(r.get(l_key, 0.0))
                cp = float(r.get(c_key, 0.0))
                vl = float(r.get(v_key, 0.0))
            except Exception as e:
                raise ValidationException(f"Normalization Error: Could not convert metrics to float values. Details: {e}")

            # 4. Original Source Preservation & Metadata Preservation
            # Deep preserve all other properties
            source_metadata = {k: v for k, v in r.items() if k not in {o_key, h_key, l_key, c_key, v_key, t_key}}

            record = NormalizedMarketRecord(
                timestamp=std_ts,
                symbol=std_sym,
                open_price=op,
                high_price=hp,
                low_price=lp,
                close_price=cp,
                volume_size=vl,
                original_source=source_id,
                source_metadata=source_metadata
            )
            normalized_list.append(record)

        return normalized_list
