import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.Decision.Interfaces.interfaces import IDecisionEngine
from src.Decision.Models.models import DecisionContext, DecisionResult, DecisionReason, DecisionState
from src.Decision.Intelligence.models import (
    DecisionIntelligenceContext,
    DecisionIntelligenceReport,
    DecisionHistoryRecord
)
from src.Decision.Intelligence.services import (
    DecisionContextBuilder,
    DecisionAnalyzer,
    DecisionQualityEvaluator,
    DecisionConflictResolver,
    DecisionEvidenceCollector,
    DecisionReportBuilder,
    DecisionValidator,
    DecisionHistoryStore
)
from src.Decision.Intelligence.professional_signal_engine import ProfessionalSignalEngine
from src.Decision.Intelligence.hierarchical_base_behavior_engine import HierarchicalBaseBehaviorEngine
from src.Decision.Intelligence.multitimeframe_base_behavior_monitor import MultitimeframeBaseBehaviorMonitor
from src.Decision.Intelligence.timeframe_selector import UnifiedSignalContract
from src.Data.MarketData.Models.models import MarketDataPoint
from src.Infrastructure.exceptions import ValidationException


class DecisionEngine(IDecisionEngine):
    """
    Advanced context-aware Decision Intelligence Engine.
    Synthesizes multi-factor inputs (Research, Strategy, Risk) to produce explainable analytical decisions.
    Integrates ProfessionalSignalEngine as the canonical professional signal generation layer.
    """
    def __init__(self, signal_engine: Optional[ProfessionalSignalEngine] = None) -> None:
        self.builder = DecisionContextBuilder()
        self.analyzer = DecisionAnalyzer()
        self.evaluator = DecisionQualityEvaluator()
        self.conflict_resolver = DecisionConflictResolver()
        self.collector = DecisionEvidenceCollector()
        self.report_builder = DecisionReportBuilder()
        self.validator = DecisionValidator()
        self.history_store = DecisionHistoryStore()
        # Legacy injected signal engines are retained only as a constructor
        # compatibility argument. They are never instantiated or called.
        self.signal_engine = None
        # Parent/child Base intelligence is proposal-only until a validated demo executor is added.
        self.base_behavior_engine = HierarchicalBaseBehaviorEngine()
        # Live closed-candle Base observer: hierarchy + reaction ledger, no broker side effects.
        self.base_behavior_monitor = MultitimeframeBaseBehaviorMonitor()
        self.last_base_behavior_report: Dict[str, Any] = {"status": "NOT_RUN", "execution_enabled": False}

    def generate_professional_signal(
        self,
        symbol: str,
        candles_by_tf: Dict[str, List[MarketDataPoint]],
        spread_pip: float = 1.0,
        account_balance: float = 10000.0
    ) -> UnifiedSignalContract:
        """
        Delegates signal generation directly to the integrated ProfessionalSignalEngine.
        Returns a UnifiedSignalContract containing the qualified BUY, SELL, or WAIT signal.
        """
        # Base hierarchy plus costed Base-re-entry profiles are the only signal source.
        # Conventional/indicator signal engines are deliberately not consulted here.
        try:
            self.last_base_behavior_report = self.base_behavior_monitor.analyze(
                candles_by_tf=candles_by_tf, now=datetime.now().astimezone()
            )
        except Exception as exc:
            self.last_base_behavior_report = {
                "status": "MONITOR_ERROR", "error": str(exc), "execution_enabled": False,
            }
        from src.Intelligence.Execution.strategy_orchestrator import StrategyOrchestrator
        import json
        tf_rank = {"MN1": 0, "W1": 1, "D1": 2, "H4": 3, "H1": 4, "M30": 5, "M15": 6, "M5": 7, "M1": 8}
        normalized = {}
        for tf, rows in (candles_by_tf or {}).items():
            normalized[str(tf).upper()] = [
                {"timestamp": (p.Timestamp.isoformat() if hasattr(p.Timestamp, "isoformat") else str(p.Timestamp)),
                 "open": float(p.Open), "high": float(p.High), "low": float(p.Low),
                 "close": float(p.Close)}
                for p in rows
            ]
        primary_tf = max(normalized, key=lambda tf: tf_rank.get(tf, -1)) if normalized else "M1"
        candles = normalized.get(primary_tf, [])
        report = StrategyOrchestrator().evaluate_all_strategies(
            symbol=symbol, primary_timeframe=primary_tf, candles=candles,
            all_timeframe_candles=normalized, spread_pip=spread_pip,
        )
        candidate = report.get("best_candidate") or {}
        direction = str(candidate.get("direction", "WAIT")).upper()
        if direction not in ("BUY", "SELL"):
            direction = "WAIT"
        try:
            entry = float(candidate.get("entry") or 0.0)
            stop = float(candidate.get("stop_loss") or 0.0)
            target = float(candidate.get("take_profit") or 0.0)
            rr = float(candidate.get("risk_reward") or 0.0)
            confidence = float(candidate.get("confidence") or 0.0)
        except (TypeError, ValueError):
            direction, entry, stop, target, rr, confidence = "WAIT", 0.0, 0.0, 0.0, 0.0, 0.0
        if direction == "WAIT" or not all(v > 0 for v in (entry, stop, target, rr)):
            direction, entry, stop, target, rr = "WAIT", 0.0, 0.0, 0.0, 0.0
        self.last_base_behavior_report = {
            **self.last_base_behavior_report,
            "status": "BASE_SIGNAL_PROPOSED" if direction in ("BUY", "SELL") else "WAIT",
            "base_strategy_report": report, "execution_enabled": False,
        }
        return UnifiedSignalContract(
            signal_id=str(candidate.get("strategy_id") or uuid.uuid4()),
            symbol=symbol, timeframe=str(candidate.get("timeframe") or primary_tf),
            direction=direction, entry_price=entry, stop_loss=stop, take_profit=target,
            risk_reward=rr, confidence=confidence,
            pattern_id="BASE_HIERARCHY_REENTRY" if direction in ("BUY", "SELL") else "BASE_WAIT",
            market_context=json.dumps(self.last_base_behavior_report, default=str, ensure_ascii=False),
            created_at=datetime.now().astimezone().isoformat(),
        )

    def generate_hierarchical_base_plan(
        self,
        events_by_tf: Dict[str, List[Dict[str, Any]]],
        quote: Dict[str, float],
        now: float,
        historical_labels: Optional[List[Dict[str, Any]]] = None,
        learning_as_of: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Generate a Base parent/child analysis and pending-order proposal only.

        Historical labels are optional, but without sufficient prior labeled outcomes
        the Base engine fails closed and returns WAIT. No broker order is submitted.
        """
        if historical_labels is not None:
            self.base_behavior_engine.learn(
                events_by_tf=events_by_tf,
                labels=historical_labels,
                as_of=int(learning_as_of if learning_as_of is not None else now),
            )
        return self.base_behavior_engine.analyze(events_by_tf=events_by_tf, quote=quote, now=now)

    def analyze_multitimeframe_base_behavior(
        self,
        candles_by_tf: Dict[str, List[MarketDataPoint]],
        now: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Analyze closed Base behavior across supplied timeframes.

        The result includes detected zones, nested parent/child links, revisit
        counts/depth/MFE/MAE, and an explicit WAIT decision until the strategy
        has validated costed historical edge. This method never places orders.
        Candle inputs are expected to be MarketDataPoint sequences keyed by TF.
        """
        if now is None:
            now = datetime.now().astimezone()
        return self.base_behavior_monitor.analyze(candles_by_tf=candles_by_tf, now=now)

    def evaluate_decision(self, context: DecisionContext) -> DecisionResult:
        """
        Implements the traditional IDecisionEngine interface for backward compatibility.
        """
        decision_id = str(uuid.uuid4())
        total_weight = sum(context.AssetWeights.values()) if context.AssetWeights else 0.0

        if total_weight <= 0:
            state = DecisionState.NO_ACTION
            summary = "No asset allocation recommended."
            audit_status = "Skipped"
            confidence = 1.0
        elif total_weight > 1.5:
            state = DecisionState.REJECTED
            summary = "Total recommended allocation weight exceeds acceptable leverage constraints."
            audit_status = "Risk Check Failed"
            confidence = 0.90
        elif total_weight > 1.0:
            state = DecisionState.REVIEW_REQUIRED
            summary = "Allocation contains active leverage; review is required."
            audit_status = "Awaiting Verification"
            confidence = 0.85
        else:
            state = DecisionState.APPROVED
            summary = f"Allocation of {len(context.AssetWeights)} assets meets all standard constraints."
            audit_status = "Approved"
            confidence = 0.95

        reason = DecisionReason(
            AnalysisSummary=summary,
            RiskAuditStatus=audit_status,
            ConfidenceScore=confidence
        )

        return DecisionResult(
            DecisionId=decision_id,
            Context=context,
            State=state,
            Reason=reason,
            CreatedAt=datetime.now()
        )

    def evaluate_intelligence_context(
        self,
        context: DecisionIntelligenceContext
    ) -> DecisionIntelligenceReport:
        """
        Executes the advanced multi-dimensional decision evaluation workflow.
        """
        decision_id = str(uuid.uuid4())

        # 1. Structural Validation
        self.validator.validate_context(context)

        # 2. Analyze context
        analysis = self.analyzer.analyze_context(context)

        # 2b. Invoke ProfessionalSignalEngine if candle/market points exist in context
        prof_sig = None
        prof_sig_error = None
        if hasattr(context, "MarketDataPoints") and context.MarketDataPoints:
            try:
                symbol = getattr(context, "Asset", "XAUUSD")
                candles_by_tf = {"M15": context.MarketDataPoints} if isinstance(context.MarketDataPoints, list) else context.MarketDataPoints
                if isinstance(candles_by_tf, dict):
                    prof_sig = self.generate_professional_signal(symbol, candles_by_tf)
                    analysis.SupportingEvidence["professional_signal"] = prof_sig.__dict__ if hasattr(prof_sig, "__dict__") else str(prof_sig)
            except Exception as pe:
                prof_sig_error = str(pe)
                analysis.SupportingEvidence["professional_signal_error"] = prof_sig_error

        # 3. Evaluate decision quality
        quality_score = self.evaluator.evaluate_quality(context, analysis)

        # 4. Resolve layer conflicts
        conflict_result = self.conflict_resolver.resolve_conflicts(context, analysis)

        # 5. Collect evidence trail (propagates analysis.SupportingEvidence)
        evidence_trail = self.collector.collect_evidence(decision_id, context, analysis)

        # 6. Determine analytical Decision State derived from Professional Signal Engine
        if prof_sig_error:
            state = DecisionState.REVIEW_REQUIRED
        elif prof_sig:
            if prof_sig.direction in ["BUY", "SELL"]:
                state = DecisionState.APPROVED
            elif prof_sig.direction == "WAIT":
                market_ctx = getattr(prof_sig, "market_context", "") or ""
                pattern_id = getattr(prof_sig, "pattern_id", "") or ""
                risk_lvl = getattr(prof_sig, "risk_level", "") or ""
                if "REJECTED" in market_ctx or "REJECTED" in pattern_id or risk_lvl in ["HIGH_SPREAD_REJECTION", "REJECTED"]:
                    state = DecisionState.REJECTED
                else:
                    state = DecisionState.NO_ACTION
            else:
                state = DecisionState.NO_ACTION
        else:
            # No Base-only signal means no actionable approval. Research, scoring,
            # or generic allocation evidence cannot act as a fallback strategy.
            state = DecisionState.NO_ACTION
            analysis.SupportingEvidence["base_signal_missing"] = True


        # 7. Compile report
        report = self.report_builder.build_report(
            context=context,
            analysis=analysis,
            quality_score=quality_score,
            conflict_analysis=conflict_result,
            evidence_trail=evidence_trail,
            state=state
        )

        # 8. Validate final confidence level
        self.validator.validate_confidence(report.Confidence)

        # 9. Store in History
        self.history_store.record_decision(report)

        return report
