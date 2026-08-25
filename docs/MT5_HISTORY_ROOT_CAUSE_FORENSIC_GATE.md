# YarTrader Native MT5 History Root-Cause Forensic Gate Report

## Executive Summary & Final Gate Verdict

This report documents the root-cause forensic investigation into why native MetaTrader 5 currently returns approximately **100,032 M1 bars starting on 2026-05-14T02:40:00Z** on the **Alpari-MT5-Demo** connection (`Account 52961173`, Terminal Build 6140).

```text
ROOT_CAUSE = UNDETERMINED
CLASSIFICATION = INSUFFICIENT_EVIDENCE
2021_NATIVE_XAUUSD_M1 = NOT_VERIFIED
FRACTAL_2021_2026_DATASET = NOT_AVAILABLE
FRACTAL_RESEARCH_GATE = BLOCKED
```

---

## 1. Environment Baseline & Observed Facts

```text
Terminal Executable: C:\Program Files\MetaTrader 5\terminal64.exe
Terminal Build: 6140
Trade Server: Alpari-MT5-Demo
Account Login: 52961173 (Read-Only DEMO)
MaxBars Setting: 3,000,000
Data Path: C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075
Symbol: XAUUSD
Timeframe: M1
Returned Bar Count: 100,032
First Available Bar: 2026-05-14T02:40:00Z
Last Available Bar:  2026-08-25T13:16:00Z
```

### Direct Measurements (OBSERVED_FACT)
1. `copy_rates_from_pos("XAUUSD", M1, 0, N)` for `N` = 100k, 200k, 500k, 1M, 2M, 3M all converge to exactly **100,032 bars** beginning at `2026-05-14T02:40:00Z`.
2. All tested major symbols on `Alpari-MT5-Demo` (`EURUSD`, `GBPUSD`, `USDJPY`, `XAGUSD`, `XAUUSD`) yield identical **100,032 M1 bars** starting on `2026-05-14T02:40:00Z`.
3. Higher timeframes on `XAUUSD` provide deeper historical coverage: `M5` (2025-08-10), `M15` (2023-11-04), `H1` (2010-02-18), `H4` (2001-01-03), `D1` (1999-01-04).
4. Local history directory `bases\Alpari-MT5-Demo\history\XAUUSD\` contains only `2026.hcc`. Binary cache files `2021.hcc` through `2025.hcc` do not exist.
5. Explicit `copy_rates_range()` requests for intervals prior to `2026-05-14` return 0 bars with `mt5.last_error() = (1, "Success")`.

---

## 2. Unproven Hypotheses (HYPOTHESIS)

* **HYPOTHESIS 1**: `Alpari-MT5-Demo` trade server enforces a server-side M1 history retention cap for demo accounts.
  - *Status*: **UNPROVEN**. Requires a differential test against a secondary authenticated trade server.
* **HYPOTHESIS 2**: Broker-wide or symbol-specific XAUUSD history limitation.
  - *Status*: **UNPROVEN**. Requires testing alternative trade servers or live/Pro ECN broker accounts.

---

## 3. Rejected Causal Explanations

* **LOCAL_MAXBARS_CAUSE**: **REJECTED**. The terminal setting `Max bars in chart` was raised to `3,000,000`, but the earliest available bar remained `2026-05-14T02:40:00Z`.
* **MT5_API_LIMIT_CAUSE**: **REJECTED**. `copy_rates_from_pos`, `copy_rates_range`, and `copy_rates_from` all yield identical historical boundaries.
* **XAUUSD_SYMBOL_LIMITATION**: **REJECTED**. All major symbols (`EURUSD`, `GBPUSD`, `USDJPY`, `XAGUSD`) share the exact same 100,032 M1 bar boundary.

---

## 4. Blocked Experiments (BLOCKED_EXPERIMENT)

```text
BLOCKED_EXPERIMENT = Provider Differential Test
BLOCK_REASON = No independently authenticated secondary MT5 trade-server/account (e.g. MetaQuotes-Demo or Alpari-Pro.ECN) is logged in or accessible without credentials in the current environment.
```

---

## 5. Final Classification Matrix

| Category | Status |
| :--- | :--- |
| **LOCAL_MAXBARS_CAUSE** | **REJECTED** |
| **MT5_API_LIMIT_CAUSE** | **REJECTED** |
| **XAUUSD_SYMBOL_LIMITATION** | **REJECTED** |
| **METALS_SYMBOL_LIMITATION** | **REJECTED** |
| **DEMO_ACCOUNT_LIMITATION** | **UNDETERMINED** |
| **ALPARI_SERVER_LIMITATION** | **UNDETERMINED** |
| **BROKER_GLOBAL_LIMITATION** | **UNDETERMINED** |
| **NATIVE_2021_XAUUSD_M1** | **NOT_VERIFIED** |
| **ROOT_CAUSE** | **UNDETERMINED** |
| **CLASSIFICATION** | **INSUFFICIENT_EVIDENCE** |

---

## 6. Next Required Experiment

Log into a secondary MT5 demo or live account on another trade server (e.g., `MetaQuotes-Demo`) on Windows Server `5.102.37.180` and execute:
```python
mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_M1, 0, 2000000)
```
Compare returned bar counts to complete the provider differential test.
