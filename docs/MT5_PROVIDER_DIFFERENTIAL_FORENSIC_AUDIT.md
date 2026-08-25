# YarTrader Native MT5 Provider Differential Historical Forensic Audit

## Executive Summary & Final Gate Verdict

This report provides the forensic audit of native MetaTrader 5 historical M1 data availability for **XAUUSD** on the **Alpari-MT5-Demo** connection (`Account 52961173`, Terminal Build 6140).

```text
FINAL_CLASSIFICATION=HISTORICAL_PROVIDER_LIMIT_UNPROVEN
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

## 2. Terminal Profiles Discovered

```text
PROFILE 1 (D0E8209F77C8CF37AD8BF550E51FF075):
  MetaTrader 5 Active Terminal Data Directory (Connected to Alpari-MT5-Demo)

PROFILE 2 (50CA3DFB510CC5A8F28B48D1BF2A5702):
  Secondary MT4/MT5 Terminal Instance
```

*Finding*: No secondary authenticated MT5 account profile (e.g. `MetaQuotes-Demo` or `Alpari-Pro.ECN`) is logged in or accessible without credentials in the current environment.

---

## 3. History Filesystem Forensics

Local history cache inspection under:
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

*Forensic Conclusion*: Local cache contains **only 2026 data** (`2026.hcc`). Older historical binary cache chunks do not exist in the local terminal directory.

---

## 4. Date-Range Probe Results (`copy_rates_range`)

Native MT5 API probes executed across specific historical intervals:

| Requested Range | Returned Count | First Bar Timestamp | Last Bar Timestamp | `mt5.last_error()` |
| :--- | :--- | :--- | :--- | :--- |
| **2026-05-14 -> 2026-08-25** | 100,032 | `2026-05-14T02:40:00Z` | `2026-08-25T13:16:00Z` | `(1, "Success")` |
| **2026-04-01 -> 2026-05-01** | 0 | `N/A` | `N/A` | `(1, "Success")` |
| **2026-01-01 -> 2026-02-01** | 0 | `N/A` | `N/A` | `(1, "Success")` |
| **2025-01-01 -> 2025-02-01** | 0 | `N/A` | `N/A` | `(1, "Success")` |
| **2024-01-01 -> 2024-02-01** | 0 | `N/A` | `N/A` | `(1, "Success")` |
| **2023-01-01 -> 2023-02-01** | 0 | `N/A` | `N/A` | `(1, "Success")` |
| **2022-01-01 -> 2022-02-01** | 0 | `N/A` | `N/A` | `(1, "Success")` |
| **2021-01-01 -> 2021-02-01** | 0 | `N/A` | `N/A` | `(1, "Success")` |

*Finding*: All requests prior to `2026-05-14` return 0 bars with `last_error = (1, "Success")`.

---

## 5. MT5 API Cross-Check (`from_pos` vs `range` vs `from`)

All native MT5 API functions (`mt5.copy_rates_from_pos`, `mt5.copy_rates_range`, `mt5.copy_rates_from`) yield identical historical limits:
* Maximum retrievable count: **100,032 bars**
* Earliest timestamp: **`2026-05-14T02:40:00Z`**

---

## 6. Evidence Matrix

| Hypothesis | Evidence | Status |
| :--- | :--- | :--- |
| **MaxBars caused 100k boundary** | MaxBars raised from 100k to 3M, returned count remained ~100k (100,032) | **REJECTED** |
| **Local cache contains older history** | Filesystem audit shows only `2026.hcc` exists; 2021–2025 `.hcc` files are absent | **REJECTED** |
| **Alpari Demo server limitation** | Requires differential provider test against secondary trade server | **UNPROVEN** |
| **Broker-wide limitation** | Requires differential test against alternative broker/server | **UNPROVEN** |
| **XAUUSD-specific limitation** | Requires differential test against alternative symbol (e.g. GOLD) | **UNPROVEN** |
| **MT5 API limitation** | `copy_rates_from_pos`, `copy_rates_range`, and `copy_rates_from` yield identical boundary | **REJECTED** |
| **Native 2021 XAUUSD M1 available** | Zero bars returned for 2021–2025 intervals via native MT5 IPC | **NOT VERIFIED** |

---

## 7. Unresolved Questions

1. Does the trade server `Alpari-MT5-Demo` purge M1 history older than ~100k bars for demo accounts, or does a live/Pro ECN server retain multi-year history?
2. Can manual chart scrolling in MT5 GUI trigger server-side history synchronization to populate `2021.hcc`–`2025.hcc` binary cache files on disk?

---

## 8. Exact Next Action Required for 2021–2026 XAUUSD M1 Data

To conduct Gates 0–2 historical fractal research spanning 2021–2026:
1. Log into a live/Pro ECN MT5 trade server or `MetaQuotes-Demo` account on server `5.102.37.180`.
2. Scroll the `XAUUSD M1` chart back to 2021 in MT5 GUI (or execute `mt5.copy_rates_range` iteratively) to force server-side history download into `.hcc` files.
3. Export the complete multi-year M1 dataset to `data/research/xauusd_m1_real.json`.
