from typing import List, Dict, Any, Optional
import os
import json

from src.Intelligence.Execution.narrative import MarketNarrativeEngine
from src.Intelligence.Execution.liquidity import LiquidityIntelligenceEngine
from src.Intelligence.Execution.zones import InstitutionalZoneEngine
from src.Intelligence.Execution.alignment import MultiTimeframeAlignmentEngine
from src.Intelligence.Execution.similarity import PatternSimilarityIntelligenceEngine
from src.Intelligence.Execution.portfolio import PortfolioRiskIntelligenceEngine

class ExecutionIntelligenceCore:
    """
    Unified Orchestration Hub coordinating:
    - Market Narrative Engine
    - Liquidity Intelligence Engine
    - Institutional Zone Engine
    - Multi-Timeframe Structural Alignment
    - Pattern Similarity Intelligence (research telemetry only)
    - Portfolio Risk Intelligence
    - Canonical Base-hierarchy decision authority (only actionable strategy)

    Legacy analytics are non-authoritative research telemetry. Only the hierarchical
    Base behavior and costed Base-reaction engine may emit an actionable plan.
    Context state remains isolated by symbol and timeframe.
    """
    _instance: Optional["ExecutionIntelligenceCore"] = None

    @classmethod
    def get_instance(cls) -> "ExecutionIntelligenceCore":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self.narrative_engine = MarketNarrativeEngine()
        self.liquidity_engine = LiquidityIntelligenceEngine()
        self.zone_engine = InstitutionalZoneEngine()
        self.alignment_engine = MultiTimeframeAlignmentEngine()
        self.similarity_engine = PatternSimilarityIntelligenceEngine()
        self.portfolio_engine = PortfolioRiskIntelligenceEngine()

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
        """
        Executes the entire execution intelligence pipeline sequentially for a single research context.
        Uses pure mathematical structure mapping; strictly no mock indicators are used.
        """
        state = self.get_context_state(symbol, timeframe)
        if not candles:
            return state

        # Compute SHA256 provenance hash & unique decision cycle ID strictly from OHLC candle price data
        import hashlib
        import uuid
        candle_count = len(candles)
        latest_ts = str(candles[-1].get("time", candles[-1].get("timestamp", "")))
        # OHLC summary vector hash computed strictly from price values to detect identical data
        ohlc_summary = f"{symbol.upper()}:{candle_count}:" + "|".join([
            f"{c.get('open')},{c.get('high')},{c.get('low')},{c.get('close')}" for c in candles
        ])
        ctx_hash = f"ctx-{hashlib.sha256(ohlc_summary.encode('utf-8')).hexdigest()[:16]}"
        cycle_id = f"cycle-{symbol.upper()}-{timeframe.upper()}-{uuid.uuid4().hex[:8]}"


        # 1. Market Narrative
        narrative_res = self.narrative_engine.analyze_narrative(candles)
        narrative_res["data_source"] = "MT5_XAUUSD_M1_RATES"
        narrative_res["data_mode"] = "REAL"
        narrative_res["candle_count"] = candle_count
        narrative_res["latest_candle_timestamp"] = latest_ts
        narrative_res["context_identity"] = ctx_hash
        narrative_res["decision_cycle_id"] = cycle_id
        state["narrative"] = narrative_res

        # 2. Liquidity Mapping
        liquidity_res = self.liquidity_engine.analyze_liquidity(candles, narrative_res.get("swings", []))
        state["liquidity"] = liquidity_res

        # 3. Institutional Zones
        zones_res = self.zone_engine.analyze_zones(candles, narrative_res.get("swings", []))
        state["zones"] = zones_res

        # 4. Multi-Timeframe Alignment
        alignment_narratives = {timeframe: narrative_res}
        if all_timeframe_candles:
            for tf, tf_candles in all_timeframe_candles.items():
                if tf.upper() != timeframe.upper():
                    tf_narrative = self.narrative_engine.analyze_narrative(tf_candles)
                    alignment_narratives[tf] = tf_narrative

        alignment_res = self.alignment_engine.align_structures(symbol, alignment_narratives)
        state["alignment"] = alignment_res

        # 5. Pattern Similarity & Unified Fractal Analysis
        # Current structural signature: last 4 swing heights
        swings = narrative_res.get("swings", [])
        sig = [s["price"] for s in swings[-4:]] if len(swings) >= 4 else [float(c["close"]) for c in candles[-4:]]

        # Load historical patterns from database/memory
        historical_patterns = self._load_historical_pattern_memory()
        similarity_res = self.similarity_engine.find_similar_structures(sig, historical_patterns)
        state["similarity"] = similarity_res

        # Unified Primitive Structure & Memory State (Indicator-Free)
        state["fractal"] = {
            "symbol": symbol.upper(),
            "primary_timeframe": timeframe.upper(),
            "fractal_status": "PRIMITIVE_STRUCTURE_ONLY",
            "evidence_state": "NO_INDICATORS"
        }

        # 6. Portfolio Risk evaluation
        active_trades = active_portfolio_trades or []
        portfolio_res = self.portfolio_engine.calculate_portfolio_risk(active_trades, virtual_balance)

        # 6b. Canonical strategy authority: hierarchical Bases and costed Base reactions.
        # The legacy planner and its narrative/liquidity/zone/similarity inputs are
        # deliberately not allowed to emit or override actionable BUY/SELL decisions.
        from src.Intelligence.Execution.strategy_orchestrator import StrategyOrchestrator
        base_result = StrategyOrchestrator().evaluate_all_strategies(
            symbol=symbol,
            primary_timeframe=timeframe,
            candles=candles,
            all_timeframe_candles=all_timeframe_candles,
            spread_pip=1.0,
        )
        base_candidates = list(base_result.get("candidates") or [])
        strategy_eval_res = {
            "candidates": base_candidates,
            "authority": "BASE_HIERARCHY_ONLY",
            "execution_authority": True,
            "decision_source": "hierarchical_base_behavior_plus_costed_reaction",
            "summary": base_result.get("summary", "Base-only strategy."),
        }
        if base_candidates:
            candidate = base_candidates[0]
            plan = {
                "action": str(candidate.get("direction", "WAIT")),
                "decision": str(candidate.get("direction", "WAIT")),
                "strategy": "BASE_HIERARCHY",
                "status": "PROPOSED",
                "entry": candidate.get("entry"),
                "stop_loss": candidate.get("stop_loss"),
                "take_profit": candidate.get("take_profit"),
                "risk_reward": candidate.get("risk_reward"),
                "confidence": candidate.get("confidence", 0.0),
                "reason": "; ".join(candidate.get("reasoning") or []),
                "decision_authority": "BASE_HIERARCHY_ONLY",
                "decision_source": "BASE_HIERARCHY_ONLY",
                "context_identity": ctx_hash,
                "decision_cycle_id": cycle_id,
                "source": "hierarchical_base_behavior_plus_costed_reaction",
            }
        else:
            base_plan = base_result.get("base_plan") or {}
            plan = {
                "action": "WAIT",
                "decision": "WAIT",
                "strategy": "BASE_HIERARCHY",
                "status": "WAIT",
                "entry": None,
                "stop_loss": None,
                "take_profit": None,
                "risk_reward": 0.0,
                "confidence": 0.0,
                "reason": str(base_plan.get("reason") or base_result.get("summary") or
                              "No validated Base-reaction setup; no alternative strategy is permitted."),
                "decision_authority": "BASE_HIERARCHY_ONLY",
                "decision_source": "BASE_HIERARCHY_ONLY",
                "context_identity": ctx_hash,
                "decision_cycle_id": cycle_id,
                "source": "hierarchical_base_behavior_plus_costed_reaction",
            }
        state["plan"] = plan
        from datetime import datetime
        state["last_updated"] = datetime.now().isoformat()

        # Combine research telemetry with the sole Base-only actionable plan.
        return {
            "symbol": symbol.upper(),
            "timeframe": timeframe.upper(),
            "narrative": narrative_res,
            "liquidity": liquidity_res,
            "zones": zones_res,
            "alignment": alignment_res,
            "similarity": similarity_res,
            "fractal": state.get("fractal", {}),
            "strategy_evaluation": strategy_eval_res,
            "portfolio_risk": portfolio_res,
            "plan": plan,
            "base_analysis": base_result,
        }

    def _load_historical_pattern_memory(self) -> List[Dict[str, Any]]:
        """Helper to load historical pattern definitions safely."""
        patterns_path = "runtime_logs/pattern_outcomes.json"
        if os.path.exists(patterns_path):
            try:
                with open(patterns_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []
