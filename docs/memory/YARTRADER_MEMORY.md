# YarTrader — Phase 12: Memory Foundation Architecture

## 1. Overview & Purpose

Phase 12 introduces a **minimal, deterministic Memory Foundation layer** (`MemoryStore`, `MemoryRecord`, and `MemoryService`).

The Memory Foundation stores structured historical knowledge and insights derived from Phase 11 Learning (`LearningInsight`):
```text
Historical Learning Insights (Phase 11)
            ↓
Memory Service (Phase 12)
            ↓
Immutable MemoryRecord & Deterministic MemoryStore
            ↓
Protected REST Endpoint (GET /api/memory)
            ↓
Read-Only Dashboard UI Card
```

---

## 2. Core Architectural Guarantees & CTO Rules

1. **Zero AI, LLM, or Vector Database:**
   - Memory Foundation stores facts, not intelligence.
   - Zero chat memory, zero vector embeddings, zero LLM prompts, zero neural networks, zero agent brains.

2. **Immutable Structured Knowledge:**
   - `MemoryRecord` is an immutable dataclass requiring UTC timestamps, symbol, interval, strategy_type, observation_type, metrics, and confidence.
   - Records are stored deterministically in `MemoryStore`.

3. **Strict Separation of Concerns:**
   - Memory does NOT modify strategy rules or thresholds.
   - Memory does NOT calculate indicators or fetch market candles.
   - Memory does NOT call MT5, brokers, or execution paths.
   - Memory does NOT trigger trades, orders, or wallet/ledger mutations.

---

## 3. Data Models & API Specifications

### REST Endpoint
```http
GET /api/memory?symbol=XAUUSD&strategy=TREND
```

### JSON Response Schema
```json
{
  "status": "Success",
  "data": {
    "total_records": 1,
    "filters": {
      "symbol": "XAUUSD",
      "strategy_type": "TREND",
      "start_time": null,
      "end_time": null
    },
    "summary": {
      "latest_timestamp": "2026-09-08T07:15:00.000000+00:00",
      "strategy_distribution": {
        "TREND": 1
      },
      "symbol_distribution": {
        "XAUUSD": 1
      }
    },
    "records": [
      {
        "id": "mem-XAUUSD-TREND-20260908071500",
        "timestamp": "2026-09-08T07:15:00.000000+00:00",
        "symbol": "XAUUSD",
        "interval": "M15",
        "strategy_type": "TREND",
        "observation_type": "LEARNING_STATISTICAL_INSIGHT",
        "metrics": {
          "observation_count": 80,
          "signal_counts": {
            "TREND_UP": 50,
            "NO_SIGNAL": 30
          },
          "signal_frequencies": {
            "TREND_UP": 0.625,
            "NO_SIGNAL": 0.375
          },
          "sample_sufficiency": true
        },
        "confidence": 0.625,
        "source_phase": "PHASE_11_LEARNING"
      }
    ]
  }
}
```

---

## 4. Testing & Verification

- **Unit/Integration Test Suite:** `tests/YarTrader.Tests/Services/test_memory_phase12.py` (15 test cases passing).
- **Regression Suite:** 123 canonical Phase 4–11 tests passing + 15 Phase 12 tests = **138/138 passing**.
- **Future Data Isolation:** Verified via `test_13_future_data_isolation`.
- **Zero Execution Leakage:** Verified via `test_15_no_execution_leakage`.
