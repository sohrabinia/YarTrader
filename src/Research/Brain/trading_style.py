from typing import Dict, Any, Optional
from enum import Enum

class TradingStyle(str, Enum):
    FAST_SCALPING = "FAST_SCALPING"
    SCALPING = "SCALPING"
    INTRADAY = "INTRADAY"
    SWING = "SWING"

class TradingStyleSelector:
    """
    Selects and evaluates trading styles based on timeframe, market session, volatility, and spread sensitivity.
    """

    STYLE_PROFILES = {
        TradingStyle.FAST_SCALPING: {
            "timeframes": ["M1", "M5"],
            "holding_time": "Very Short (1-15 mins)",
            "max_allowed_spread_pip": 1.5,
            "min_rr": 1.5,
            "session_awareness": False,
            "description": "Ultra-fast execution targeting micro price imbalances with high spread sensitivity."
        },
        TradingStyle.SCALPING: {
            "timeframes": ["M5", "M15"],
            "holding_time": "Short (15-60 mins)",
            "max_allowed_spread_pip": 2.5,
            "min_rr": 1.5,
            "session_awareness": True,
            "description": "Short intraday opportunities capturing rapid liquidity expansions."
        },
        TradingStyle.INTRADAY: {
            "timeframes": ["M15", "H1", "H4"],
            "holding_time": "Medium (1-8 hours)",
            "max_allowed_spread_pip": 4.0,
            "min_rr": 2.0,
            "session_awareness": True,
            "description": "Day trading setups aligned with major London/NY session momentum."
        },
        TradingStyle.SWING: {
            "timeframes": ["H4", "D1", "W1"],
            "holding_time": "Multi-day (1-7 days)",
            "max_allowed_spread_pip": 10.0,
            "min_rr": 2.5,
            "session_awareness": False,
            "description": "Macro position holding aligned with higher timeframe market structure."
        }
    }

    def select_style(self, timeframe: str, current_spread_pip: float = 1.0) -> Dict[str, Any]:
        tf_upper = timeframe.upper()

        selected = TradingStyle.INTRADAY # Default fallback
        if tf_upper in ["M1"]:
            selected = TradingStyle.FAST_SCALPING
        elif tf_upper in ["M5"]:
            selected = TradingStyle.FAST_SCALPING if current_spread_pip <= 1.5 else TradingStyle.SCALPING
        elif tf_upper in ["M15"]:
            selected = TradingStyle.SCALPING
        elif tf_upper in ["H1"]:
            selected = TradingStyle.INTRADAY
        elif tf_upper in ["H4", "D1", "W1"]:
            selected = TradingStyle.SWING

        profile = self.STYLE_PROFILES[selected].copy()
        profile["selected_style"] = selected.value
        profile["is_spread_acceptable"] = current_spread_pip <= profile["max_allowed_spread_pip"]
        profile["current_spread_pip"] = current_spread_pip

        return profile
