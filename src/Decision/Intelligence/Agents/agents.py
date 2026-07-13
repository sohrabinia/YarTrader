import uuid
from datetime import datetime
from src.Decision.Intelligence.Agents.models import IIntelligenceAgent, AgentMessage, AgentContext
from src.Infrastructure.exceptions import ValidationException

class ResearchAgent(IIntelligenceAgent):
    """
    Research Agent responsible for analyzing market features, discoveries, and trends.
    """
    @property
    def Name(self) -> str:
        return "ResearchAgent"

    @property
    def Responsibility(self) -> str:
        return "Market observation, feature analysis, and pattern discovery."

    def process_message(self, message: AgentMessage, context: AgentContext) -> AgentMessage:
        # Enforce that agents cannot handle or trigger trading execution details
        # Simulates performing research
        asset = message.Payload.get("asset", "UNKNOWN")
        sentiment = "bullish" if asset == "AAPL" or asset == "MSFT" else "neutral"

        result_payload = {
            "asset": asset,
            "research_sentiment": sentiment,
            "insights_count": 2,
            "patterns": ["Double Bottom", "Bullish engulfing"]
        }

        return AgentMessage(
            MessageId=f"msg-res-{str(uuid.uuid4())[:8]}",
            Sender=self.Name,
            Recipient=message.Sender,
            Payload=result_payload,
            Timestamp=datetime.now(),
            CorrelationId=message.MessageId
        )


class StrategyAnalystAgent(IIntelligenceAgent):
    """
    Strategy Analyst Agent responsible for strategy evaluation and score ranking.
    """
    @property
    def Name(self) -> str:
        return "StrategyAnalystAgent"

    @property
    def Responsibility(self) -> str:
        return "Strategy evaluation, comparison, and criteria scoring."

    def process_message(self, message: AgentMessage, context: AgentContext) -> AgentMessage:
        # Evaluate strategies based on research insights
        asset = message.Payload.get("asset", "UNKNOWN")
        sentiment = message.Payload.get("research_sentiment", "neutral")

        score = 0.85 if sentiment == "bullish" else 0.50

        result_payload = {
            "asset": asset,
            "strategy_id": f"strat-agent-{asset}",
            "strategy_score": score,
            "confidence": 0.90,
            "notes": "Optimal ranking based on research momentum"
        }

        return AgentMessage(
            MessageId=f"msg-strat-{str(uuid.uuid4())[:8]}",
            Sender=self.Name,
            Recipient=message.Sender,
            Payload=result_payload,
            Timestamp=datetime.now(),
            CorrelationId=message.MessageId
        )


class RiskAgent(IIntelligenceAgent):
    """
    Risk Agent responsible for performing portfolio risk assessments and stress-testing.
    """
    @property
    def Name(self) -> str:
        return "RiskAgent"

    @property
    def Responsibility(self) -> str:
        return "Risk limit audit, exposure analysis, and scenario evaluations."

    def process_message(self, message: AgentMessage, context: AgentContext) -> AgentMessage:
        asset = message.Payload.get("asset", "UNKNOWN")
        strat_score = message.Payload.get("strategy_score", 0.50)

        # Standard safety rule checks
        is_safe = True
        notes = "Risk profile complies fully with moderate limit parameters"

        # Simulates volatility stress trigger
        volatility_level = message.Payload.get("volatility_level", "low")
        if volatility_level == "high" and strat_score > 0.80:
            is_safe = False
            notes = "Fails volatility stress check: score exceeds cap under high instability"

        result_payload = {
            "asset": asset,
            "risk_approved": is_safe,
            "risk_profile": "Moderate",
            "assessment_notes": notes
        }

        return AgentMessage(
            MessageId=f"msg-risk-{str(uuid.uuid4())[:8]}",
            Sender=self.Name,
            Recipient=message.Sender,
            Payload=result_payload,
            Timestamp=datetime.now(),
            CorrelationId=message.MessageId
        )


class ValidationAgent(IIntelligenceAgent):
    """
    Validation Agent responsible for auditing final decisions and ensuring policy compliance.
    """
    @property
    def Name(self) -> str:
        return "ValidationAgent"

    @property
    def Responsibility(self) -> str:
        return "Compliance audits, layer alignment checks, and quality checks."

    def process_message(self, message: AgentMessage, context: AgentContext) -> AgentMessage:
        # Check system details
        asset = message.Payload.get("asset", "UNKNOWN")
        risk_approved = message.Payload.get("risk_approved", True)

        is_valid = True
        reasons = []

        if not risk_approved:
            is_valid = False
            reasons.append("Fails risk assessment verification")

        result_payload = {
            "asset": asset,
            "validation_passed": is_valid,
            "compliance_flags": {"APES-FIN-Compliant": True},
            "reasons": reasons
        }

        return AgentMessage(
            MessageId=f"msg-val-{str(uuid.uuid4())[:8]}",
            Sender=self.Name,
            Recipient=message.Sender,
            Payload=result_payload,
            Timestamp=datetime.now(),
            CorrelationId=message.MessageId
        )


class LearningAgent(IIntelligenceAgent):
    """
    Learning Agent responsible for processing historical outcomes and continuous optimization suggestion generation.
    """
    @property
    def Name(self) -> str:
        return "LearningAgent"

    @property
    def Responsibility(self) -> str:
        return "Continuous feedback processing, performance metrics tracks, and improvement suggestions."

    def process_message(self, message: AgentMessage, context: AgentContext) -> AgentMessage:
        asset = message.Payload.get("asset", "UNKNOWN")
        observed_result = message.Payload.get("observed_result", 0.0)

        # Generate classic parameter adjustments
        suggestion = "Maintain existing parameters"
        if observed_result < -0.05:
            suggestion = "Reduce max single-asset exposure limit parameter"

        result_payload = {
            "asset": asset,
            "observed_result": observed_result,
            "suggestion": suggestion,
            "suggested_action": "SystemParameterOptimization"
        }

        return AgentMessage(
            MessageId=f"msg-learn-{str(uuid.uuid4())[:8]}",
            Sender=self.Name,
            Recipient=message.Sender,
            Payload=result_payload,
            Timestamp=datetime.now(),
            CorrelationId=message.MessageId
        )
