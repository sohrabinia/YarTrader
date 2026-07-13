import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from src.Infrastructure.exceptions import ValidationException
from src.Research.MarketAnalysis.Interfaces.interfaces import IResearchEngine
from src.Research.MarketAnalysis.Models.models import MarketObservation, MarketInsight, ResearchRequest, ResearchResult
from src.Research.Features.models import MarketFeatureSet
from src.Research.Engine.models import PatternObservation, ResearchReport


class ObservationAnalyzer:
    """Analyzes market feature relationships and behavioral states to produce MarketObservations."""

    def analyze_features(self, feature_set: MarketFeatureSet) -> List[MarketObservation]:
        if not feature_set.Features:
            raise ValidationException("Validation Error: Cannot analyze empty feature set.")

        observations: List[MarketObservation] = []
        asset = feature_set.AssetId
        timestamp = feature_set.EndTime

        # 1. Volatility State Analysis
        vol_feature = feature_set.Features.get("rolling_volatility")
        vol_state_feature = feature_set.Features.get("volatility_state")
        if vol_feature and vol_state_feature:
            vol_val = vol_feature.Value
            vol_state = vol_state_feature.Value
            if vol_state == "high":
                observations.append(MarketObservation(
                    Asset=asset,
                    Timestamp=timestamp,
                    Observations={
                        "condition": "Increasing Volatility State",
                        "volatility_value": vol_val,
                        "description": f"Asset {asset} exhibits high rolling annualized volatility of {vol_val:.2%}"
                    },
                    Source="ObservationAnalyzer"
                ))
            elif vol_state == "low":
                observations.append(MarketObservation(
                    Asset=asset,
                    Timestamp=timestamp,
                    Observations={
                        "condition": "Range Compression State",
                        "volatility_value": vol_val,
                        "description": f"Asset {asset} exhibits range compression with low volatility of {vol_val:.2%}"
                    },
                    Source="ObservationAnalyzer"
                ))

        # 2. Trend Behavior Analysis
        trend_feature = feature_set.Features.get("trend_strength_classification")
        return_feature = feature_set.Features.get("percentage_return")
        if trend_feature and return_feature:
            trend = trend_feature.Value
            ret = return_feature.Value
            if "strong" in str(trend):
                observations.append(MarketObservation(
                    Asset=asset,
                    Timestamp=timestamp,
                    Observations={
                        "condition": "Stable Trend Behavior",
                        "trend_direction": trend,
                        "percentage_return": ret,
                        "description": f"Asset {asset} exhibits a stable {trend} trend with a return of {ret:.2%}"
                    },
                    Source="ObservationAnalyzer"
                ))

        # 3. Range Expansion Analysis
        expansion_feature = feature_set.Features.get("range_expansion")
        if expansion_feature:
            expansion = expansion_feature.Value
            if expansion > 1.2:
                observations.append(MarketObservation(
                    Asset=asset,
                    Timestamp=timestamp,
                    Observations={
                        "condition": "Market Transition Condition",
                        "range_expansion": expansion,
                        "description": f"Asset {asset} shows significant high-low range expansion of {expansion:.2f}x"
                    },
                    Source="ObservationAnalyzer"
                ))

        # Default fallback observation to ensure we always have at least one observation
        if not observations:
            observations.append(MarketObservation(
                Asset=asset,
                Timestamp=timestamp,
                Observations={
                    "condition": "Standard Market Condition",
                    "description": f"Asset {asset} exhibits neutral baseline features."
                },
                Source="ObservationAnalyzer"
            ))

        return observations


class PatternDetector:
    """Discovers historical behavioral pattern matches based on market observations and features."""

    def detect_patterns(
        self,
        observations: List[MarketObservation],
        feature_set: Optional[MarketFeatureSet] = None
    ) -> List[PatternObservation]:
        patterns: List[PatternObservation] = []
        timestamp = datetime.now()

        conditions = {obs.Observations.get("condition") for obs in observations if obs.Observations}

        # 1. Volatility Expansion / Breakout Pattern
        if "Increasing Volatility State" in conditions and "Market Transition Condition" in conditions:
            patterns.append(PatternObservation(
                PatternName="Volatility Expansion Breakthrough Pattern",
                Description="Coincidence of high volatility and high-low range expansion indicates structural breakout.",
                Confidence=0.85,
                Timestamp=timestamp,
                MatchedFeatures=["rolling_volatility", "range_expansion"],
                Metadata={"regime_shift": True}
            ))

        # 2. Mean Reversion Structural Pattern
        if "Range Compression State" in conditions:
            patterns.append(PatternObservation(
                PatternName="Mean Reversion Structural Pattern",
                Description="Sustained range compression with low volatility typically precedes standard mean reversion behavior.",
                Confidence=0.75,
                Timestamp=timestamp,
                MatchedFeatures=["rolling_volatility", "volatility_state"],
                Metadata={"potential_breakout_direction": "unknown"}
            ))

        # 3. Strong Directional Momentum Pattern
        if "Stable Trend Behavior" in conditions:
            patterns.append(PatternObservation(
                PatternName="Strong Directional Momentum Pattern",
                Description="Stable trend direction supported by high percentage returns suggests sustained directional momentum.",
                Confidence=0.80,
                Timestamp=timestamp,
                MatchedFeatures=["trend_strength_classification", "percentage_return"],
                Metadata={"directional_bias": "confirmed"}
            ))

        return patterns


