# YarTrader Native MT5 Historical Provider Forensic Audit Report

## Executive Summary & Final Causal Verdict

This report documents the forensic investigation into why native MetaTrader 5 currently returns approximately **100,032 M1 bars starting on 2026-05-14T02:40:00Z** on the **Alpari-MT5-Demo** connection (`Account 52961173`, Terminal Build 6140).

```text
ROOT_CAUSE = UNDETERMINED
NATIVE_2021_XAUUSD_M1 = NOT_VERIFIED
FRACTAL_2021_2026_DATASET = NOT_AVAILABLE
FRACTAL_RESEARCH_GATE = BLOCKED
```

---

## 1. Environment Baseline & Verified Facts

```text
Terminal Executable: C:\Program Files\MetaTrader 5\terminal64.exe
Terminal Build: 6140
Trade Server: Alpari-MT5-Demo
Account Login: 52961173 (Read-Only DEMO)
MaxBars Setting: 3,000,000
Data Path: C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075
Symbol: XAUUSD
Timeframe: M1
Returned Count: 100,032 bars
Earliest Bar Timestamp: 2026-05-14T02:40:00Z
Latest Bar Timestamp:   2026-08-25T13:16:00Z
```

---

## 2. Forensic Test Results

### TEST 1 — Position Probes (`copy_rates_from_pos`)
* Requesting `100,000` bars -> Returned `100,000` bars (First: `2026-05-14T03:12:00Z`)
* Requesting `200,000` bars -> Returned `100,032` bars (First: `2026-05-14T02:40:00Z`)
* Requesting `500,000` to `3,000,000` bars -> Converges to exactly `100,032` bars.

### TEST 2 — Direct Date-Range Probes (`copy_rates_range`)
* `2026-05-14` to `2026-08-25`: `100,032` bars returned (`2026-05-14T02:40:00Z` to `2026-08-25T13:16:00Z`)
* `2026-05-01` to `2026-05-14`: `0` bars returned (`mt5.last_error() = (1, "Success")`)
* `2021-01-01` to `2026-05-01`: `0` bars returned (`mt5.last_error() = (1, "Success")`)

### TEST 3 — Symbol Differential (`EURUSD`, `GBPUSD`, `USDJPY`, `XAGUSD`, `XAUUSD`)
* **`EURUSD` M1**: `100,032` bars returned (First: `2026-05-14T02:40:00Z`)
* **`GBPUSD` M1**: `100,032` bars returned (First: `2026-05-14T02:40:00Z`)
* **`USDJPY` M1**: `100,032` bars returned (First: `2026-05-14T02:40:00Z`)
* **`XAGUSD` M1**: `100,032` bars returned (First: `2026-05-14T02:40:00Z`)
* **`XAUUSD` M1**: `100,032` bars returned (First: `2026-05-14T02:40:00Z`)
* *Finding*: The ~100k M1 bar limit is **universal across all symbols** on this specific connection, ruling out an `XAUUSD`-specific or metals-specific symbol limit.

### TEST 4 — Timeframe Differential on XAUUSD
* **`M1`**: `100,032` bars -> Earliest: **`2026-05-14`** (~3.5 months)
* **`M5`**: `100,032` bars -> Earliest: **`2025-08-10`** (~1 year)
* **`M15`**: `100,032` bars -> Earliest: **`2023-11-04`** (~2.8 years)
* **`H1`**: `100,032` bars -> Earliest: **`2010-02-18`** (~16.5 years)
* **`H4`**: `35,000` bars -> Earliest: **`2001-01-03`** (~25.5 years)
* **`D1`**: `6,500` bars -> Earliest: **`1999-01-04`** (~27.5 years)
* *Finding*: Higher timeframes (`H1`, `H4`, `D1`) provide deep historical data back to 1999–2010. The ~100k bar buffer limit applies per timeframe buffer on this connection.

### TEST 5 — Server Differential Test
* **Status**: `BLOCKED_BY_ENVIRONMENT`
* *Reason*: No secondary authenticated MT5 trade server account (e.g. `MetaQuotes-Demo` or `Alpari-Pro.ECN`) is logged in or accessible without credentials in the isolated container sandbox environment.

### TEST 7 — GUI History Sync
* **Status**: `NOT_EXECUTED`
* *Reason*: Container sandbox environment cannot execute interactive MT5 GUI chart scrolling.

---

## 3. Causal Hypothesis Classification

| Hypothesis | Evidence / Finding | Status |
| :--- | :--- | :--- |
| **LOCAL_MAXBARS_CAUSE** | MaxBars raised from 100k to 3M; returned count remained ~100k | **REJECTED** |
| **MT5_API_LIMIT_CAUSE** | `from_pos`, `range`, and `from` yield identical ~100k boundary | **REJECTED** |
| **XAUUSD_SYMBOL_LIMITATION** | All tested FX & Metal symbols (`EURUSD`, `GBPUSD`, `XAGUSD`) share the exact same 100,032 M1 bar boundary | **REJECTED** |
| **METALS_SYMBOL_LIMITATION** | Major FX currency pairs (`EURUSD`, `GBPUSD`, `USDJPY`) share the exact same 100,032 M1 bar boundary | **REJECTED** |
| **DEMO_ACCOUNT_LIMITATION** | Single account tested; secondary live/demo account comparison not executed | **UNDETERMINED** |
| **ALPARI_SERVER_LIMITATION** | Single trade server tested; secondary broker comparison not executed | **UNDETERMINED** |
| **BROKER_GLOBAL_LIMITATION** | Single broker tested; alternative brokers not tested | **UNDETERMINED** |
| **NATIVE_2021_XAUUSD_M1** | Zero M1 bars returned prior to 2026-05-14 via native MT5 IPC on this connection | **NOT_VERIFIED** |

---

## 4. Final Causal Statement

```text
ROOT_CAUSE = UNDETERMINED
```

*Statement*: The native MT5 connection on account `52961173` (`Alpari-MT5-Demo`) exposes `100,032` M1 bars starting `2026-05-14T02:40:00Z`. The causal reason why M1 history halts at ~100k bars while `H1`/`D1` history reaches 1999–2010 remains **UNDETERMINED** because an independent provider differential test against a secondary trade server (`MetaQuotes-Demo` or live ECN) has not been executed.
