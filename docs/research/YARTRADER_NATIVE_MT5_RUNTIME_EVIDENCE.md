# YarTrader Native MT5 Runtime Evidence

```text
YarTrader Native MT5 Runtime Evidence

Environment OS: Linux 6.8.0-1021-aws (x86_64)
Python Version: 3.12.13
MetaTrader5 Python Module: NOT INSTALLED / NOT SUPPORTED ON LINUX
MT5 Terminal Path: UNAVAILABLE (Non-Windows Linux Container Environment)
MT5 Data Path: UNAVAILABLE

MT5 Connected: NO
XAUUSD Available: NO (Requires Active Native MT5 Terminal Connection)
M1 Available: NO (Requires Active Native MT5 Terminal Connection)

Requested Start:
2021-01-01 00:00:00

Requested End:
2026-08-25 23:59:59

Actual First M1:
N/A (REAL_DATA_UNAVAILABLE)

Actual Last M1:
N/A (REAL_DATA_UNAVAILABLE)

Actual Bar Count:
0

Actual Duration:
0.0 Years

Dataset:
data/research/xauusd_m1_real.json

Dataset Exists:
NO

Dataset Classification:
BLOCKED (REAL_DATA_UNAVAILABLE)

Dataset SHA256:
N/A

Manifest:
data/research/xauusd_m1_manifest.json

Manifest Status:
INCOMPLETE (BLOCKED_NO_MT5_IPC)

Research Executed:
NO (Fail-Closed Stop Condition Triggered)

Research Consumed Dataset:
NONE

Research Dataset SHA256:
N/A

Research Result:
BLOCKED — REAL HISTORICAL MT5 DATA ACQUISITION REQUIRES NATIVE WINDOWS MT5 TERMINAL IPC

LIVE_TRADING_ENABLED:
False (Hard-locked SRE isolation)

YarTrader Brand Compliance:
PASS (0 new non-compliant brand references)

Read-Only Safety:
PASS (LIVE_TRADING_ENABLED=False enforced, 0 order executions)

Indicator-Free Integrity:
PASS (0 active technical indicators, 0% Fibonacci dependencies)

Final Gate:
BLOCKED — NATIVE WINDOWS MT5 EXECUTION REQUIRED
```

---

## Forensic Audit Summary

1. **Environment Probing:**
   - Host Architecture: `Linux 6.8.0-1021-aws x86_64`
   - `MetaTrader5` C-extension DLL Python package cannot be loaded on Linux operating systems.
   - Native MetaTrader 5 terminal process (`C:\Program Files\MetaTrader 5\terminal64.exe`) is physically absent from this Linux container execution sandbox.

2. **Truthfulness Policy Compliance:**
   - Per Section 2 ("Truthfulness Principle") and Section 25 ("BLOCK Conditions"), synthetic candle generation, interpolation, mock historical injection, or test fixture promotion is **STRICTLY FORBIDDEN**.
   - No synthetic dataset was created or promoted to `REAL_HISTORICAL`.
   - The acquisition engine cleanly halted execution with `REAL_DATA_UNAVAILABLE`.

3. **Required Next Step for Final PASS:**
   - To achieve `FINAL GATE = PASS`, `scripts/run_gold_fractal_intelligence_pipeline.py` and `src/Research/Brain/mt_data_acquisition.py` must be executed directly inside a native Windows Server environment running MetaTrader 5 terminal connected to an authorized broker feed.
