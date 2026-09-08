from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from src.Application.Decision.decision_intelligence_engine import DecisionIntelligenceSummary
from src.Infrastructure.exceptions import ValidationException


@dataclass(frozen=True)
class GovernanceRule:
    """
    Immutable domain representation of a decision governance validation rule.
    Pure historical evidence check.
    Zero AI, zero LLM, zero predictions, zero buy/sell signals.
    """
    rule_id: str
    rule_name: str
    min_required_value: Any
    category: str
    explanation: str

    def validate(self) -> None:
        if not self.rule_id or not isinstance(self.rule_id, str):
            raise ValidationException("GovernanceRule rule_id must be a non-empty string.")
        if not self.rule_name or not isinstance(self.rule_name, str):
            raise ValidationException("GovernanceRule rule_name must be a non-empty string.")
        if not self.category or not isinstance(self.category, str):
            raise ValidationException("GovernanceRule category must be a non-empty string.")
        if not self.explanation or not isinstance(self.explanation, str):
            raise ValidationException("GovernanceRule explanation must be a non-empty string.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "min_required_value": self.min_required_value,
            "category": self.category,
            "explanation": self.explanation
        }


@dataclass(frozen=True)
class GovernanceCheck:
    """
    Immutable domain representation of an individual governance rule check outcome.
    """
    rule_id: str
    rule_name: str
    passed: bool
    observed_value: Any
    required_value: Any
    message: str

    def validate(self) -> None:
        if not self.rule_id or not isinstance(self.rule_id, str):
            raise ValidationException("GovernanceCheck rule_id must be a non-empty string.")
        if not self.rule_name or not isinstance(self.rule_name, str):
            raise ValidationException("GovernanceCheck rule_name must be a non-empty string.")
        if not isinstance(self.passed, bool):
            raise ValidationException("GovernanceCheck passed must be a boolean.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "passed": self.passed,
            "observed_value": self.observed_value,
            "required_value": self.required_value,
            "message": self.message
        }


@dataclass(frozen=True)
class GovernanceResult:
    """
    Immutable root summary produced deterministically by DecisionGovernanceEngine.
    Exposes governance_id, governance_state, checks, rejection_reasons, and compiled_at.
    """
    governance_id: str
    symbol: str
    interval: str
    strategy_type: str
    governance_state: str
    evidence_quality: str
    checks: List[GovernanceCheck]
    rejection_reasons: List[str]
    decision_intelligence_summary: DecisionIntelligenceSummary
    compiled_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "governance_id": self.governance_id,
            "symbol": self.symbol,
            "interval": self.interval,
            "strategy_type": self.strategy_type,
            "governance_state": self.governance_state,
            "evidence_quality": self.evidence_quality,
            "checks": [c.to_dict() for c in self.checks],
            "rejection_reasons": self.rejection_reasons,
            "decision_intelligence_summary": self.decision_intelligence_summary.to_dict(),
            "compiled_at": self.compiled_at.isoformat()
        }


class DecisionGovernanceEngine:
    """
    Pure, deterministic Decision Governance Engine.
    Validates Phase 15 DecisionIntelligenceSummary outputs against deterministic governance rules:
    - Minimum sample depth check (min 10 bars)
    - Data quality check (forbids LOW_QUALITY)
    - Context stability check (requires INTELLIGENCE_READY)
    - Conflicting signal threshold check (active signal ratio >= 0.1)

    Does NOT make buy/sell decisions, generate signals, calculate indicators, query MT5,
    train ML models, or execute orders.
    """

    def evaluate_governance(
        self,
        intelligence_summary: DecisionIntelligenceSummary
    ) -> GovernanceResult:
        if not intelligence_summary:
            raise ValidationException("intelligence_summary cannot be None.")

        sym = intelligence_summary.symbol
        tf = intelligence_summary.interval
        strat = intelligence_summary.strategy_type

        d_ctx_summary = intelligence_summary.decision_context_summary
        d_ctx = d_ctx_summary.decision_context
        tot_obs = d_ctx.historical_context_count
        now_utc = datetime.now(timezone.utc)

        checks: List[GovernanceCheck] = []
        rejections: List[str] = []

        # Check 1: Sample Depth Rule (Min 10 bars)
        chk_depth = GovernanceCheck(
            rule_id="GOV-001",
            rule_name="MinimumSampleDepth",
            passed=(tot_obs >= 10),
            observed_value=tot_obs,
            required_value=10,
            message=f"Sample size {tot_obs} satisfies min threshold of 10 bars." if tot_obs >= 10 else f"Insufficient sample size ({tot_obs} < 10 bars)."
        )
        chk_depth.validate()
        checks.append(chk_depth)
        if not chk_depth.passed:
            rejections.append(chk_depth.message)

        # Check 2: Data Quality Rule
        quality_val = intelligence_summary.evidence_factor_quality
        chk_quality = GovernanceCheck(
            rule_id="GOV-002",
            rule_name="DataQualityThreshold",
            passed=(quality_val != "LOW_QUALITY"),
            observed_value=quality_val,
            required_value="MODERATE_QUALITY or HIGH_QUALITY",
            message=f"Data quality '{quality_val}' passed validation." if quality_val != "LOW_QUALITY" else "Data quality is LOW_QUALITY."
        )
        chk_quality.validate()
        checks.append(chk_quality)
        if not chk_quality.passed:
            rejections.append(chk_quality.message)

        # Check 3: Readiness / Context Stability Rule
        readiness_val = intelligence_summary.decision_readiness_state
        chk_readiness = GovernanceCheck(
            rule_id="GOV-003",
            rule_name="ContextStabilityReadiness",
            passed=(readiness_val == "INTELLIGENCE_READY"),
            observed_value=readiness_val,
            required_value="INTELLIGENCE_READY",
            message=f"Readiness state '{readiness_val}' is stable." if readiness_val == "INTELLIGENCE_READY" else f"Context readiness state '{readiness_val}' is unstable."
        )
        chk_readiness.validate()
        checks.append(chk_readiness)
        if not chk_readiness.passed:
            rejections.append(chk_readiness.message)

        # Check 4: Active Signal Evidence Ratio Rule (Min 10%)
        act_cnt = d_ctx.intelligence_summary.get("active_signals_count", 0)
        act_ratio = (act_cnt / float(tot_obs)) if tot_obs > 0 else 0.0
        chk_ratio = GovernanceCheck(
            rule_id="GOV-004",
            rule_name="ActiveEvidenceRatio",
            passed=(act_ratio >= 0.10 or tot_obs == 0),
            observed_value=round(act_ratio, 4),
            required_value=0.10,
            message=f"Active signal ratio {round(act_ratio, 4)} satisfies min 0.10 evidence threshold." if (act_ratio >= 0.10 or tot_obs == 0) else f"Active signal evidence ratio {round(act_ratio, 4)} below 0.10."
        )
        chk_ratio.validate()
        checks.append(chk_ratio)
        if not chk_ratio.passed:
            rejections.append(chk_ratio.message)

        gov_state = "GOVERNANCE_APPROVED" if len(rejections) == 0 else "GOVERNANCE_REJECTED"
        gov_id = f"gov-{sym.upper()}-{strat.upper()}-{now_utc.strftime('%Y%m%d%H%M%S')}"

        return GovernanceResult(
            governance_id=gov_id,
            symbol=sym,
            interval=tf,
            strategy_type=strat,
            governance_state=gov_state,
            evidence_quality=quality_val,
            checks=checks,
            rejection_reasons=rejections,
            decision_intelligence_summary=intelligence_summary,
            compiled_at=now_utc
        )
