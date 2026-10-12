"""Compatibility facade for the retired conventional signal engine.

All callers are routed to the single hierarchical Base/re-entry reaction strategy.
This module intentionally contains no indicator, momentum, scalp, or style-selection
signal logic.
"""
from typing import Dict, List, Optional
from datetime import datetime, timezone
import uuid
from src.Data.MarketData.Models.models import MarketDataPoint
from src.Decision.Intelligence.timeframe_selector import UnifiedSignalContract
# Kept as a module attribute for old integrations/tests; this facade never records
# a signal or updates a separate strategy learner.
from src.Research.Brain.learning_bridge import BrainLearningBridge


class ProfessionalSignalEngine:
    """Legacy name retained for API compatibility; Base-only signal generation."""

    def __init__(self, *args, **kwargs) -> None:
        del args, kwargs

    def generate_unified_signal(
        self,
        symbol: str,
        candles_by_tf: Dict[str, List[MarketDataPoint]],
        spread_pip: float = 1.0,
        account_balance: float = 10000.0,
    ) -> UnifiedSignalContract:
        from src.Decision.Intelligence.engine import DecisionEngine
        return DecisionEngine().generate_professional_signal(
            symbol=symbol, candles_by_tf=candles_by_tf,
            spread_pip=spread_pip, account_balance=account_balance,
        )


    def generate_signal(
        self,
        symbol: str,
        timeframe: str,
        candles_by_tf: Dict[str, List[MarketDataPoint]],
        spread_pip: float = 1.0,
        platform_provenance: Optional[str] = None,
        account_balance: float = 10000.0,
    ) -> UnifiedSignalContract:
        """Backward-compatible entry point; non-MT5 provenance fails closed to WAIT."""
        if platform_provenance and platform_provenance.strip().upper() != "MT5":
            return UnifiedSignalContract(
                signal_id=f"BASE_WAIT-{uuid.uuid4().hex[:12]}",
                symbol=symbol.upper(), timeframe=timeframe.upper(), direction="WAIT",
                entry_price=0.0, stop_loss=0.0, take_profit=0.0, risk_reward=0.0,
                confidence=0.0, pattern_id="BASE_WAIT",
                market_context="Only the canonical MT5 Base-hierarchy authority is enabled.",
                created_at=datetime.now(timezone.utc).isoformat(),
            )
        return self.generate_unified_signal(
            symbol=symbol, candles_by_tf=candles_by_tf, spread_pip=spread_pip,
            account_balance=account_balance,
        )
