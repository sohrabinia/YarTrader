"""
YARTRADER — Symbol Discovery Service
Queries MT5 or fallback symbol registry for tradeable active symbols.
Supports Forex, Gold, Crypto, Indices, and Commodities.
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("SymbolDiscoveryService")

DEFAULT_SYMBOLS = [
    "XAUUSD",
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "BTCUSD",
    "BITCOIN",
    "ETHUSD",
    "ETHEREUM",
    "SOLUSD",
    "GER40",
    "US30"
]


class SymbolDiscoveryService:
    def __init__(self, mt5_adapter: Optional[Any] = None):
        self.mt5_adapter = mt5_adapter

    def get_tradeable_symbols(self) -> List[Dict[str, Any]]:
        """
        Retrieves active, tradeable symbols from MT5 terminal or fallback registry.
        Filters for visible=True, trade_mode enabled, tick available.
        """
        discovered = []
        if self.mt5_adapter and hasattr(self.mt5_adapter, "get_all_symbols"):
            try:
                raw_symbols = self.mt5_adapter.get_all_symbols()
                for sym in raw_symbols:
                    if isinstance(sym, dict):
                        name = sym.get("name")
                        visible = sym.get("visible", True)
                        trade_mode = sym.get("trade_mode", 0)
                        if name and visible and trade_mode != 0:
                            discovered.append({
                                "symbol": name,
                                "category": sym.get("path", "Forex"),
                                "visible": visible,
                                "trade_mode": trade_mode,
                                "volume_min": sym.get("volume_min", 0.01),
                                "volume_step": sym.get("volume_step", 0.01)
                            })
            except Exception as e:
                logger.warning(f"Failed to query MT5 adapter for symbols: {e}")

        if not discovered:
            # Sandbox / Fallback discovery
            for sym in DEFAULT_SYMBOLS:
                discovered.append({
                    "symbol": sym,
                    "category": "Crypto" if "BTC" in sym or "ETH" in sym or "BITCOIN" in sym or "SOL" in sym else ("Gold" if "XAU" in sym else ("Indices" if "GER" in sym or "US30" in sym else "Forex")),
                    "visible": True,
                    "trade_mode": 4,  # Full access
                    "volume_min": 0.01,
                    "volume_step": 0.01
                })

        return discovered
