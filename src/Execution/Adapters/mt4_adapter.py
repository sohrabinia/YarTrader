"""
YarTrader Real MT4 Broker Adapter & Live Data Ingestion Layer
==============================================================

Provides explicit platform-separated access to MT4 live market data and demo order execution.
Strictly isolates MT4 execution from MT5 research/backtest pipelines.
Enforces real-account rejection (`REAL ACCOUNT -> REJECT`) and `LIVE_TRADING_ENABLED = False`.
"""

import os
import sys
import logging
import time
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from src.Execution.Interfaces.interfaces import IBrokerAdapter
from src.Execution.Models.models import OrderRequest, OrderResponse
from src.Execution.Safety.safety_gate import MetaTraderSafetyGate
from src.Infrastructure.exceptions import ValidationException

logger = logging.getLogger("RealMT4BrokerAdapter")


class RealMT4BrokerAdapter(IBrokerAdapter):
    """
    Dedicated MT4 Platform Broker Adapter.
    Separates MT4 live market signal ingestion and MT4 DEMO trading execution
    from MT5 research, backtest, and walk-forward pipelines.
    """

    TARGET_ACCOUNT = "4109825"
    TARGET_SERVER = "Alpari-MT4-Demo"
    PLATFORM_NAME = "MT4"

    def __init__(self, auto_initialize: bool = True):
        self._initialized = False
        self._mt4 = None
        if auto_initialize:
            self._try_init()

    def _try_init(self) -> bool:
        """Attempts to initialize MT4 IPC connection."""
        try:
            import MetaTrader4 as mt4
            self._mt4 = mt4
            if self._mt4.initialize():
                self._initialized = True
                logger.info("[RealMT4BrokerAdapter] MT4 initialized successfully.")
                return True
        except ImportError:
            logger.info("[RealMT4BrokerAdapter] Native MetaTrader4 package not present. Real MT4 connection unavailable.")
        except Exception as ex:
            logger.warning(f"[RealMT4BrokerAdapter] MT4 initialize exception: {ex}")

        self._initialized = False
        self._mt4 = None
        return False

    def verify_safety_and_account(self, operation_type: str = "DEMO") -> bool:
        """
        Enforces MetaTraderSafetyGate, rejects REAL accounts, and verifies MT4 DEMO identity.
        """
        # 1. Call MetaTraderSafetyGate for MT4
        MetaTraderSafetyGate.verify_operation(
            terminal_type="MT4",
            operation_type=operation_type,
            account_id=self.TARGET_ACCOUNT,
            server_name=self.TARGET_SERVER
        )

        acc_info = self.get_account_info()
        if acc_info is None:
            raise ValidationException("MT4 Terminal is disconnected or account info is unavailable (Fail-Closed).")

        login = str(acc_info.get("login", ""))
        server = str(acc_info.get("server", ""))
        trade_mode = acc_info.get("trade_mode", 0)  # 0 is DEMO

        # Strict Real Account Rejection Check
        if trade_mode != 0 or acc_info.get("is_real", False):
            raise ValidationException("SECURITY VIOLATION: MT4 Connected account is REAL! Real account execution is strictly rejected.")

        if login and login != self.TARGET_ACCOUNT:
            raise ValidationException(
                f"SRE Security Gate Violation: Connected MT4 account '{login}' does not match authorized DEMO account '{self.TARGET_ACCOUNT}'."
            )

        if server and server != self.TARGET_SERVER:
            raise ValidationException(
                f"SRE Security Gate Violation: Connected MT4 server '{server}' does not match authorized DEMO server '{self.TARGET_SERVER}'."
            )

        return True

    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """Returns MT4 account info from native API. Returns None (UNKNOWN) if MT4 is unavailable."""
        if not self._mt4 or not self._initialized:
            return None
        try:
            acc = self._mt4.account_info()
            if acc is None:
                return None
            return dict(acc) if hasattr(acc, "_asdict") else dict(acc)
        except Exception as e:
            logger.error(f"[RealMT4BrokerAdapter] get_account_info exception: {e}")
            return None

    def get_terminal_info(self) -> Optional[Dict[str, Any]]:
        """Returns active MT4 terminal info. Returns None (UNKNOWN) if MT4 is unavailable."""
        if not self._mt4 or not self._initialized:
            return None
        try:
            term = self._mt4.terminal_info()
            if term is None:
                return None
            return dict(term) if hasattr(term, "_asdict") else dict(term)
        except Exception as e:
            logger.error(f"[RealMT4BrokerAdapter] get_terminal_info exception: {e}")
            return None

    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetches symbol information from MT4. Returns None (UNKNOWN) if MT4 is unavailable."""
        if not self._mt4 or not self._initialized:
            return None
        try:
            sym = self._mt4.symbol_info(symbol)
            if sym is None:
                return None
            return dict(sym) if hasattr(sym, "_asdict") else dict(sym)
        except Exception as e:
            logger.error(f"[RealMT4BrokerAdapter] get_symbol_info exception: {e}")
            return None

    def get_symbol_tick(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetches symbol tick from MT4. Returns None (UNKNOWN) if MT4 is unavailable."""
        if not self._mt4 or not self._initialized:
            return None
        try:
            tick = self._mt4.symbol_info_tick(symbol)
            if tick is None:
                return None
            return dict(tick) if hasattr(tick, "_asdict") else dict(tick)
        except Exception as e:
            logger.error(f"[RealMT4BrokerAdapter] get_symbol_tick exception: {e}")
            return None

    def send_order_to_broker(self, request: OrderRequest) -> OrderResponse:
        """
        MT4 HAS ZERO PRODUCTION ORDER EXECUTION AUTHORITY.
        Order execution requests via MT4 are unconditionally rejected.
        """
        logger.error("[RealMT4BrokerAdapter] SECURITY REJECTION: MT4 order execution requested. MT4 execution authority is ZERO.")
        raise ValidationException("SECURITY VIOLATION: MT4 adapter has ZERO production order execution authority. Production execution is strictly reserved for MT5 DEMO.")

    def get_positions(self, symbol: Optional[str] = None, ticket: Optional[int] = None) -> Optional[List[Dict[str, Any]]]:
        """Queries active MT4 positions. Returns None (UNKNOWN) if MT4 is unavailable or query fails."""
        if not self._mt4 or not self._initialized:
            return None
        try:
            kwargs = {}
            if symbol:
                kwargs["symbol"] = symbol
            if ticket:
                kwargs["ticket"] = int(ticket)
            positions = self._mt4.positions_get(**kwargs)
            if positions is None:
                return None
            return [dict(p) if hasattr(p, "_asdict") else dict(p) for p in positions]
        except Exception as e:
            logger.error(f"[RealMT4BrokerAdapter] get_positions exception: {e}")
            return None
