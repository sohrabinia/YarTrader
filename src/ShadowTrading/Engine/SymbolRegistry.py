"""Compatibility import for legacy callers.

The canonical market universe registry now lives outside the retired Shadow
runtime. New production code must import from src.Market.Universe.symbol_registry.
"""

from src.Market.Universe.symbol_registry import (  # noqa: F401
    CANONICAL_30_SYMBOLS,
    REGISTRY_FILE,
    SymbolRegistry,
    parse_market_universe_yaml,
)

__all__ = [
    "CANONICAL_30_SYMBOLS",
    "REGISTRY_FILE",
    "SymbolRegistry",
    "parse_market_universe_yaml",
]
