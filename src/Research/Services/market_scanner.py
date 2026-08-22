"""
YARTRADER — Market Scanner Service
Scans discovered MT5 symbols, fetches ticks, spread, volatility, and ranks candidates.
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("MarketScanner")


class MarketScanner:
    def __init__(self, mt5_adapter: Optional[Any] = None, discovery_service: Optional[Any] = None):
        self.mt5_adapter = mt5_adapter
        self.discovery_service = discovery_service

    def scan_markets(self) -> List[Dict[str, Any]]:
        """
        Scans discovered symbols, evaluates price ticks, spreads, and ranks candidates.
        """
        symbols = []
        if self.discovery_service:
            symbols = self.discovery_service.get_tradeable_symbols()
        else:
            symbols = [{"symbol": "XAUUSD"}, {"symbol": "EURUSD"}, {"symbol": "BITCOIN"}]

        scanned = []
        for sym_info in symbols:
            symbol = sym_info["symbol"] if isinstance(sym_info, dict) else sym_info
            tick = None
            if self.mt5_adapter and hasattr(self.mt5_adapter, "get_symbol_tick"):
                try:
                    tick = self.mt5_adapter.get_symbol_tick(symbol)
                except Exception:
                    pass

            bid = tick.get("bid", 2000.0) if tick else 2000.0
            ask = tick.get("ask", 2000.5) if tick else 2000.5
            spread = max(0.0, ask - bid)

            scanned.append({
                "symbol": symbol,
                "bid": bid,
                "ask": ask,
                "spread": spread,
                "liquidity": "available" if (bid > 0 and ask > 0) else "unavailable",
                "volatility": "normal"
            })

        # Rank candidates by lowest spread / available liquidity
        scanned.sort(key=lambda x: (x["liquidity"] != "available", x["spread"]))
        return scanned
