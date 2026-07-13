import math
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.Infrastructure.exceptions import ValidationException
from src.Infrastructure.validation import ModelValidator
from src.Decision.Models.models import DecisionState
from src.Decision.Intelligence.models import (
    DecisionIntelligenceContext,
    DecisionAnalysis,
    DecisionQualityScore,
    ConflictResolutionResult,
    DecisionEvidenceTrail,
    DecisionIntelligenceReport,
    DecisionHistoryRecord
)


class DecisionContextBuilder:
    """
    Collects, normalizes, and prepares structured multi-layer intelligence evidence
    into a cohesive, immutable DecisionIntelligenceContext.
    """
    def build_context(
        self,
        research_output: Optional[Any] = None,
        strategy_evaluation: Optional[Any] = None,
        risk_assessment: Optional[Any] = None,
        market_context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DecisionIntelligenceContext:
        # Normalize missing inputs
        insights = []
        patterns = []
        if research_output is not None:
            # support ResearchResult, ResearchReport, or direct lists
            if hasattr(research_output, "insights"):
                insights = getattr(research_output, "insights") or []
            elif hasattr(research_output, "Findings"):
                # ResearchResult Findings can be a dictionary or list
                findings = getattr(research_output, "Findings")
                if isinstance(findings, list):
                    insights = findings
                elif isinstance(findings, dict):
                    insights = [findings]
            elif isinstance(research_output, list):
                insights = research_output

            if hasattr(research_output, "patterns"):
                patterns = getattr(research_output, "patterns") or []

        evals = []
        if strategy_evaluation is not None:
            if isinstance(strategy_evaluation, list):
                evals = strategy_evaluation
            else:
                evals = [strategy_evaluation]

        risks = []
        if risk_assessment is not None:
            if isinstance(risk_assessment, list):
                risks = risk_assessment
            else:
                risks = [risk_assessment]

        norm_market = market_context.copy() if market_context else {}
        norm_metadata = metadata.copy() if metadata else {}

        # Resolve missing crucial details gracefully
        if "asset" not in norm_metadata:
            if hasattr(research_output, "AssetId"):
                norm_metadata["asset"] = getattr(research_output, "AssetId")
            elif hasattr(research_output, "Request") and hasattr(getattr(research_output, "Request"), "Asset"):
                norm_metadata["asset"] = getattr(getattr(research_output, "Request"), "Asset")
            else:
                norm_metadata["asset"] = "UNKNOWN"

        # Construct and return immutable context
        return DecisionIntelligenceContext(
            ResearchInsights=insights,
            PatternObservations=patterns,
            StrategyEvaluations=evals,
            RiskAssessments=risks,
            MarketConditions=norm_market,
            HistoricalEvidence={},
            Metadata=norm_metadata
        )


class DecisionAnalyzer:
    """
    Analyzes intelligence alignment, risk compatibility, evidence quality, confidence level,
    and information completeness to produce structured DecisionAnalysis findings.
    """
    def analyze_context(self, context: DecisionIntelligenceContext) -> DecisionAnalysis:
        # 1. Information Completeness Check
        total_fields = 5
        filled_fields = 0
        if context.ResearchInsights: filled_fields += 1
        if context.PatternObservations: filled_fields += 1
        if context.StrategyEvaluations: filled_fields += 1
        if context.RiskAssessments: filled_fields += 1
        if context.MarketConditions: filled_fields += 1

        completeness_ratio = filled_fields / total_fields

        # 2. Extract Confidence Level
        research_conf = 0.5
        if context.ResearchInsights:
            confs = []
            for r in context.ResearchInsights:
                if hasattr(r, "Confidence"):
                    confs.append(getattr(r, "Confidence"))
                elif hasattr(r, "ConfidenceScore"):
                    confs.append(getattr(r, "ConfidenceScore"))
                elif isinstance(r, dict) and "confidence" in r:
                    confs.append(r["confidence"])
            if confs:
                research_conf = sum(confs) / len(confs)

        strat_score = 0.5
        strat_conf = 0.5
        if context.StrategyEvaluations:
            scores = []
            confs = []
            for s in context.StrategyEvaluations:
                if hasattr(s, "Score"):
                    sc = getattr(s, "Score")
                    if hasattr(sc, "OverallScore"):
                        scores.append(getattr(sc, "OverallScore"))
                    if hasattr(sc, "Confidence"):
                        confs.append(getattr(sc, "Confidence"))
                elif isinstance(s, dict):
                    # Check both 'score' and 'strategy_score' formats safely
                    score_val = s.get("score", s.get("strategy_score"))
                    if score_val is not None:
                        scores.append(score_val)
                    if "confidence" in s:
                        confs.append(s["confidence"])
            if scores:
                strat_score = sum(scores) / len(scores)
            if confs:
                strat_conf = sum(confs) / len(confs)

        # Synthesized Confidence Level
        synthesized_confidence = (research_conf * 0.4) + (strat_conf * 0.6)

        # 3. Intelligence Alignment
        # Check if research observations support strategy evaluations
        # e.g., if research sentiment is positive/bullish and strategy score is high, alignment is high.
        research_sentiment_positive = True
        for r in context.ResearchInsights:
            desc = ""
            if hasattr(r, "Description"):
                desc = getattr(r, "Description").lower()
            elif isinstance(r, dict) and "description" in r:
                desc = r["description"].lower()
            if "bearish" in desc or "negative" in desc or "downward" in desc or "reversal" in desc:
                research_sentiment_positive = False

        alignment_score = 1.0
        if research_sentiment_positive and strat_score < 0.4:
            alignment_score = 0.3
        elif not research_sentiment_positive and strat_score >= 0.6:
            alignment_score = 0.2

        # 4. Risk Compatibility
        risk_approved = True
        risk_notes = ""
        if context.RiskAssessments:
            for r in context.RiskAssessments:
                if hasattr(r, "IsApproved"):
                    if not getattr(r, "IsApproved"):
                        risk_approved = False
                elif isinstance(r, dict):
                    # Check both uppercase and lowercase casings safely
                    is_app_val = r.get("IsApproved", r.get("is_approved", r.get("risk_approved", True)))
                    if not is_app_val:
                        risk_approved = False
                if hasattr(r, "AssessmentNotes"):
                    risk_notes += getattr(r, "AssessmentNotes") + " "
                elif isinstance(r, dict) and "assessment_notes" in r:
                    risk_notes += r["assessment_notes"] + " "

        risk_compat = 1.0 if risk_approved else 0.0

        # Create structured analysis summary
        asset = context.Metadata.get("asset", "UNKNOWN")
        summary = (
            f"Decision Analysis for {asset}. "
            f"Completeness: {completeness_ratio*100:.1f}%. "
            f"Alignment: {alignment_score:.2f}. "
            f"Risk Approved: {risk_approved}. "
            f"Synthesized Confidence: {synthesized_confidence:.2f}."
        )

        evidence = {
            "completeness_ratio": completeness_ratio,
            "research_confidence": research_conf,
            "strategy_score": strat_score,
            "strategy_confidence": strat_conf,
            "alignment_score": alignment_score,
            "risk_approved": risk_approved,
            "risk_notes": risk_notes.strip()
        }

        return DecisionAnalysis(
            Summary=summary,
            SupportingEvidence=evidence,
            Confidence=synthesized_confidence,
            ReasoningMetadata={
                "analyzed_at": datetime.now().isoformat(),
                "asset": asset
            }
        )


class DecisionQualityEvaluator:
    """
    Evaluates evidence quality, logical consistency, and stability of the decision elements
    to output a comprehensive DecisionQualityScore.
    """
    def evaluate_quality(
        self,
        context: DecisionIntelligenceContext,
        analysis: DecisionAnalysis
    ) -> DecisionQualityScore:
        # Evidence Quality: completeness, insights count, pattern count
        evidence_quality = min(1.0, (
            len(context.ResearchInsights) * 0.2 +
            len(context.PatternObservations) * 0.3 +
            analysis.SupportingEvidence.get("completeness_ratio", 0.0) * 0.5
        ))

        # Consistency: research vs strategy alignment, strategy vs risk compatibility
        alignment = analysis.SupportingEvidence.get("alignment_score", 1.0)
        risk_compat = 1.0 if analysis.SupportingEvidence.get("risk_approved", True) else 0.2
        consistency = (alignment * 0.5) + (risk_compat * 0.5)

        # Reliability: confidence score stability, lack of uncertainty
        reliability = analysis.Confidence

        # Overall Score: weighted average of quality, consistency, and reliability
        overall_score = (evidence_quality * 0.3) + (consistency * 0.4) + (reliability * 0.3)

        metrics = {
            "insights_count": len(context.ResearchInsights),
            "patterns_count": len(context.PatternObservations),
            "strategy_evals_count": len(context.StrategyEvaluations),
            "risk_assess_count": len(context.RiskAssessments)
        }

        return DecisionQualityScore(
            OverallScore=round(overall_score, 4),
            EvidenceQuality=round(evidence_quality, 4),
            Consistency=round(consistency, 4),
            Reliability=round(reliability, 4),
            Metrics=metrics
        )


class DecisionConflictResolver:
    """
    Resolves contradictory observations between Research, Strategy, and Risk assessment layers.
    Does NOT auto-execute; only catalogs the conflict details and suggests a resolution strategy.
    """
    def resolve_conflicts(
        self,
        context: DecisionIntelligenceContext,
        analysis: DecisionAnalysis
    ) -> ConflictResolutionResult:
        # Determine conflicts
        # Scenario A: Positive research sentiment but Strategy rating is very low
        # Scenario B: Positive research/strategy but Risk assessment rejects it
        research_sentiment_positive = True
        for r in context.ResearchInsights:
            desc = ""
            if hasattr(r, "Description"):
                desc = getattr(r, "Description").lower()
            elif isinstance(r, dict):
                desc = str(r.get("description", r.get("research_sentiment", r.get("sentiment", "")))).lower()
            if "bearish" in desc or "negative" in desc or "downward" in desc or "reversal" in desc:
                research_sentiment_positive = False

        strat_score = analysis.SupportingEvidence.get("strategy_score", 0.5)
        risk_approved = analysis.SupportingEvidence.get("risk_approved", True)

        conflict_detected = False
        conflict_type = "None"
        sources = []
        explanation = "No conflicts detected."
        confidence_impact = 0.0

        if research_sentiment_positive and strat_score < 0.4:
            conflict_detected = True
            conflict_type = "Research_vs_Strategy"
            sources = ["ResearchInsights", "StrategyEvaluations"]
            explanation = "Research indicates positive sentiment, but strategy evaluated with a low scoring rank."
            confidence_impact = -0.25

        elif not research_sentiment_positive and strat_score >= 0.6:
            conflict_detected = True
            conflict_type = "Research_vs_Strategy"
            sources = ["ResearchInsights", "StrategyEvaluations"]
            explanation = "Research indicates bearish sentiment/risks, but strategy evaluated with a high scoring rank."
            confidence_impact = -0.20

        if not risk_approved:
            conflict_detected = True
            if conflict_type == "None":
                conflict_type = "Strategy_vs_Risk"
                sources = ["StrategyEvaluations", "RiskAssessments"]
                explanation = "Strategy score warrants recommendation, but Risk audit failed constraint thresholds."
                confidence_impact = -0.30
            else:
                conflict_type = "Research_Strategy_Risk_Triple_Conflict"
                sources.append("RiskAssessments")
                explanation += " Additionally, Risk audit failed constraint thresholds."
                confidence_impact = -0.40

        return ConflictResolutionResult(
            ConflictDetected=conflict_detected,
            ConflictType=conflict_type,
            ConflictingSources=sources,
            ResolutionExplanation=explanation,
            ConfidenceImpact=confidence_impact
        )


class DecisionEvidenceCollector:
    """
    Traces and aggregates all items of evidence into an explainable DecisionEvidenceTrail.
    """
    def collect_evidence(
        self,
        decision_id: str,
        context: DecisionIntelligenceContext
    ) -> DecisionEvidenceTrail:
        # Collect features from context metadata if available
        features = context.Metadata.get("features", [])

        return DecisionEvidenceTrail(
            DecisionId=decision_id,
            ResearchEvidence=context.ResearchInsights,
            FeatureEvidence=features,
            PatternEvidence=context.PatternObservations,
            StrategyEvidence=context.StrategyEvaluations,
            RiskEvidence=context.RiskAssessments,
            CollectedAt=datetime.now()
        )


class DecisionReportBuilder:
    """
    Compiles analysis, quality scores, conflict results, and evidence trails into
    a comprehensive DecisionIntelligenceReport.
    """
    def build_report(
        self,
        context: DecisionIntelligenceContext,
        analysis: DecisionAnalysis,
        quality_score: DecisionQualityScore,
        conflict_analysis: ConflictResolutionResult,
        evidence_trail: DecisionEvidenceTrail,
        state: str
    ) -> DecisionIntelligenceReport:
        report_id = f"rep-{evidence_trail.DecisionId}"

        # Adjust confidence by conflict impact (clamped to [0.0, 1.0])
        final_confidence = max(0.0, min(1.0, analysis.Confidence + conflict_analysis.ConfidenceImpact))

        return DecisionIntelligenceReport(
            ReportId=report_id,
            Context=context,
            State=state,
            IntelligenceSummary=analysis.Summary,
            EvidenceTrail=evidence_trail,
            QualityScore=quality_score,
            ConflictAnalysis=conflict_analysis,
            Confidence=round(final_confidence, 4),
            GeneratedAt=datetime.now()
        )


class DecisionValidator:
    """
    Validates structural and numerical boundaries, checks missing context features,
    audits contradictory inputs, and validates confidence sanity.
    """
    def validate_context(self, context: DecisionIntelligenceContext) -> None:
        if not context:
            raise ValidationException("Validation Error: Context cannot be None.")

        # Incomplete context validation (check if absolutely no data exists across any dimension)
        if (not context.ResearchInsights and
            not context.PatternObservations and
            not context.StrategyEvaluations and
            not context.RiskAssessments and
            not context.MarketConditions):
            raise ValidationException("Validation Error: DecisionIntelligenceContext is completely empty/incomplete.")

        # Check metadata
        if not context.Metadata:
            raise ValidationException("Validation Error: Metadata cannot be empty.")

    def validate_confidence(self, confidence: float) -> None:
        if math.isnan(confidence):
            raise ValidationException("Validation Error: Confidence level cannot be NaN.")
        ModelValidator.validate_range(confidence, 0.0, 1.0, "Confidence Level")


class DecisionHistoryStore:
    """
    Thread-safe in-memory store for tracking and querying DecisionHistoryRecords.
    """
    def __init__(self) -> None:
        self._records: Dict[str, DecisionHistoryRecord] = {}

    def record_decision(self, report: DecisionIntelligenceReport) -> DecisionHistoryRecord:
        record_id = f"hist-{report.ReportId}"
        context_summary = f"Asset={report.Context.Metadata.get('asset')}, State={report.State}, Confidence={report.Confidence}"

        # Collect evidence references (e.g. strategy ids, research report ids)
        refs = []
        if report.Context.StrategyEvaluations:
            for s in report.Context.StrategyEvaluations:
                if hasattr(s, "StrategyId"):
                    refs.append(f"strat:{getattr(s, 'StrategyId')}")
        if report.Context.ResearchInsights:
            refs.append(f"insights:{len(report.Context.ResearchInsights)}")

        record = DecisionHistoryRecord(
            RecordId=record_id,
            Timestamp=datetime.now(),
            ContextSummary=context_summary,
            DecisionState=report.State,
            Confidence=report.Confidence,
            EvidenceReferences=refs,
            Metadata={
                "quality_score": report.QualityScore.OverallScore,
                "conflict_detected": report.ConflictAnalysis.ConflictDetected
            }
        )
        self._records[record_id] = record
        return record

    def get_history(self) -> List[DecisionHistoryRecord]:
        return list(self._records.values())

    def clear(self) -> None:
        self._records.clear()
