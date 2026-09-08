# YarTrader — Phase 14: Decision Context Foundation Architecture

## 1. Overview & Purpose

Phase 14 introduces a **deterministic Decision Context Foundation layer** (`DecisionContextEngine`, `DecisionContext`, `DecisionFactor`, `DecisionContextSummary`, and `DecisionContextService`).

The Decision Context Foundation layer compiles explainable context from Phase 11 Learning, Phase 12 Memory, and Phase 13 Intelligence outputs to prepare historical evidence for future human or AI decision consumers:
```text
Intelligence Summary (Phase 13) + Learning (Phase 11) + Memory (Phase 12)
                                ↓
                 Decision Context Service (Phase 14)
                                ↓
        Deterministic DecisionContextEngine Aggregation
                                ↓
         Protected REST Endpoint (GET /api/decision-context)
                                ↓
                   Read-Only Dashboard UI Card
```

---

## 2. Core Architectural Guarantees & CTO Rules

1. **Context Preparation, NOT Decision Making:**
   - This layer prepares explainable evidence context.
   - It does NOT make buy/sell decisions, generate predictions, forecast prices, or suggest trades.

2. **Zero AI / ML Model Dependency:**
   - Pure deterministic Python dataclass aggregation.
   - Zero LLM prompts, zero neural networks, zero vector databases, zero reinforcement learning.

3. **Strict Non-Interference:**
   - Does NOT modify strategy rules, learning thresholds, memory records, or intelligence context.
   - Does NOT query MT5, calculate indicators, or execute broker order placement.

---

## 3. Data Models & API Specifications

### REST Endpoint
```http
GET /api/decision-context?symbol=XAUUSD&interval=M15&strategy=TREND&limit=100
```

### JSON Response Schema
```json
{
  "status": "Success",
  "data": {
    "context_id": "ctx-XAUUSD-TREND-20260908091500",
    "symbol": "XAUUSD",
    "interval": "M15",
    "strategy_type": "TREND",
    "decision_context": {
      "timestamp": "2026-09-08T09:15:00.000000+00:00",
      "symbol": "XAUUSD",
      "interval": "M15",
      "historical_context_count": 80,
      "learning_summary": {
        "observation_count": 80,
        "signal_counts": {
          "TREND_UP": 50,
          "NO_SIGNAL": 30
        },
        "sample_sufficiency": true
      },
      "memory_summary": {
        "records_count": 1
      },
      "intelligence_summary": {
        "active_signals_count": 50,
        "sample_sufficiency_status": "VALID_SAMPLE",
        "statistical_confidence_score": 1.0
      }
    },
    "factors": [
      {
        "factor_name": "HistoricalObservationCount",
        "factor_value": 80,
        "source": "Phase 11 Learning",
        "explanation": "Evaluated 80 historical market bars for XAUUSD (M15)."
      },
      {
        "factor_name": "MemoryRecordsCount",
        "factor_value": 1,
        "source": "Phase 12 Memory Foundation",
        "explanation": "Retrieved 1 structured historical knowledge records."
      },
      {
        "factor_name": "StatisticalSampleSufficiency",
        "factor_value": "VALID_SAMPLE",
        "source": "Phase 13 Intelligence Foundation",
        "explanation": "Sample size classification is VALID_SAMPLE."
      },
      {
        "factor_name": "StatisticalConfidenceScore",
        "factor_value": 1.0,
        "source": "Phase 13 Intelligence Foundation",
        "explanation": "Sample size score relative to 30-bar baseline is 1.0."
      }
    ],
    "reliability_state": "STABLE_CONTEXT",
    "data_quality_state": "HIGH_QUALITY",
    "compiled_at": "2026-09-08T09:15:00.000000+00:00"
  }
}
```

---

## 4. Testing & Verification

- **Unit/Integration Test Suite:** `tests/YarTrader.Tests/Services/test_decision_context_phase14.py` (20 test cases passing).
- **Regression Suite:** 158 canonical Phase 4–13 tests passing + 20 Phase 14 tests = **178/178 passing**.
- **Future Data Safety:** Verified via `test_10_no_future_data_leakage`.
- **Zero Execution Leakage:** Verified via `test_16_zero_execution_leakage`.
