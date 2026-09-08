# YarTrader — Phase 15: Decision Intelligence Foundation Architecture

## 1. Overview & Purpose

Phase 15 introduces a **deterministic Decision Intelligence Foundation layer** (`DecisionIntelligenceEngine`, `DecisionIntelligenceMetric`, `DecisionIntelligenceSummary`, and `DecisionIntelligenceService`).

The Decision Intelligence Foundation layer compiles explainable intelligence metrics (sample sufficiency scores, evidence factor quality, and system context readiness state) directly from Phase 14 Decision Context Summary outputs:
```text
Decision Context Summary (Phase 14)
                 ↓
Decision Intelligence Service (Phase 15)
                 ↓
Deterministic DecisionIntelligenceEngine Aggregation
                 ↓
Protected REST Endpoint (GET /api/decision-intelligence)
                 ↓
   Read-Only Dashboard UI Card
```

---

## 2. Core Architectural Guarantees & CTO Rules

1. **System Context Readiness Indicator, NOT AI Agent / Predictor:**
   - Evaluates sample depth score and evidence factor quality.
   - Does NOT predict prices, make buy/sell recommendations, or trigger auto-trading.

2. **Zero AI / ML Model Dependency:**
   - Pure deterministic Python dataclass aggregation.
   - Zero LLM prompts, zero neural networks, zero vector databases, zero reinforcement learning.

3. **Strict Non-Interference:**
   - Does NOT modify strategy rules, learning thresholds, memory records, intelligence summaries, or context summaries.
   - Does NOT query MT5, calculate indicators, or execute broker order placement.

---

## 3. Data Models & API Specifications

### REST Endpoint
```http
GET /api/decision-intelligence?symbol=XAUUSD&interval=M15&strategy=TREND&limit=100
```

### JSON Response Schema
```json
{
  "status": "Success",
  "data": {
    "intelligence_id": "intel-XAUUSD-TREND-20260908093000",
    "symbol": "XAUUSD",
    "interval": "M15",
    "strategy_type": "TREND",
    "decision_readiness_state": "INTELLIGENCE_READY",
    "context_sufficiency_score": 1.0,
    "evidence_factor_quality": "HIGH_QUALITY",
    "metrics": [
      {
        "metric_name": "ContextSufficiencyScore",
        "metric_value": 1.0,
        "category": "SAMPLE_DEPTH",
        "explanation": "Sample depth score of 1.0 relative to 30-bar baseline for XAUUSD (M15)."
      },
      {
        "metric_name": "EvidenceFactorQuality",
        "metric_value": "HIGH_QUALITY",
        "category": "DATA_QUALITY",
        "explanation": "Evidence factor quality classified as HIGH_QUALITY."
      },
      {
        "metric_name": "DecisionReadinessState",
        "metric_value": "INTELLIGENCE_READY",
        "category": "SYSTEM_READINESS",
        "explanation": "System decision context readiness state is INTELLIGENCE_READY."
      }
    ],
    "compiled_at": "2026-09-08T09:30:00.000000+00:00"
  }
}
```

---

## 4. Testing & Verification

- **Unit/Integration Test Suite:** `tests/YarTrader.Tests/Services/test_decision_intelligence_phase15.py` (20 test cases passing).
- **Regression Suite:** 178 canonical Phase 4–14 tests passing + 20 Phase 15 tests = **198/198 passing**.
- **Future Data Safety:** Verified via `test_11_no_future_data_leakage`.
- **Zero Execution Leakage:** Verified via `test_16_zero_execution_leakage`.
