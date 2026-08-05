# Centralized Timeframe Registry - Single Source of Truth
# All validation, mapping, and core intelligence layers use this registry.
from typing import Any

SUPPORTED_TIMEFRAMES = {
    "M1": {
        "identifier": "M1",
        "minutes": 1,
        "category": "intraday",
        "mt5_mapping": 1,  # TIMEFRAME_M1
        "validation_rules": {"min_candles": 14},
        "minimum_lookback_days": 1
    },
    "M5": {
        "identifier": "M5",
        "minutes": 5,
        "category": "intraday",
        "mt5_mapping": 5,  # TIMEFRAME_M5
        "validation_rules": {"min_candles": 14},
        "minimum_lookback_days": 2
    },
    "M15": {
        "identifier": "M15",
        "minutes": 15,
        "category": "intraday",
        "mt5_mapping": 15,  # TIMEFRAME_M15
        "validation_rules": {"min_candles": 14},
        "minimum_lookback_days": 6
    },
    "H1": {
        "identifier": "H1",
        "minutes": 60,
        "category": "intraday",
        "mt5_mapping": 16385,  # TIMEFRAME_H1
        "validation_rules": {"min_candles": 14},
        "minimum_lookback_days": 22
    },
    "H4": {
        "identifier": "H4",
        "minutes": 240,
        "category": "swing",
        "mt5_mapping": 16388,  # TIMEFRAME_H4
        "validation_rules": {"min_candles": 14},
        "minimum_lookback_days": 52
    },
    "D1": {
        "identifier": "D1",
        "minutes": 1440,
        "category": "daily",
        "mt5_mapping": 16408,  # TIMEFRAME_D1
        "validation_rules": {"min_candles": 14},
        "minimum_lookback_days": 205
    },
    "W1": {
        "identifier": "W1",
        "minutes": 10080,
        "category": "macro",
        "mt5_mapping": 32769,  # TIMEFRAME_W1
        "validation_rules": {"min_candles": 14},
        "minimum_lookback_days": 210
    },
    "MN1": {
        "identifier": "MN1",
        "minutes": 43200,
        "category": "macro",
        "mt5_mapping": 49153,  # TIMEFRAME_MN1
        "validation_rules": {"min_candles": 14},
        "minimum_lookback_days": 900
    }
}


class TimeframeNormalizer:
    @staticmethod
    def normalize(timeframe: Any) -> Any:
        """
        Normalizes a timeframe into a canonical internal representation.
        Supports both traditional integer tick counts (must be > 0)
        and new multi-timeframe string IDs ("Tick", "M1", "M5", "M15", "H1", "H4", "D1", "W1", "MN1").
        """
        if timeframe is None:
            raise ValueError("Timeframe cannot be None")

        if isinstance(timeframe, bool):
            raise ValueError("Booleans are not valid timeframes")

        # If it's already an integer, check if it's positive
        if isinstance(timeframe, int):
            if timeframe > 0:
                return timeframe
            raise ValueError(f"Invalid integer timeframe (must be > 0): {timeframe}")

        if isinstance(timeframe, str):
            # Check if it represents an integer like "64" or "1024"
            if timeframe.isdigit():
                val = int(timeframe)
                if val > 0:
                    return val
                raise ValueError(f"Invalid integer timeframe string (must be > 0): {timeframe}")

            # Match standard strings (case-insensitive)
            supported = ["Tick", "M1", "M5", "M15", "H1", "H4", "D1", "W1", "MN1"]
            for s in supported:
                if s.upper() == timeframe.upper():
                    return s

            raise ValueError(f"Invalid string timeframe: {timeframe}")

        raise ValueError(f"Unsupported timeframe type: {type(timeframe)}")
