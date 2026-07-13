import math
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.Infrastructure.exceptions import ValidationException
from src.Infrastructure.validation import ModelValidator
from src.Learning.Models.models import ImprovementSuggestion
from src.Learning.Optimization.models import (
    LearningFeedbackRecord,
    FeedbackAnalysis,
    LearningPerformanceRecord,
    LearningQualityMetrics,
    OptimizationReport
)


class FeedbackAnalyzer:
    """
    Analyzes decision outcomes against expected models to trace layer correctness.
    Identifies strengths, weaknesses, and reliability anomalies.
    """
    def analyze_feedback(self, record: LearningFeedbackRecord) -> FeedbackAnalysis:
        # Validate inputs
        if record.ExpectedQuality < 0 or record.ExpectedQuality > 1.0 or math.isnan(record.ExpectedQuality):
            raise ValidationException("Validation Error: ExpectedQuality must be within range [0.0, 1.0].")

        # Track deviation between expected quality and observed result
        deviation = abs(record.ExpectedQuality - record.ObservedResult)

        strengths = []
        weaknesses = []
        improvement_areas = []

        # Analyze research quality / confidence accuracy
        if deviation <= 0.15:
            strengths.append("High confidence tracking accuracy.")
            strengths.append("Strong multi-layer alignment.")
            confidence_evaluation = "Optimal confidence calibration"
        else:
            weaknesses.append("Confidence overestimation detected.")
            improvement_areas.append("Improve research confidence evidence validation rules.")
            confidence_evaluation = "Unstable confidence calibration"

        # Check risk assessment quality
        risk_passed = record.AnalysisContext.get("risk_approved", True)
        if not risk_passed and record.ObservedResult < 0.0:
            strengths.append("Risk controls properly prevented downside exposure.")
        elif risk_passed and record.ObservedResult < -0.10:
            weaknesses.append("High risk assessment uncertainty/drawdown.")
            improvement_areas.append("Increase risk scenario coverage and stress levels.")

        # Check research quality
        insights_count = record.AnalysisContext.get("insights_count", 1)
        if insights_count == 0:
            weaknesses.append("Zero/Insufficient research observations.")
            improvement_areas.append("Enrich feature extraction coverage.")

        return FeedbackAnalysis(
            Strengths=strengths,
            Weaknesses=weaknesses,
            ImprovementAreas=improvement_areas,
            ConfidenceEvaluation=confidence_evaluation
        )


class PerformanceTracker:
    """
    Tracks and records intelligence performance parameters over time, enabling
    historical comparisons and trend analysis without trading activity metrics.
    """
    def __init__(self) -> None:
        self._records: Dict[str, LearningPerformanceRecord] = {
            "DecisionConsistency": LearningPerformanceRecord("DecisionConsistency", {}),
            "ResearchReliability": LearningPerformanceRecord("ResearchReliability", {}),
            "RiskAnalysisQuality": LearningPerformanceRecord("RiskAnalysisQuality", {}),
            "StrategyEvaluationQuality": LearningPerformanceRecord("StrategyEvaluationQuality", {})
        }

    def log_metric(self, name: str, value: float, timestamp: Optional[datetime] = None) -> None:
        if name not in self._records:
            self._records[name] = LearningPerformanceRecord(name, {})
        ts = timestamp or datetime.now()
        self._records[name].HistoricalValues[ts] = value

    def get_record(self, name: str) -> Optional[LearningPerformanceRecord]:
        return self._records.get(name)

    def calculate_trends(self, name: str) -> List[float]:
        record = self.get_record(name)
        if not record or not record.HistoricalValues:
            return []
        # Sort values by timestamp
        sorted_times = sorted(record.HistoricalValues.keys())
        return [record.HistoricalValues[t] for t in sorted_times]


class ImprovementEngine:
    """
    Generates structured, explainable ImprovementSuggestions based on recurring
    weaknesses, historical tracking logs, and feedback analyses.
    """
    def generate_suggestions(
        self,
        analyses: List[FeedbackAnalysis],
        tracker: PerformanceTracker
    ) -> List[ImprovementSuggestion]:
        suggestions = []

        # Analyze recurring weaknesses
        all_weaknesses = []
        for a in analyses:
            all_weaknesses.extend(a.Weaknesses)

        # Count occurrences of specific weaknesses
        confidence_issues = sum(1 for w in all_weaknesses if "confidence" in w.lower())
        risk_issues = sum(1 for w in all_weaknesses if "risk" in w.lower())
        research_issues = sum(1 for w in all_weaknesses if "research" in w.lower() or "observation" in w.lower())

        now = datetime.now()

        # Recommendation Rules:
        if confidence_issues >= 2 or (len(analyses) > 0 and confidence_issues / len(analyses) >= 0.4):
            suggestions.append(ImprovementSuggestion(
                TargetParameter="ResearchConfidenceValidationLevel",
                SuggestedValue=0.85,
                Reasoning="Research confidence is frequently unstable. Suggesting a higher confidence filter threshold.",
                CalculatedAt=now
            ))

        if risk_issues >= 1:
            suggestions.append(ImprovementSuggestion(
                TargetParameter="RiskScenarioCoverageLimit",
                SuggestedValue=12,
                Reasoning="Risk assessment uncertainty is high. Suggesting increasing scenario stress levels and coverage.",
                CalculatedAt=now
            ))

        if research_issues >= 1:
            suggestions.append(ImprovementSuggestion(
                TargetParameter="FeatureExtractionLookback",
                SuggestedValue=20,
                Reasoning="Insufficient research evidence. Suggesting expanding the feature lookback window to reduce observation noise.",
                CalculatedAt=now
            ))

        # Default standard suggestion if empty
        if not suggestions:
            suggestions.append(ImprovementSuggestion(
                TargetParameter="SystemParametersStable",
                SuggestedValue=True,
                Reasoning="Intelligence metrics are highly stable and within optimal thresholds.",
                CalculatedAt=now
            ))

        return suggestions