class InsightGenerator:
    """Converts structured observations and patterns into standard qualitative MarketInsights."""

    def generate_insights(
        self,
        observations: List[MarketObservation],
        patterns: List[PatternObservation]
    ) -> List[MarketInsight]:
        insights: List[MarketInsight] = []
        timestamp = datetime.now()

        # 1. Volatility Insights
        vol_patterns = [p for p in patterns if "Volatility" in p.PatternName]
        if vol_patterns:
            top_pat = vol_patterns[0]
            insights.append(MarketInsight(
                Category="VolatilityState",
                Description=f"Descriptive Insight: {top_pat.Description} Identified matched features: {', '.join(top_pat.MatchedFeatures)}.",
                Confidence=top_pat.Confidence,
                CreatedAt=timestamp
            ))

        # 2. Momentum Insights
        mom_patterns = [p for p in patterns if "Momentum" in p.PatternName]
        if mom_patterns:
            top_pat = mom_patterns[0]
            insights.append(MarketInsight(
                Category="TrendAnalysis",
                Description=f"Descriptive Insight: {top_pat.Description} (Directional Bias: {top_pat.Metadata.get('directional_bias')}).",
                Confidence=top_pat.Confidence,
                CreatedAt=timestamp
            ))

        # 3. Mean Reversion Insights
        mr_patterns = [p for p in patterns if "Mean Reversion" in p.PatternName]
        if mr_patterns:
            top_pat = mr_patterns[0]
            insights.append(MarketInsight(
                Category="MarketRegime",
                Description=f"Descriptive Insight: {top_pat.Description}",
                Confidence=top_pat.Confidence,
                CreatedAt=timestamp
            ))

        # Fallback Insight
        if not insights:
            insights.append(MarketInsight(
                Category="GeneralAnalysis",
                Description="Baseline market analysis shows neutral price-volatility structures.",
                Confidence=0.50,
                CreatedAt=timestamp
            ))

        return insights


class ResearchReportBuilder:
    """Generates structural ResearchReports summarizing the full research outputs."""

    def build_report(
        self,
        asset_id: str,
        start_time: datetime,
        end_time: datetime,
        observations: List[MarketObservation],
        patterns: List[PatternObservation],
        insights: List[MarketInsight],
        metadata: Optional[Dict[str, Any]] = None
    ) -> ResearchReport:
        report_id = f"rpt-{asset_id}-{uuid.uuid4().hex[:8]}"
        meta = metadata or {}
        return ResearchReport(
            ReportId=report_id,
            AssetId=asset_id,
            StartTime=start_time,
            EndTime=end_time,
            Observations=observations,
            Patterns=patterns,
            Insights=insights,
            Metadata=meta,
            GeneratedAt=datetime.now()
        )


class ResearchEngine(IResearchEngine):
    """
    Evolved Research Engine coordinating ObservationAnalyzer, PatternDetector,
    InsightGenerator, and ResearchReportBuilder to deliver comprehensive descriptive insights.
    """

    def __init__(
        self,
        analyzer: Optional[ObservationAnalyzer] = None,
        detector: Optional[PatternDetector] = None,
        generator: Optional[InsightGenerator] = None,
        builder: Optional[ResearchReportBuilder] = None
    ) -> None:
        self._analyzer = analyzer or ObservationAnalyzer()
        self._detector = detector or PatternDetector()
        self._generator = generator or InsightGenerator()
        self._builder = builder or ResearchReportBuilder()

    def analyze_market(self, request: ResearchRequest) -> ResearchResult:
        """
        Processes a ResearchRequest containing a MarketFeatureSet, orchestrates research sub-components,
        and packages a ResearchReport into the ResearchResult findings.
        """
        # Retrieve MarketFeatureSet from request context
        feature_set = request.Context.get("market_feature_set")
        if not feature_set or not isinstance(feature_set, MarketFeatureSet):
            # Fallback: if market_feature_set is missing, try to reconstruct/mock or raise ValidationException
            # Since strict errors are expected:
            raise ValidationException(
                "Validation Error: MarketFeatureSet is missing or invalid in ResearchRequest Context."
            )

        # 1. Observation Analysis
        observations = self._analyzer.analyze_features(feature_set)

        # 2. Pattern Detection
        patterns = self._detector.detect_patterns(observations, feature_set)

        # 3. Insight Generation
        insights = self._generator.generate_insights(observations, patterns)

        # 4. Report Construction
        report = self._builder.build_report(
            asset_id=request.Asset,
            start_time=request.StartTime,
            end_time=request.EndTime,
            observations=observations,
            patterns=patterns,
            insights=insights,
            metadata=request.Context.get("report_metadata", {})
        )

        # 5. Format results into structured findings package
        findings = {
            "asset_id": report.AssetId,
            "period_start": report.StartTime.isoformat(),
            "period_end": report.EndTime.isoformat(),
            "report_id": report.ReportId,
            "observations_count": len(report.Observations),
            "patterns_count": len(report.Patterns),
            "insights_count": len(report.Insights),
            "observations": [
                {
                    "timestamp": obs.Timestamp.isoformat(),
                    "observations": obs.Observations,
                    "source": obs.Source
                }
                for obs in report.Observations
            ],
            "patterns": [
                {
                    "name": p.PatternName,
                    "description": p.Description,
                    "confidence": p.Confidence,
                    "timestamp": p.Timestamp.isoformat(),
                    "matched_features": p.MatchedFeatures
                }
                for p in report.Patterns
            ],
            "insights": [
                {
                    "category": ins.Category,
                    "description": ins.Description,
                    "confidence": ins.Confidence,
                    "created_at": ins.CreatedAt.isoformat()
                }
                for ins in report.Insights
            ],
            "generated_at": report.GeneratedAt.isoformat(),
            "status": "completed"
        }

        # Determine overall confidence as average or max of insights
        confidence = 0.50
        if report.Insights:
            confidence = sum(ins.Confidence for ins in report.Insights) / len(report.Insights)

        return ResearchResult(
            Request=request,
            Findings=findings,
            ConfidenceScore=confidence,
            CreatedAt=datetime.now()
        )
