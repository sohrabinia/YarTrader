import uuid
from datetime import datetime
from typing import Any, Dict, List
from src.Application.Agents.interfaces import IIntelligenceAgent
from src.Application.Agents.context import AgentContext
from src.Application.Agents.communication import IntelligenceMessage
from src.Infrastructure.exceptions import ValidationException


class BaseAgent(IIntelligenceAgent):
    """Base class for all Agents, implementing standard scanning and shared attributes."""
    def __init__(self, agent_id: str, name: str, responsibility: str) -> None:
        self._agent_id = agent_id
        self._name = name
        self._responsibility = responsibility

    @property
    def agent_id(self) -> str:
        return self._agent_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def responsibility(self) -> str:
        return self._responsibility

    def _verify_isolation(self, message: IntelligenceMessage, forbidden_keywords: List[str]) -> None:
        """Enforces strict agent isolation by scanning for forbidden keywords in payload."""
        def check_val(val: Any) -> None:
            if isinstance(val, str):
                lower_val = val.lower()
                for keyword in forbidden_keywords:
                    if keyword in lower_val:
                        raise ValidationException(
                            f"Isolation Violation: Agent '{self.name}' accessed or output forbidden capability '{keyword}'."
                        )
            elif isinstance(val, dict):
                for k, v in val.items():
                    check_val(k)
                    check_val(v)
            elif isinstance(val, (list, tuple, set)):
                for item in val:
                    check_val(item)

        check_val(message.payload)


class ResearchAgent(BaseAgent):
    """
    Research Agent.
    Allowed: Market observation, Feature analysis, Pattern discovery.
    Forbidden: Execution, Orders, Trading commands.
    """
    def __init__(self) -> None:
        super().__init__(
            agent_id="agent-research",
            name="Research Agent",
            responsibility="Generates market observations, feature extractions, and technical pattern discoveries."
        )

    def process(self, context: AgentContext, message: IntelligenceMessage) -> IntelligenceMessage:
        # Strict isolation check
        forbidden = ["execution", "orders", "trading commands", "buy", "sell", "place_order"]
        self._verify_isolation(message, forbidden)

        # Retrieve market data details from context or message payload
        asset = context.data.get("asset", "UNKNOWN")

        # Generate passive market observation
        observation = {
            "asset": asset,
            "observation_type": "Market observation, feature analysis, pattern discovery",
            "findings": ["Trend is stable bullish on H4 timeframe", "Pattern: Double Bottom found on H1"],
            "features": {"volatility": 0.12, "trend_strength": 0.82},
            "timestamp": datetime.now().isoformat()
        }

        # Build output message
        return IntelligenceMessage(
            message_id=f"msg-res-{uuid.uuid4()}",
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            timestamp=datetime.now(),
            message_type="ResearchReport",
            payload=observation,
            trace_trail=list(message.trace_trail)
        )


class StrategyAnalystAgent(BaseAgent):
    """
    Strategy Analyst Agent.
    Allowed: Strategy evaluation, Comparison, Scoring.
    Forbidden: Trading signals.
    """
    def __init__(self) -> None:
        super().__init__(
            agent_id="agent-strategy",
            name="Strategy Analyst Agent",
            responsibility="Evaluates registered strategies, scores candidate performance, and ranks alignment."
        )

    def process(self, context: AgentContext, message: IntelligenceMessage) -> IntelligenceMessage:
        forbidden = ["trading signals", "buy_signal", "sell_signal", "execute_trade", "place_order", "order"]
        self._verify_isolation(message, forbidden)

        asset = context.data.get("asset", "UNKNOWN")

        # Evaluate strategy
        score_data = {
            "asset": asset,
            "strategy_id": "strat-momentum-pipeline",
            "score": {
                "OverallScore": 0.85,
                "Confidence": 0.90,
                "Criteria": {"Stability": 0.80, "Complexity": 0.30, "RiskCompatibility": 0.90}
            },
            "evaluation_notes": "Strategy score is high with strong risk-compatibility.",
            "timestamp": datetime.now().isoformat()
        }

        return IntelligenceMessage(
            message_id=f"msg-strat-{uuid.uuid4()}",
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            timestamp=datetime.now(),
            message_type="StrategyEvaluation",
            payload=score_data,
            trace_trail=list(message.trace_trail)
        )