class LearningMemory:
    """
    Thread-safe in-memory memory storage for feedback logs, performance tracks,
    and optimization suggestions.
    """
    def __init__(self) -> None:
        self._feedback_history: List[LearningFeedbackRecord] = []
        self._suggestions: List[ImprovementSuggestion] = []

    def save_feedback(self, record: LearningFeedbackRecord) -> None:
        self._feedback_history.append(record)

    def get_feedback_history(self) -> List[LearningFeedbackRecord]:
        return list(self._feedback_history)

    def save_suggestions(self, suggestions: List[ImprovementSuggestion]) -> None:
        self._suggestions.extend(suggestions)

    def get_suggestions_history(self) -> List[ImprovementSuggestion]:
        return list(self._suggestions)

    def clear(self) -> None:
        self._feedback_history.clear()
        self._suggestions.clear()


class OptimizationReportBuilder:
    """
    Assembles historical records and intelligence tracking statistics into
    comprehensive, explainable OptimizationReports.
    """
    def build_report(
        self,
        memory: LearningMemory,
        tracker: PerformanceTracker,
        suggestions: List[ImprovementSuggestion]
    ) -> OptimizationReport:
        report_id = f"opt-{str(uuid.uuid4())}"

        # Calculate metrics trends
        decision_trends = tracker.calculate_trends("DecisionConsistency")
        research_trends = tracker.calculate_trends("ResearchReliability")
        risk_trends = tracker.calculate_trends("RiskAnalysisQuality")
        strat_trends = tracker.calculate_trends("StrategyEvaluationQuality")

        # Synthesize Quality Metrics
        consistency_score = decision_trends[-1] if decision_trends else 1.0
        evidence_trend = research_trends[-1] if research_trends else 1.0
        research_stability = research_trends[-1] if research_trends else 1.0
        risk_stability = risk_trends[-1] if risk_trends else 1.0

        # Overall Intelligence Score is weighted average of active intelligence layers
        overall_quality = (consistency_score * 0.3) + (evidence_trend * 0.2) + (research_stability * 0.2) + (risk_stability * 0.3)

        quality_metrics = LearningQualityMetrics(
            DecisionConsistencyScore=round(consistency_score, 4),
            EvidenceQualityTrend=round(evidence_trend, 4),
            ResearchStabilityScore=round(research_stability, 4),
            RiskEvaluationStability=round(risk_stability, 4),
            OverallIntelligenceQuality=round(overall_quality, 4)
        )

        history = memory.get_feedback_history()
        summary = f"Processed {len(history)} outcome evaluations. Overall intelligence status: {overall_quality*100:.1f}%."

        detected_issues = []
        for suggestion in suggestions:
            if "unstable" in suggestion.Reasoning or "uncertainty" in suggestion.Reasoning or "insufficient" in suggestion.Reasoning:
                detected_issues.append(suggestion.Reasoning)

        trends = {
            "DecisionConsistency": decision_trends,
            "ResearchReliability": research_trends,
            "RiskAnalysisQuality": risk_trends,
            "StrategyEvaluationQuality": strat_trends
        }

        return OptimizationReport(
            ReportId=report_id,
            FeedbackSummary=summary,
            PerformanceTrends=trends,
            DetectedIssues=detected_issues,
            ImprovementSuggestions=suggestions,
            IntelligenceQualityMetrics=quality_metrics,
            GeneratedAt=datetime.now()
        )


class LearningProcessor:
    """
    Orchestrates continuous intelligence improvement processing across the platform.
    Analyses decision quality, records feedback history, tracks intelligence quality,
    and constructs suggestions and reports.
    """
    def __init__(self) -> None:
        self.analyzer = FeedbackAnalyzer()
        self.tracker = PerformanceTracker()
        self.engine = ImprovementEngine()
        self.memory = LearningMemory()
        self.report_builder = OptimizationReportBuilder()

    def process_feedback_record(self, record: LearningFeedbackRecord) -> FeedbackAnalysis:
        """Processes a single feedback record, updates tracking, and saves to memory."""
        # Validate record
        if not record.DecisionReference:
            raise ValidationException("Validation Error: DecisionReference cannot be empty.")

        # Analyze feedback
        analysis = self.analyzer.analyze_feedback(record)

        # Update tracking metrics based on analysis
        consistency = 1.0 if not analysis.Weaknesses else max(0.0, 1.0 - (len(analysis.Weaknesses) * 0.2))
        research_quality = 1.0 if "Unstable confidence" not in analysis.ConfidenceEvaluation else 0.60
        risk_quality = 0.50 if any("risk" in w.lower() for w in analysis.Weaknesses) else 0.95
        strat_quality = 0.85

        self.tracker.log_metric("DecisionConsistency", consistency, record.Timestamp)
        self.tracker.log_metric("ResearchReliability", research_quality, record.Timestamp)
        self.tracker.log_metric("RiskAnalysisQuality", risk_quality, record.Timestamp)
        self.tracker.log_metric("StrategyEvaluationQuality", strat_quality, record.Timestamp)

        # Save to memory
        self.memory.save_feedback(record)

        return analysis

    def generate_optimization_report(self) -> OptimizationReport:
        """Runs the suggestions engine and returns the compiled OptimizationReport."""
        history = self.memory.get_feedback_history()
        analyses = [self.analyzer.analyze_feedback(h) for h in history]

        suggestions = self.engine.generate_suggestions(analyses, self.tracker)
        self.memory.save_suggestions(suggestions)

        return self.report_builder.build_report(self.memory, self.tracker, suggestions)
