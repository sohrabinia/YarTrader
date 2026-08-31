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
        self.signal_engine = signal_engine or ProfessionalSignalEngine()

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
        return self.signal_engine.generate_unified_signal(
            symbol=symbol,
            candles_by_tf=candles_by_tf,
            spread_pip=spread_pip,
            account_balance=account_balance
        )

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
                    prof_sig = self.signal_engine.generate_unified_signal(symbol, candles_by_tf)
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
            state = DecisionState.APPROVED
            if not context.StrategyEvaluations or not context.ResearchInsights:
                state = DecisionState.REVIEW_REQUIRED

            risk_approved = analysis.SupportingEvidence.get("risk_approved", True)
            if not risk_approved:
                state = DecisionState.REJECTED

            has_weights = False
            if context.StrategyEvaluations:
                for s in context.StrategyEvaluations:
                    if hasattr(s, "Score") and getattr(s, "Score").OverallScore > 0:
                        has_weights = True
                    elif isinstance(s, dict) and s.get("score", 0.0) > 0:
                        has_weights = True
            if not has_weights and state == DecisionState.APPROVED:
                state = DecisionState.NO_ACTION

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
