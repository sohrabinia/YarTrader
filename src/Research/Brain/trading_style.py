"""Base-only compatibility style selector.

Legacy code may still import TradingStyleSelector, but no scalp, momentum,
intraday, or swing style is selectable in YarTrader.
"""
from enum import Enum


class TradingStyle(str, Enum):
    BASE_HIERARCHY = "BASE_HIERARCHY"


class TradingStyleSelector:
    """Compatibility selector that always returns the single supported strategy."""

    @staticmethod
    def select_trading_style(*args, **kwargs):
        del args, kwargs
        return TradingStyle.BASE_HIERARCHY

    @staticmethod
    def select(*args, **kwargs):
        del args, kwargs
        return TradingStyle.BASE_HIERARCHY

    @staticmethod
    def get_parameters(*args, **kwargs):
        del args, kwargs
        return {}
