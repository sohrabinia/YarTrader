from typing import List, Dict, Any, Optional
import os
import json
from src.Application.Deployment.storage import YarTraderStorageManager

from src.Intelligence.Execution.narrative import MarketNarrativeEngine
from src.Intelligence.Execution.liquidity import LiquidityIntelligenceEngine
from src.Intelligence.Execution.zones import InstitutionalZoneEngine
from src.Intelligence.Execution.alignment import MultiTimeframeAlignmentEngine
from src.Intelligence.Execution.similarity import PatternSimilarityIntelligenceEngine
from src.Intelligence.Execution.portfolio import PortfolioRiskIntelligenceEngine
from src.Intelligence.Execution.execution_planner import ExecutionIntelligencePlanner

class ExecutionIntelligenceCore:
    """
    Unified Orchestration Hub coordinating:
    - Market Narrative Engine
    - Liquidity Intelligence Engine
    - Institutional Zone Engine
    - Multi-Timeframe Structural Alignment
    - Pattern Similarity Intelligence
    - Explainable Execution Planning
    - Portfolio Risk Intelligence

    Adheres strictly to the Shared Cognitive Intelligence Core rule (no separate per-symbol/TF models).
    Serves 300 independent research contexts with complete memory/state isolation.
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
        self.planner = ExecutionIntelligencePlanner()

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
        lang: str = "fa"
    ) -> Dict[str, Any]:
        """
        Executes the entire execution intelligence pipeline sequentially for a single research context.
        Uses pure mathematical structure mapping; strictly no mock indicators are used.
        """
        state = self.get_context_state(symbol, timeframe)
        if not candles:
            return state

        # 1. Market Narrative
        narrative_res = self.narrative_engine.analyze_narrative(candles)
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

        # 5. Pattern Similarity Search
        # Current structural signature: last 4 swing heights
        swings = narrative_res.get("swings", [])
        sig = [s["price"] for s in swings[-4:]] if len(swings) >= 4 else [float(c["close"]) for c in candles[-4:]]

        # Load historical patterns from database/memory
        historical_patterns = self._load_historical_pattern_memory()
        similarity_res = self.similarity_engine.find_similar_structures(sig, historical_patterns)
        state["similarity"] = similarity_res

        # 6. Portfolio Risk evaluation
        active_trades = active_portfolio_trades or []
        portfolio_res = self.portfolio_engine.calculate_portfolio_risk(active_trades, virtual_balance)

        # 7. Generate advisory plan recommendation
        current_price = float(candles[-1]["close"])
        plan_res = self.planner.generate_execution_plan(
            symbol=symbol,
            timeframe=timeframe,
            narrative=narrative_res,
            liquidity=liquidity_res,
            zones=zones_res,
            alignment=alignment_res,
            similarity=similarity_res,
            portfolio_risk=portfolio_res,
            current_price=current_price,
            lang=lang
        )
        state["plan"] = plan_res["plan"]
        from datetime import datetime
        state["last_updated"] = datetime.now().isoformat()

        # Combine results
        return {
            "symbol": symbol.upper(),
            "timeframe": timeframe.upper(),
            "narrative": narrative_res,
            "liquidity": liquidity_res,
            "zones": zones_res,
            "alignment": alignment_res,
            "similarity": similarity_res,
            "portfolio_risk": portfolio_res,
            "plan": plan_res["plan"]
        }

    def _load_historical_pattern_memory(self) -> List[Dict[str, Any]]:
        """Helper to load historical pattern definitions safely."""
        patterns_path = os.path.join(YarTraderStorageManager.get_manager().get_runtime_dir(), "pattern_outcomes.json")
        if os.path.exists(patterns_path):
            try:
                with open(patterns_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []
