# YarTrader — Phase 13: Intelligence Foundation Architecture

## 1. Overview & Purpose

Phase 13 introduces a **deterministic statistical Intelligence Foundation layer** (`IntelligenceEngine`, `IntelligenceContext`, `IntelligenceSignal`, `IntelligenceSummary`, and `IntelligenceService`).

The Intelligence Foundation aggregates historical context and signal distributions from Learning (Phase 11) and Memory (Phase 12) outputs without predictions, machine learning, or neural networks:
```text
Learning Insights (Phase 11) + Memory Records (Phase 12)
                        ↓
            Intelligence Service (Phase 13)
                        ↓
    Deterministic IntelligenceEngine Aggregation
                        ↓
    Protected REST Endpoint (GET /api/intelligence)
                        ↓
           Read-Only Dashboard UI Card
```

---

## 2. Core Architectural Guarantees & CTO Rules

1. **Zero AI, LLM, or Neural Networks:**
   - Intelligence Foundation provides pure statistical sample summaries, NOT future predictions or AI trading signals.
   - Confidence score represents historical sample size sufficiency score relative to a 30-bar baseline, NOT predictive probability.

2. **Immutable Domain Models:**
   - `IntelligenceContext`, `IntelligenceSignal`, and `IntelligenceSummary` are immutable dataclasses enforcing UTC timestamps and valid field bounds.

3. **Strict Non-Interference:**
   - Intelligence Foundation does NOT modify strategies, learning thresholds, or memory records.
   - Intelligence Foundation does NOT calculate indicators, query MT5, place orders, or mutate broker/wallet states.

---

## 3. Data Models & API Specifications

### REST Endpoint
```http
GET /api/intelligence?symbol=XAUUSD&interval=M15&strategy=TREND&limit=100
```

### JSON Response Schema
```json
{
  "status": "Success",
  "data": {
    "symbol": "XAUUSD",
    "interval": "M15",
    "strategy_type": "TREND",
    "historical_context_count": 80,
    "memory_records_count": 1,
    "context": {
      "symbol": "XAUUSD",
      "interval": "M15",
      "strategy_type": "TREND",
      "total_observations": 80,
      "active_signals_count": 50,
      "signal_distribution": {
        "TREND_UP": 50,
        "NO_SIGNAL": 30
      },
      "signal_frequencies": {
        "TREND_UP": 0.625,
        "NO_SIGNAL": 0.375
      }
    },
    "signal_summaries": [
      {
        "signal_name": "TREND_UP",
        "historical_count": 50,
        "frequency_ratio": 0.625,
        "sample_confidence_state": "HIGH_SAMPLE"
      },
      {
        "signal_name": "NO_SIGNAL",
        "historical_count": 30,
        "frequency_ratio": 0.375,
        "sample_confidence_state": "HIGH_SAMPLE"
      }
    ],
    "sample_sufficiency_status": "VALID_SAMPLE",
    "statistical_confidence_score": 1.0,
    "compiled_at": "2026-09-08T07:30:00.000000+00:00"
  }
}
```

---

## 4. Testing & Verification

- **Unit/Integration Test Suite:** `tests/YarTrader.Tests/Services/test_intelligence_phase13.py` (20 test cases passing).
- **Regression Suite:** 138 canonical Phase 4–12 tests passing + 20 Phase 13 tests = **158/158 passing**.
- **Future Data Isolation:** Verified via `test_9_no_future_data_leakage`.
- **Zero Execution Leakage:** Verified via `test_17_zero_execution_leakage`.
