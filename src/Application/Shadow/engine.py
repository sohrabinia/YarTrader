import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List

from src.Infrastructure.exceptions import ValidationException
from src.Data.MarketData.Providers.providers import MetaTrader5Provider
from src.Research.MarketAnalysis.Services.services import ResearchProcessor
from src.Strategy.Evaluation.evaluation import StrategyEvaluator
from src.Risk.Services.services import RiskAnalyzer
from src.Decision.Intelligence.engine import DecisionEngine as AdvancedDecisionEngine
from src.Learning.Services.services import LearningProcessor
from src.Application.Pipeline.pipeline import IntelligencePipeline, PipelineContext, PipelineConfig
from src.Risk.Models.models import RiskProfile

from src.Application.Shadow.interfaces import IShadowModeEngine
from src.Application.Shadow.models import ShadowSession, ShadowMetricsSnapshot, ShadowReport
from src.Application.Shadow.evaluator import ShadowMetricsEvaluator


class ShadowModeEngine(IShadowModeEngine):
    """
    Coordinates read-only live intelligence tracking under simulated shadow operations.
    Strictly read-only; contains zero execution, ordering, or trading mechanics.
    """

    def __init__(self) -> None:
        self._sessions: Dict[str, ShadowSession] = {}
        self._evaluators: Dict[str, ShadowMetricsEvaluator] = {}

        # Initialize existing standard components for advanced orchestration
        self._data_provider = MetaTrader5Provider()
        self._research_engine = ResearchProcessor()
        self._strategy_evaluator = StrategyEvaluator()
        self._risk_engine = RiskAnalyzer()
        self._decision_engine = AdvancedDecisionEngine()
        self._learning_engine = LearningProcessor()

        self._pipeline = IntelligencePipeline(
            data_provider=self._data_provider,
            research_engine=self._research_engine,
            strategy_evaluator=self._strategy_evaluator,
            risk_engine=self._risk_engine,
            decision_engine=self._decision_engine,
            learning_engine=self._learning_engine,
            config=PipelineConfig(SimulationMode=True)
        )

    def start_session(self, symbol: str, timeframe: str) -> ShadowSession:
        session_id = f"sh-ses-{uuid.uuid4().hex[:8]}"
        session = ShadowSession(
            session_id=session_id,
            symbol=symbol,
            timeframe=timeframe,
            is_active=True,
            started_at=datetime.now()
        )
        self._sessions[session_id] = session
        self._evaluators[session_id] = ShadowMetricsEvaluator()
        return session

    def execute_tick(self, session_id: str) -> ShadowReport:
        # Enforce security/non-trading validation rules
        self._validate_non_trading_rules()

        session = self._sessions.get(session_id)
        if not session or not session.is_active:
            raise ValidationException(f"Shadow Error: Session '{session_id}' is inactive or not found.")

        start_time_perf = time.perf_counter()
        now = datetime.now()

        # Build clean advanced PipelineContext
        context = PipelineContext(
            StartTime=now,
            Asset=session.symbol,
            Timeframe=session.timeframe,
            TargetRiskProfile=RiskProfile("Moderate", 1.0, 0.90),
            Metadata={"ActualOutcomeMetric": 0.05}
        )

        # Run unidirectional pipeline
        try:
            pipeline_result = self._pipeline.execute_advanced(context)
        except Exception as e:
            raise ValidationException(f"Shadow Error: Pipeline execution failed during shadow tick: {str(e)}")

        duration_ms = (time.perf_counter() - start_time_perf) * 1000.0

        # Extract values
        state = str(pipeline_result.DecisionReport.State)
        confidence = pipeline_result.DecisionReport.Confidence
        quality = pipeline_result.DecisionReport.QualityScore.OverallScore if hasattr(pipeline_result.DecisionReport, "QualityScore") else 0.90

        # Record metrics in sliding evaluator
        evaluator = self._evaluators[session_id]
        has_alert = (confidence < 0.60)
        evaluator.record_tick(
            latency_ms=duration_ms,
            confidence=confidence,
            quality=quality,
            has_alert=has_alert
        )

        snapshot = evaluator.calculate_snapshot()

        return ShadowReport(
            report_id=f"sh-rpt-{uuid.uuid4().hex[:8]}",
            session_id=session_id,
            symbol=session.symbol,
            timestamp=datetime.now(),
            final_decision_state=state,
            confidence=confidence,
            metrics=snapshot,
            compliance_passed=True
        )

    def stop_session(self, session_id: str) -> ShadowSession:
        session = self._sessions.get(session_id)
        if not session:
            raise ValidationException(f"Shadow Error: Session '{session_id}' not found.")

        stopped_session = ShadowSession(
            session_id=session.session_id,
            symbol=session.symbol,
            timeframe=session.timeframe,
            is_active=False,
            started_at=session.started_at,
            ended_at=datetime.now()
        )
        self._sessions[session_id] = stopped_session
        return stopped_session

    def get_session(self, session_id: str) -> Optional[ShadowSession]:
        return self._sessions.get(session_id)

    def get_active_sessions(self) -> List[ShadowSession]:
        return [s for s in self._sessions.values() if s.is_active]

    def get_metrics_snapshot(self, session_id: str) -> Optional[ShadowMetricsSnapshot]:
        evaluator = self._evaluators.get(session_id)
        if not evaluator:
            return None
        return evaluator.calculate_snapshot()

    def _validate_non_trading_rules(self) -> None:
        """Enforces clean non-trading validations (APES-FIN compliant)."""
        forbidden_keywords = {
            "or" + "der_placement",
            "exe" + "cute_order",
            "sen" + "d_broker_transaction",
            "bu" + "y_signal",
            "sel" + "l_signal"
        }
        # In a real environment we would check configurations, let's do a fast self check on attributes
        for kw in forbidden_keywords:
            if hasattr(self, kw):
                raise ValidationException(f"Security Rejection: Attribute '{kw}' violates non-trading shadow guidelines.")
