import uuid
import math
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple
from src.Application.Backtesting.models import BacktestScenario, BacktestResult
from src.Data.connector import ExternalDataPipelineConnector
from src.Data.External.models import ExternalDataRequest
from src.Application.Agents.supervisor import IntelligenceSupervisor
from src.Application.Agents.context import AgentContextBuilder
from src.Decision.Intelligence.engine import DecisionEngine
from src.Decision.Intelligence.models import DecisionIntelligenceReport
from src.Infrastructure.exceptions import ValidationException


class IntelligenceMetricsEvaluator:
    """Evaluates chronological decision consistency and research accuracy over backtesting spans."""
    def evaluate_backtest_metrics(
        self,
        reports: List[DecisionIntelligenceReport]
    ) -> Dict[str, float]:
        if not reports:
            return {
                "decision_consistency": 1.0,
                "research_accuracy_ratio": 1.0,
                "average_decision_confidence": 1.0,
                "overall_intelligence_score": 1.0
            }

        # 1. Decision Consistency: variance of confidence levels across outcomes
        confs = [r.Confidence for r in reports]
        avg_conf = sum(confs) / len(reports)
        variance = sum((c - avg_conf) ** 2 for c in confs) / len(reports)
        # Higher consistency = lower variance
        consistency = max(0.0, min(1.0, 1.0 - math.sqrt(variance)))

        # 2. Research Accuracy: ratio of high-confidence research insights
        high_conf_insights = 0
        total_insights = 0
        for r in reports:
            for insight in r.Context.ResearchInsights:
                total_insights += 1
                if hasattr(insight, "Confidence") and getattr(insight, "Confidence") >= 0.80:
                    high_conf_insights += 1

        accuracy_ratio = (high_conf_insights / total_insights) if total_insights > 0 else 1.0

        # Overall Score
        overall_score = (consistency * 0.4) + (accuracy_ratio * 0.3) + (avg_conf * 0.3)

        return {
            "decision_consistency": round(consistency, 4),
            "research_accuracy_ratio": round(accuracy_ratio, 4),
            "average_decision_confidence": round(avg_conf, 4),
            "overall_intelligence_score": round(overall_score, 4)
        }


class IntelligenceBacktestEngine:
    """
    Coordinates historical data ingestion loops, multi-agent validation runs,
    and decision quality score compilations over backtesting scenarios.
    """
    def __init__(
        self,
        supervisor: IntelligenceSupervisor,
        decision_engine: DecisionEngine,
        connector: ExternalDataPipelineConnector
    ) -> None:
        self.supervisor = supervisor
        self.decision_engine = decision_engine
        self.connector = connector
        self.evaluator = IntelligenceMetricsEvaluator()

    def run_backtest(self, scenario: BacktestScenario) -> BacktestResult:
        """Runs standard pipeline processing iteratively across the scenario date window."""
        # Enforce zero execution leakage scanning on scenario parameters
        forbidden_keywords = {"order", "position", "broker", "trade_command", "buy_signal", "sell_signal", "execute"}
        for k, v in scenario.parameters.items():
            for kw in forbidden_keywords:
                if kw in str(k).lower() or kw in str(v).lower():
                    raise ValidationException(f"Safety Violation: Backtest scenario parameters contain forbidden keyword '{kw}'.")

        reports: List[DecisionIntelligenceReport] = []
        current_time = scenario.start_time
        interval_minutes = scenario.parameters.get("interval_minutes", 60)

        # Ensure providers are registerable and resolved
        symbol = scenario.symbol

        # Loop through intervals sequentially
        total_intervals = 0
        while current_time < scenario.end_time:
            total_intervals += 1

            # 1. Fetch raw rates via Connector
            req = ExternalDataRequest(
                symbol=symbol,
                timeframe=scenario.timeframe,
                start_time=current_time - timedelta(hours=2),
                end_time=current_time,
                parameters={"scenario": "VALID"}
            )
            normalized_records, data_report = self.connector.retrieve_and_process(req)

            # 2. Ingest into Agent Ecosystem
            agent_ctx = AgentContextBuilder.create_with_market_data(symbol, scenario.timeframe)
            if normalized_records:
                # Add actual normalized records to context so agents can read and process them dynamically
                agent_ctx = agent_ctx.enrich(
                    "system",
                    "normalized_records",
                    normalized_records
                )

            # Orchestrate agents
            enriched_agent_ctx = self.supervisor.orchestrate(agent_ctx)

            # 3. Decision Synthesis
            dec_intel_ctx = self.supervisor.compile_to_decision_context(enriched_agent_ctx)

            # Evaluate Decision report
            report = self.decision_engine.evaluate_intelligence_context(dec_intel_ctx)
            reports.append(report)

            # Advance timeframe
            current_time += timedelta(minutes=interval_minutes)

        # Evaluate overall backtest scores
        metrics = self.evaluator.evaluate_backtest_metrics(reports)

        return BacktestResult(
            backtest_id=f"bt-{uuid.uuid4()}",
            scenario_id=scenario.scenario_id,
            start_time=scenario.start_time,
            end_time=scenario.end_time,
            total_intervals_processed=total_intervals,
            reports_history=reports,
            performance_metrics=metrics,
            compliance_audit_passed=True
        )
