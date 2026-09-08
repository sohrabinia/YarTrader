# YarTrader — Phase 11: Learning Architecture & Statistical Knowledge Foundation

## 1. Overview & Purpose

Phase 11 introduces a **pure, deterministic, statistical Learning Engine** that extracts explainable knowledge and signal distribution metrics from historical backtest evaluations (`BacktestResult`).

The Learning layer operates as a strict consumer of historical outcomes:
```text
Historical Market Data (Phase 6)
       ↓
Strategies (Phases 7–9)
       ↓
Backtest Simulation (Phase 10)
       ↓
Learning Observations & Dataset (Phase 11)
       ↓
Deterministic Statistical Aggregation
       ↓
Protected REST API / Read-Only UI
```

---

## 2. Core Architectural Guarantees

1. **Strict Immutability & Zero Strategy Modification:**
   - Learning NEVER modifies strategy mathematical rules, thresholds, parameters, or configurations.
   - Learning engine possesses ZERO feedback loop into `SpikeStrategyEngine`, `RangeStrategyEngine`, or `TrendStrategyEngine`.

2. **$t \le T$ Historical Causality & Zero Look-Ahead Bias:**
   - Observations are constructed strictly from backtest evaluations up to index $T$.
   - Appending future candles or future observations does NOT alter historical learning insights up to cutoff $T$.

3. **Zero AI/ML Framework Dependency:**
   - Operates strictly on deterministic mathematical and statistical frequency ratios.
   - Zero opaque neural networks, vector databases, reinforcement learning, LLM prompts, or agent brains.

4. **Zero Order Execution Leakage:**
   - Analytical layer only. Zero order submission, position tracking, live trading, wallet, or ledger mutations.

---

## 3. Data Models & API Specifications

### REST Endpoint
```http
GET /api/learning?symbol=XAUUSD&interval=M15&strategy=TREND&limit=100
```

### JSON Response Schema
```json
{
  "status": "Success",
  "data": {
    "symbol": "XAUUSD",
    "interval": "M15",
    "strategy_type": "TREND",
    "observation_count": 80,
    "signal_counts": {
      "TREND_UP": 50,
      "NO_SIGNAL": 30
    },
    "signal_frequencies": {
      "TREND_UP": 0.625,
      "NO_SIGNAL": 0.375
    },
    "sample_sufficiency": true,
    "reliability_summary": {
      "total_observations": 80,
      "active_signal_count": 50,
      "active_signal_ratio": 0.625,
      "sample_sufficiency": true,
      "min_sample_threshold": 10,
      "status": "VALID_SAMPLE"
    },
    "config": {
      "symbol": "XAUUSD",
      "interval": "M15",
      "strategy_type": "TREND",
      "min_sample_threshold": 10
    },
    "analyzed_at": "2026-09-08T07:15:00.000000+00:00"
  }
}
```

---

## 4. Verification & Testing

- **Unit/Integration Test Suite:** `tests/YarTrader.Tests/Services/test_learning_phase11.py` (25 test cases passing).
- **Regression Suite:** 98/98 canonical Phase 4–10 tests passing + 25 Phase 11 tests = **123/123 passing**.
- **Future-Data Invariance:** Verified via `test_16_mandatory_future_data_invariance`.
- **Strategy Immutability:** Verified via `test_17_mandatory_strategy_immutability`.