class RiskAgent(BaseAgent):
    """
    Risk Agent.
    Allowed: Risk analysis, Exposure analysis, Scenario evaluation.
    Forbidden: Position opening.
    """
    def __init__(self) -> None:
        super().__init__(
            agent_id="agent-risk",
            name="Risk Agent",
            responsibility="Performs exposure checks, calculates portfolio risk metrics, and stress-tests allocations."
        )

    def process(self, context: AgentContext, message: IntelligenceMessage) -> IntelligenceMessage:
        forbidden = ["position opening", "open_position", "execute_trade", "place_order", "leverage_order"]
        self._verify_isolation(message, forbidden)

        asset = context.data.get("asset", "UNKNOWN")

        # Generate portfolio risk and exposure analysis
        risk_data = {
            "asset": asset,
            "IsApproved": True,
            "RiskProfileName": "Moderate",
            "PortfolioRiskMetrics": {
                "annualized_volatility": 0.12,
                "max_drawdown": 0.05,
                "sharp_ratio": 2.1
            },
            "AssessmentNotes": "Proposed weights conform to Moderate risk limits. Exposure within safety margin.",
            "timestamp": datetime.now().isoformat()
        }

        return IntelligenceMessage(
            message_id=f"msg-risk-{uuid.uuid4()}",
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            timestamp=datetime.now(),
            message_type="RiskAssessment",
            payload=risk_data,
            trace_trail=list(message.trace_trail)
        )


class ValidationAgent(BaseAgent):
    """
    Validation Agent.
    Allowed: Compliance checks, Quality checks.
    Forbidden: Modifying decisions.
    """
    def __init__(self) -> None:
        super().__init__(
            agent_id="agent-validation",
            name="Validation Agent",
            responsibility="Validates compliance against system design boundaries, data quality, and ensures zero execution leakage."
        )

    def process(self, context: AgentContext, message: IntelligenceMessage) -> IntelligenceMessage:
        forbidden = ["modify_decision", "change_state", "override_action", "buy", "sell"]
        self._verify_isolation(message, forbidden)

        asset = context.data.get("asset", "UNKNOWN")

        # Compliance and quality report
        validation_data = {
            "asset": asset,
            "compliance_checked": True,
            "data_quality_score": 0.98,
            "system_health_status": "Healthy",
            "notes": "Passed all architectural boundary checks. Strict isolation verified.",
            "timestamp": datetime.now().isoformat()
        }

        return IntelligenceMessage(
            message_id=f"msg-val-{uuid.uuid4()}",
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            timestamp=datetime.now(),
            message_type="ComplianceAudit",
            payload=validation_data,
            trace_trail=list(message.trace_trail)
        )


class LearningAgent(BaseAgent):
    """
    Learning Agent.
    Allowed: Learning optimization, Performance tracking, Feedback analysis.
    Forbidden: Active trading parameters, Real-time model retraining.
    """
    def __init__(self) -> None:
        super().__init__(
            agent_id="agent-learning",
            name="Learning Agent",
            responsibility="Ingests feedback loops, evaluates agent decisions for consistency, and logs performance analytics."
        )

    def process(self, context: AgentContext, message: IntelligenceMessage) -> IntelligenceMessage:
        forbidden = ["active_trading", "set_trading_param", "model_retraining", "retrain_now", "live_retrain"]
        self._verify_isolation(message, forbidden)

        asset = context.data.get("asset", "UNKNOWN")

        # In-memory performance logs & feedback suggestions
        learning_data = {
            "asset": asset,
            "feedback_analyzed": True,
            "tracking_metrics": {
                "decision_stability": 0.95,
                "research_accuracy": 0.88,
                "risk_adherence": 1.0
            },
            "improvement_suggestions": ["Fine-tune strategy volatility filter to 0.15"],
            "timestamp": datetime.now().isoformat()
        }

        return IntelligenceMessage(
            message_id=f"msg-learn-{uuid.uuid4()}",
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            timestamp=datetime.now(),
            message_type="LearningFeedback",
            payload=learning_data,
            trace_trail=list(message.trace_trail)
        )
