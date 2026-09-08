# YarTrader — Phase 16: Decision Governance Foundation Architecture

## 1. Overview & Purpose

Phase 16 introduces a **deterministic Decision Governance Foundation layer** (`DecisionGovernanceEngine`, `GovernanceRule`, `GovernanceCheck`, `GovernanceResult`, and `DecisionGovernanceService`).

The Decision Governance layer validates Phase 15 Decision Intelligence outputs against strict deterministic governance rules (sample depth, data quality, context stability, active evidence ratios) prior to any operational evaluation:
```text
Decision Intelligence Summary (Phase 15)
                 ↓
Decision Governance Service (Phase 16)
                 ↓
Deterministic DecisionGovernanceEngine Validation
                 ↓
Protected REST Endpoint (GET /api/decision-governance)
                 ↓
   Read-Only Dashboard UI Card
```

---

## 2. Core Architectural Guarantees & CTO Rules

1. **Governance Validation, NOT Trade Execution:**
   - Evaluates evidence quality and rule compliance.
   - Does NOT generate buy/sell signals, execute orders, or interact with MT5 brokers.

2. **Zero AI / ML Model Dependency:**
   - Pure deterministic Python dataclass aggregation and validation.
   - Zero LLM prompts, zero neural networks, zero vector databases, zero reinforcement learning.

3. **Strict Non-Interference:**
   - Does NOT modify strategy rules, learning thresholds, memory records, intelligence summaries, or context summaries.
   - Does NOT query MT5, calculate indicators, or execute order placement.

---

## 3. Data Models & API Specifications

### REST Endpoint
```http
GET /api/decision-governance?symbol=XAUUSD&interval=M15&strategy=TREND&limit=100
```

### JSON Response Schema
```json
{
  "status": "Success",
  "data": {
    "governance_id": "gov-XAUUSD-TREND-20260908100000",
    "symbol": "XAUUSD",
    "interval": "M15",
    "strategy_type": "TREND",
    "governance_state": "GOVERNANCE_APPROVED",
    "evidence_quality": "HIGH_QUALITY",
    "checks": [
      {
        "rule_id": "GOV-001",
        "rule_name": "MinimumSampleDepth",
        "passed": true,
        "observed_value": 80,
        "required_value": 10,
        "message": "Sample size 80 satisfies min threshold of 10 bars."
      },
      {
        "rule_id": "GOV-002",
        "rule_name": "DataQualityThreshold",
        "passed": true,
        "observed_value": "HIGH_QUALITY",
        "required_value": "MODERATE_QUALITY or HIGH_QUALITY",
        "message": "Data quality 'HIGH_QUALITY' passed validation."
      },
      {
        "rule_id": "GOV-003",
        "rule_name": "ContextStabilityReadiness",
        "passed": true,
        "observed_value": "INTELLIGENCE_READY",
        "required_value": "INTELLIGENCE_READY",
        "message": "Readiness state 'INTELLIGENCE_READY' is stable."
      },
      {
        "rule_id": "GOV-004",
        "rule_name": "ActiveEvidenceRatio",
        "passed": true,
        "observed_value": 0.625,
        "required_value": 0.1,
        "message": "Active signal ratio 0.625 satisfies min 0.10 evidence threshold."
      }
    ],
    "rejection_reasons": [],
    "compiled_at": "2026-09-08T10:00:00.000000+00:00"
  }
}
```

---

## 4. Testing & Verification

- **Unit/Integration Test Suite:** `tests/YarTrader.Tests/Services/test_decision_governance_phase16.py` (21 test cases passing).
- **Regression Suite:** 198 canonical Phase 4–15 tests passing + 21 Phase 16 tests = **219/219 passing**.
- **Future Data Safety:** Verified via `test_12_no_future_data_leakage`.
- **Zero Execution Leakage:** Verified via `test_18_zero_execution_leakage`.
