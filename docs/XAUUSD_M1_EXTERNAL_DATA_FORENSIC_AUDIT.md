# YarTrader XAUUSD M1 External Dataset Acquisition & Forensic Audit Report

## Executive Summary & Provenance Verdict

This report documents the forensic investigation, source discovery, acquisition attempts, and provenance verification for acquiring an authentic **XAUUSD M1** historical dataset covering **2021-01-01 to 2026-08-25** for YarTrader fractal research.

```text
DATASET_STATUS = DATA_UNAVAILABLE
PROVENANCE_STATUS = UNVERIFIED
2021_COVERAGE = NOT_AVAILABLE
2022_COVERAGE = NOT_AVAILABLE
2023_COVERAGE = NOT_AVAILABLE
2024_COVERAGE = NOT_AVAILABLE
2025_COVERAGE = NOT_AVAILABLE
2026_COVERAGE = NOT_AVAILABLE
FRACTAL_RESEARCH_READY = BLOCKED
```

---

## 1. Source Discovery & Investigation

Target range: `2021-01-01 -> 2026-08-25`

### Evaluated External Sources

| Candidate Source | Evaluated URL / Endpoint | Acquisition Result | Forensic Finding |
| :--- | :--- | :--- | :--- |
| **Dukascopy Bank SA** | `https://datafeed.dukascopy.com/datafeed/XAUUSD/...` | **BLOCKED (HTTP 429 / Timeout)** | Direct automated bi5 tick requests are rate-limited / blocked by Cloudflare edge filters. |
| **Yahoo Finance API** | `https://query1.finance.yahoo.com/v8/finance/chart/GC=F` | **REJECTED (8-day Limit)** | 1m granularity queries are restricted by Yahoo API to a maximum range of 8 days (`HTTP 422`). |
| **HistData.com** | `https://www.histdata.com/.../xauusd` | **BLOCKED (Session / Token Required)** | M1 ASCII CSV ZIP archives require interactive browser session tokens and CSRF form submissions. |
| **Third-Party GitHub / Kaggle Mirrors** | `https://github.com/.../xauusd` | **REJECTED (Unverified Third-Party)** | Unauthenticated third-party mirrors fail strict provenance rules ("GitHub repository claiming Dukascopy data is not equivalent to downloading directly from Dukascopy"). |

---

## 2. Sample Verification & Forensic Analysis

### SHA-256 Source File Hashes
```text
NO_AUTHENTIC_SOURCE_FILE_DOWNLOADED
```

### Forensic Validation Metrics
- **Identity**: `XAUUSD` (Spot Gold)
- **Timeframe**: `M1`
- **UTC Normalization**: `N/A`
- **Monotonic Ordering**: `N/A`
- **OHLC Integrity**: `N/A`
- **Gap & Continuity Analysis**: `N/A`
- **Bid/Ask Integrity**: `N/A`

---

## 3. Comparison Against Native MT5 Baseline

| Property | Native MT5 Baseline | External Candidate Source |
| :--- | :--- | :--- |
| **Trade Server** | `Alpari-MT5-Demo` (`Account 52961173`) | Dukascopy / HistData / Yahoo |
| **Available M1 Range** | `2026-05-14T02:40:00Z -> 2026-08-25T13:16:00Z` | `N/A` (Download blocked) |
| **Bar Count** | `100,032 bars` | `0 bars` |
| **2021–2025 History** | `NOT_VERIFIED` | `NOT_AVAILABLE` |
| **Provenance Status** | **VERIFIED (Native IPC)** | **UNVERIFIED** |

---

## 4. Provenance Classification

```text
PROVENANCE_CLASSIFICATION = UNVERIFIED_EXTERNAL_DATA
```

### Strict Forensic Rules Applied
1. **Zero Synthetic Data Fabrication**: No synthetic candles were generated or interpolated.
2. **Zero Unverified Sources**: Third-party GitHub/Kaggle mirrors were rejected because source chain-of-custody cannot be independently proven.
3. **No Silent Repair / Timezone Alteration**: No dataset file was created or committed without first-party cryptographic proof.

---

## 5. YarTrader Dataset & Gate Status

* **Dataset Path**: `data/research/xauusd_m1_real.json` (File absent on disk)
* **Gates 0–2 Research Status**: **BLOCKED**

```text
DATASET_STATUS = DATA_UNAVAILABLE
PROVENANCE_STATUS = UNVERIFIED
FRACTAL_RESEARCH_READY = BLOCKED
```

---

## 6. Exact Operational Requirement to Unblock Gates 0–2

To unblock historical fractal research spanning 2021–2026:
1. Log into a live/Pro ECN MT5 trade server account (e.g. `Alpari-Pro.ECN` or `MetaQuotes-Demo`) on Windows Server `5.102.37.180` where multi-year M1 history archives are served directly.
2. Execute `mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_M1, 0, 2000000)` via native read-only MT5 IPC.
3. The engine will calculate SHA-256 checksums and automatically persist the verified authentic dataset to `data/research/xauusd_m1_real.json`.
