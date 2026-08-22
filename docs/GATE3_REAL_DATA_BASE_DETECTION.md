# YarTrader Forensic Fractal Research — Gate 3 Multi-Scale Base Detection Engine

## Overview & Mission Statement

The **Gate 3 Multi-Scale Base Detection Engine** (`Gate3BaseDetectorEngine` v1.2.0) performs ratio-agnostic candidate Base discovery independently at every constructed scale level.

Rather than assuming that timeframe ratios are inherently fixed at $\times3$ or $\times4$, the engine analyzes constructed scale families ($\times3$: $1, 3, 9, 27, 81, 243, 729, 2187, 6561, 19683$ and $\times4$: $1, 4, 16, 64, 256, 1024, 4096, 16384$) independently, allowing empirical scale structures and parent/child Base relationships to emerge directly from market evidence.

---

## Key Technical Requirements & Safeguards

1. **Ratio-Agnostic Detection Layer:** Candidates are detected per scale based on price range compression, local ATR, duration, and internal swing volatility.
2. **100% Intra-Base Backward-Looking Metrics:** No look-ahead bias or future-data leakage in Base candidate scoring.
3. **Exclusion of Partial Trailing Groups:** Aggregated chunks marked with `is_partial_trailing_group: True` (Gate 2 output) are strictly filtered out to prevent incomplete trailing scale periods from forming structural Bases.
4. **Memory-Optimized Architecture:** Handles large historical market datasets (100,000+ M1 records) without OOM or performance degradation.
5. **Truthfulness Gate Enforcement:** Fallback to synthetic market data is strictly forbidden. If authentic market data is absent, execution halts with `REAL_DATA_UNAVAILABLE`.
6. **Execution Isolation:** Research code operates strictly read-only. Zero trade execution calls (`mt5.order_send`), order checks, position modifications, or risk updates exist. DEMO BTC position `#368555219` and live MT5 execution paths are 100% protected.

---

## Artifact Inventory

- **Core Module:** `src/Research/Brain/fractal_base_detection_engine.py` (`Gate3BaseDetectorEngine` v1.2.0)
- **Pipeline Runner:** `scripts/run_gate3_base_detection_pipeline.py`
- **Unit Test Suite:** `tests/YarTrader.Tests/Research/test_fractal_base_detection_engine.py`
- **Output Artifacts:** `runtime_logs/research_center/BaseDetectionReport_REAL.json` & `runtime_logs/research_center/Gate3_PersianForensicReport_REAL.json`

---

## Test Verification

```bash
PYTHONPATH=. pytest tests/YarTrader.Tests/Research/test_fractal_base_detection_engine.py
PYTHONPATH=. pytest tests/YarTrader.Tests/Research/test_mt_data_acquisition.py tests/YarTrader.Tests/Research/test_fractal_data_scale_engine.py tests/YarTrader.Tests/Research/test_fractal_base_detection_engine.py tests/test_historical_data_adapter.py
```

Result: **28/28 passed (100% pass rate)**.
