from typing import List, Dict, Any, Optional
import math
import os
import hashlib
import json
"""Base-only analysis facade. Legacy indicator/zone/similarity engines are retired."""

from src.Intelligence.Execution.portfolio import PortfolioRiskIntelligenceEngine

class ExecutionIntelligenceCore:
    """
    Every analysis request delegates only to the hierarchical Base/re-entry reaction
    engine. Old indicator, momentum, FVG, order-block, liquidity-sweep, fractal and
    similarity engines are not loaded and cannot produce a signal.
    """
    _instance: Optional["ExecutionIntelligenceCore"] = None

    @classmethod
    def get_instance(cls) -> "ExecutionIntelligenceCore":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        # Portfolio risk remains a safety control, not a signal-generating strategy.
        # 60% is limited to explicitly tagged backtest processes.
        backtest_mode = os.environ.get("YARTRADER_BACKTEST_MODE", "").strip().lower() in {"1", "true", "yes", "on"}
        daily_dd_limit = 10.0
        if backtest_mode:
            try:
                daily_dd_limit = float(os.environ.get("YARTRADER_BACKTEST_MAX_DAILY_DRAWDOWN_PCT", "60"))
            except (TypeError, ValueError, OverflowError):
                daily_dd_limit = 60.0
            if not math.isfinite(daily_dd_limit) or not 0.0 < daily_dd_limit <= 100.0:
                daily_dd_limit = 60.0
        self.portfolio_engine = PortfolioRiskIntelligenceEngine(max_daily_drawdown_pct=daily_dd_limit)

        # No alternative strategy/indicator engines are instantiated here.

        # In-memory registry of isolated context states to prevent cross-contamination
        # Keys are (symbol, timeframe) tuples
        self.context_states: Dict[tuple, Dict[str, Any]] = {}

    def get_context_state(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """Gets or initializes the isolated state for a specific research context."""
        key = (symbol.upper(), timeframe.upper())
        if key not in self.context_states:
            self.context_states[key] = {
                "symbol": symbol.upper(),
                "timeframe": timeframe.upper(),
                "narrative": {},
                "liquidity": {},
                "zones": {},
                "alignment": {},
                "similarity": {},
                "plan": {},
                "last_updated": None
            }
        return self.context_states[key]

    def evaluate_context(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict[str, Any]],
        all_timeframe_candles: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        active_portfolio_trades: Optional[List[Dict[str, Any]]] = None,
        virtual_balance: float = 10000.0,
        lang: str = "fa",
        newborn_brain_report: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Evaluate the sole canonical Base hierarchy strategy.

        Old narrative, liquidity-sweep, order-block, FVG, fractal and similarity
        engines are not instantiated or consulted. Their response fields remain
        empty only for API compatibility; they cannot influence the Base plan.
        """
        del lang, newborn_brain_report
        context_payload = json.dumps(candles or [], sort_keys=True, separators=(",", ":"), default=str)
        context_digest = hashlib.sha256(context_payload.encode("utf-8")).hexdigest()[:16]
        context_identity = f"{symbol.upper()}::{timeframe.upper()}::{context_digest}"
        try:
            if not isinstance(active_portfolio_trades, (list, type(None))):
                raise ValueError("active portfolio trades must be a list")
            balance = float(virtual_balance)
            if not math.isfinite(balance) or balance <= 0.0:
                raise ValueError("virtual balance must be finite and positive")
            portfolio_risk = self.portfolio_engine.calculate_portfolio_risk(
                active_portfolio_trades or [], virtual_balance=balance
            )
            if not isinstance(portfolio_risk, dict) or not isinstance(portfolio_risk.get("approved"), bool):
                raise ValueError("portfolio risk result is invalid")
        except Exception:
            portfolio_risk = {
                "approved": False,
                "violations": ["Portfolio risk evaluation unavailable; execution blocked."],
                "summary": "Portfolio risk unavailable; execution blocked.",
            }
        state = self.get_context_state(symbol, timeframe)
        if not candles:
            blocked = not portfolio_risk["approved"]
            empty_plan = {
                "action": "AVOID" if blocked else "WAIT",
                "decision": "AVOID" if blocked else "WAIT",
                "strategy": "BASE_HIERARCHY",
                "status": "BLOCKED_BY_PORTFOLIO_RISK" if blocked else "WAIT",
                "reason": ("; ".join(portfolio_risk.get("violations") or []) if blocked
                           else "No real candles; Base-only analysis unavailable."),
                "decision_authority": "BASE_HIERARCHY_ONLY",
                "decision_source": "BASE_HIERARCHY_ONLY",
                "context_identity": context_identity,
                "entry": 0.0 if blocked else None,
                "stop_loss": 0.0 if blocked else None,
                "take_profit": 0.0 if blocked else None,
                "confidence": 0.0,
            }
            return {
                "symbol": symbol.upper(), "timeframe": timeframe.upper(),
                "narrative": {}, "liquidity": {"status": "DISABLED_NON_BASE"},
                "zones": {"status": "DISABLED_NON_BASE", "order_blocks": [], "fair_value_gaps": []},
                "alignment": {"alignment": "UNAVAILABLE", "decision_authority": "BASE_HIERARCHY_ONLY"},
                "similarity": {
                    "status": "DISABLED_NON_BASE", "evidence_state": "INSUFFICIENT_EVIDENCE",
                    "average_similarity_score": 0.0, "similar_pattern_found": False, "best_match": None,
                },
                "fractal": {"status": "DISABLED_NON_BASE", "evidence_state": "BASE_ONLY"},
                "strategy_evaluation": {"candidates": [], "authority": "BASE_HIERARCHY_ONLY"},
                "portfolio_risk": portfolio_risk,
                "plan": empty_plan,
                "base_analysis": {"best_candidate": None, "summary": "No real candles; no signal."},
            }

        from src.Intelligence.Execution.strategy_orchestrator import StrategyOrchestrator
        tf_candles = dict(all_timeframe_candles or {})
        tf_candles.setdefault(timeframe, candles)
        base_result = StrategyOrchestrator().evaluate_all_strategies(
            symbol=symbol,
            primary_timeframe=timeframe,
            candles=candles,
            all_timeframe_candles=tf_candles,
        )
        candidate = base_result.get("best_candidate")
        raw_plan = base_result.get("base_plan") or {}
        if candidate:
            plan = {
                "action": str(candidate.get("direction", "WAIT")),
                "decision": str(candidate.get("direction", "WAIT")),
                "strategy": "BASE_HIERARCHY",
                "status": "PROPOSED",
                "entry": candidate.get("entry"),
                "stop_loss": candidate.get("stop_loss"),
                "take_profit": candidate.get("take_profit"),
                "risk_reward": candidate.get("risk_reward", 0.0),
                "confidence": candidate.get("confidence", 0.0),
                "reason": "; ".join(candidate.get("reasoning") or []),
                "decision_authority": "BASE_HIERARCHY_ONLY",
                "decision_source": "BASE_HIERARCHY_ONLY",
                "context_identity": context_identity,
                "source": "hierarchical_base_behavior_plus_costed_reaction",
            }
        else:
            plan = {
                "action": "WAIT", "decision": "WAIT", "strategy": "BASE_HIERARCHY",
                "status": "WAIT", "entry": None, "stop_loss": None, "take_profit": None,
                "risk_reward": 0.0, "confidence": 0.0,
                "reason": str(raw_plan.get("reason") or base_result.get("summary") or
                              "No validated Base-reaction setup; no alternative strategy is permitted."),
                "decision_authority": "BASE_HIERARCHY_ONLY",
                "decision_source": "BASE_HIERARCHY_ONLY",
                "context_identity": context_identity,
                "source": "hierarchical_base_behavior_plus_costed_reaction",
            }

        if not portfolio_risk["approved"]:
            violations = portfolio_risk.get("violations") or ["Portfolio risk gate rejected the plan."]
            plan.update({
                "action": "AVOID", "decision": "AVOID", "status": "BLOCKED_BY_PORTFOLIO_RISK",
                "entry": 0.0, "stop_loss": 0.0, "take_profit": 0.0,
                "risk_reward": 0.0, "confidence": 0.0,
                "reason": "; ".join(str(v) for v in violations),
            })

        hierarchy = base_result.get("hierarchy") or {}
        structure = hierarchy.get("structure") or {}
        state["narrative"] = {
            "decision_authority": "BASE_HIERARCHY_ONLY",
            "summary": base_result.get("summary"),
            "base_hierarchy": hierarchy,
        }
        state["liquidity"] = {"status": "DISABLED_NON_BASE", "resting_bsl": [],
                              "resting_ssl": [], "equal_highs": [], "equal_lows": [],
                              "sweeps": [], "latest_sweep": None, "voids": []}
        state["zones"] = {"status": "DISABLED_NON_BASE", "order_blocks": [],
                          "fair_value_gaps": [], "breaker_blocks": [],
                          "premium_zone": {}, "discount_zone": {}, "equilibrium": 0.0}
        state["alignment"] = {
            "alignment": structure.get("parent_child_alignment", "UNAVAILABLE"),
            "decision_authority": "BASE_HIERARCHY_ONLY",
            "parent_timeframe": structure.get("parent_timeframe"),
            "child_timeframe": structure.get("child_timeframe"),
        }
        state["similarity"] = {
            "status": "DISABLED_NON_BASE", "evidence_state": "INSUFFICIENT_EVIDENCE",
            "average_similarity_score": 0.0, "similar_pattern_found": False, "best_match": None,
        }
        state["fractal"] = {"status": "DISABLED_NON_BASE", "evidence_state": "BASE_ONLY"}
        state["plan"] = plan
        from datetime import datetime
        state["last_updated"] = datetime.now().isoformat()
        return {
            "symbol": symbol.upper(), "timeframe": timeframe.upper(),
            "narrative": state["narrative"], "liquidity": state["liquidity"],
            "zones": state["zones"], "alignment": state["alignment"],
            "similarity": state["similarity"], "fractal": state["fractal"],
            "strategy_evaluation": {
                "candidates": list(base_result.get("candidates") or []),
                "authority": "BASE_HIERARCHY_ONLY",
                "execution_authority": True,
                "decision_source": "hierarchical_base_behavior_plus_costed_reaction",
                "summary": base_result.get("summary", "Base-only strategy."),
            },
            "portfolio_risk": portfolio_risk,
            "plan": plan, "base_analysis": base_result,
            "historical_structure_analysis": base_result.get("historical_structure_analysis", {}),
        }
