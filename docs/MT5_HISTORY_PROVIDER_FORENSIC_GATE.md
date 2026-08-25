# YarTrader Native MT5 Historical Provider Differential Forensic Gate Report

## Executive Summary & Final Gate Verdict

This report documents the provider-differential forensic investigation into why native MetaTrader 5 currently returns approximately 100,032 **XAUUSD M1** bars starting on **2026-05-14T02:40:00Z** on the **Alpari-MT5-Demo** connection (`Account 52961173`, Terminal Build 6140).

```text
FINAL_CLASSIFICATION=INSUFFICIENT_EVIDENCE
FRACTAL_2021_2026_DATASET=NOT_AVAILABLE
FRACTAL_RESEARCH_GATE=BLOCKED
```

---

## 1. Environment Baseline & Verified Facts

```text
Terminal Executable: C:\Program Files\MetaTrader 5\terminal64.exe
Terminal Build: 6140
Trade Server: Alpari-MT5-Demo
Demo Account: 52961173 (Read-Only)
Data Directory: C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075
Symbol: XAUUSD
Timeframe: M1
MaxBars Setting: 3,000,000 (Increased from 100,000 baseline)
Returned Bar Count: 100,032
First Available Bar: 2026-05-14T02:40:00Z
Last Available Bar: 2026-08-25T13:16:00Z
```

---

## 2. Tested vs. Untested Providers

### Tested Provider
* **Server**: `Alpari-MT5-Demo`
* **Account**: `52961173`
* **MaxBars**: `3,000,000`
* **Result**: `100,032` bars (First: `2026-05-14T02:40:00Z`, Last: `2026-08-25T13:16:00Z`)

### Untested Providers
* `MetaQuotes-Demo`
* `Alpari-Pro.ECN`
* Alternative Broker MT5 Trade Servers

*Blocker Reason*: No secondary authenticated MT5 trade server account is logged in or accessible without credentials in the isolated container sandbox environment.

---

## 3. History Filesystem Forensics

Local history cache directory:
`C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\bases\Alpari-MT5-Demo\history\XAUUSD\`

```text
Files Found:
  - 2026.hcc (Binary M1 history cache for year 2026)
  - history.dat
  - symbols.raw

Missing Files:
  - 2025.hcc (ABSENT)
  - 2024.hcc (ABSENT)
  - 2023.hcc (ABSENT)
  - 2022.hcc (ABSENT)
  - 2021.hcc (ABSENT)
```

*Forensic Finding*: The local terminal history cache contains **only 2026 data** (`2026.hcc`). Binary cache chunks for 2021–2025 do not exist in the local terminal directory.

---

## 4. Date-Range Probe Results (`copy_rates_range`)

| Requested Range | Returned Bar Count | First Bar Timestamp | Last Bar Timestamp | `mt5.last_error()` |
| :--- | :--- | :--- | :--- | :--- |
| **2026-05-14 -> 2026-08-25** | 100,032 | `2026-05-14T02:40:00Z` | `2026-08-25T13:16:00Z` | `(1, "Success")` |
| **2026-04-01 -> 2026-05-01** | 0 | `N/A` | `N/A` | `(1, "Success")` |
| **2026-01-01 -> 2026-02-01** | 0 | `N/A` | `N/A` | `(1, "Success")` |
| **2025-01-01 -> 2025-02-01** | 0 | `N/A` | `N/A` | `(1, "Success")` |
| **2024-01-01 -> 2024-02-01** | 0 | `N/A` | `N/A` | `(1, "Success")` |
| **2023-01-01 -> 2023-02-01** | 0 | `N/A` | `N/A` | `(1, "Success")` |
| **2022-01-01 -> 2022-02-01** | 0 | `N/A` | `N/A` | `(1, "Success")` |
| **2021-01-01 -> 2021-02-01** | 0 | `N/A` | `N/A` | `(1, "Success")` |

---

## 5. Strict Evidence Matrix

| Hypothesis | Observed Evidence | Forensic Status |
| :--- | :--- | :--- |
| **MaxBars caused 100k boundary** | MaxBars raised from 100k to 3M, returned count remained ~100k (100,032) | **REJECTED** |
| **Local cache contains older history** | Filesystem audit shows only `2026.hcc` exists; 2021–2025 `.hcc` files are absent | **REJECTED** |
| **Alpari Demo server-side retention policy** | Single provider tested; secondary provider differential test not executed | **UNPROVEN** |
| **Broker-wide history limitation** | Single broker tested; alternative brokers not tested | **UNPROVEN** |
| **XAUUSD symbol-specific limitation** | Single symbol tested; alternative gold symbols not tested | **UNPROVEN** |
| **MT5 API limitation** | `copy_rates_from_pos`, `copy_rates_range`, and `copy_rates_from` yield identical boundary | **REJECTED** |
| **Native 2021 XAUUSD M1 available** | Zero bars returned for 2021–2025 intervals via native MT5 IPC | **NOT VERIFIED** |

---

## 6. Distinguishing Facts from Hypotheses

* **OBSERVED FACT**: The active MT5 connection (`Account 52961173`, `Alpari-MT5-Demo`) currently returns `100,032` M1 bars starting on `2026-05-14T02:40:00Z`.
* **OBSERVED FACT**: Raising `maxbars` to `3,000,000` did not expand the earliest bar timestamp.
* **HYPOTHESIS**: `Alpari-MT5-Demo` trade server enforces a server-side history retention cap for demo accounts. (*Unproven until tested against a secondary provider*).
* **UNTESTED**: Querying M1 history on `MetaQuotes-Demo` or `Alpari-Pro.ECN`.

---

## 7. Final Classification & Next Action

```text
FINAL_CLASSIFICATION=INSUFFICIENT_EVIDENCE
```

### Next Required Action
Log into a secondary MT5 demo or live account on another trade server (e.g., `MetaQuotes-Demo`) on Windows Server `5.102.37.180` and execute:
```python
mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_M1, 0, 2000000)
```
Compare returned bar counts to complete the provider differential test.
