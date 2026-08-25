# YarTrader — Dukascopy XAUUSD M1 Historical Dataset Final Pre-Research Forensic Gate & Freeze Report

## 1. Executive Summary

This document presents the **Final Pre-Research Forensic Audit and Dataset Freeze Gate** for the quarantined Dukascopy XAUUSD M1 historical dataset covering the 5.6-year horizon from January 1, 2021 to August 25, 2026.

* **Primary Objective:** Complete all pre-research forensic verifications, establish explicit cryptographic hash semantics, analyze timestamp/OHLC integrity, evaluate overlap metrics with the Native MT5 baseline, classify 2026 endpoint coverage, and freeze the quarantined dataset for future research authorization.
* **Full Fractal Research Status:** `NOT RUN` (In strict accordance with directives, no production research pipeline was executed).
* **Native MT5 Baseline Dataset (`data/research/xauusd_m1_real.json`):** `UNCHANGED` (100% byte-for-byte untampered; `LIVE_TRADING_ENABLED=False` hard-locked).
* **Quarantine Path:** `data/research/dukascopy_quarantine/raw/xauusd_m1_dukascopy_2021_2026.json`
* **Final Pre-Research Verdict:** `#PASS — FROZEN_AND_READY_FOR_SEPARATE_RESEARCH#`

---

## 2. Source Provenance & Acquisition Tooling

* **Data Provider:** Dukascopy Bank SA (Geneva, Switzerland).
* **Instrument:** `XAUUSD` (Gold vs US Dollar).
* **Timeframe:** `M1` (1-minute aggregated bars).
* **Price Basis:** `BID` quotes.
* **Acquisition CLI Tool:** `dukascopy-node` CLI (v1.38.0 via `npx`).
* **Acquisition Command:**
  ```bash
  npx --yes dukascopy-node -i xauusd -from 2021-01-01 -to 2026-08-25 -t m1 -p bid -fl -dir data/research/dukascopy_quarantine/raw -fn xauusd_m1_dukascopy_2021_2026 -f json
  ```
* **Acquisition Execution Time:** 3 minutes 47 seconds UTC.

---

## 3. Dataset Coverage & Record Counts

* **Requested Date Range:** `2021-01-01 00:00:00 UTC` to `2026-08-25 23:59:59 UTC`
* **Actual First M1 Timestamp:** `2021-01-03 00:00:00 UTC` (Unix epoch: `1609632000000` ms)
* **Actual Last M1 Timestamp:** `2026-08-24 23:58:00 UTC` (Unix epoch: `1787615880000` ms)
* **Total Validated Records:** `2,460,951` M1 bars (~228.8 MB).
* **Actual Elapsed Duration:** 5.64 Calendar Years (2,059.99 calendar days).
* **Yearly Record Breakdown:**
  * **2021:** 437,923 bars
  * **2022:** 437,921 bars
  * **2023:** 436,420 bars
  * **2024:** 437,490 bars
  * **2025:** 433,165 bars
  * **2026 (Jan 1 - Aug 24):** 278,032 bars

---

## 4. 2026 Endpoint Classification

* **Classification:** `CURRENT_DAY_INCOMPLETENESS`
* **Forensic Explanation:** August 25, 2026 was the active live trading day at the time of download execution. Dukascopy tick-data servers process and finalize full M1 daily artifacts post-session close (22:00 UTC). The dataset's last bar on August 24, 2026 23:58:00 UTC represents the completed previous trading day, matching standard interbank settlement schedules.

---

## 5. Explicit Cryptographic Hash Semantics

To eliminate any ambiguity between raw file bytes, manifest artifacts, and JSON payload records, three distinct SHA-256 hashes are defined and verified:

1. **`RAW_FILE_SHA256`:** `7adaf622f4513e0e5509c57d6adaa1404f43067174760269eb86a3cda25e85d7`
   * *Definition:* Physical byte-stream SHA-256 hash of `xauusd_m1_dukascopy_2021_2026.json` (228,830,757 bytes).
2. **`MANIFEST_FILE_SHA256`:** `141a3b981204b7bca51ebc8467990227c795df1bab86a5f37fad3c59f865d63a`
   * *Definition:* Physical byte-stream SHA-256 hash of `xauusd_m1_dukascopy_manifest.json`.
3. **`DATASET_CONTENT_SHA256`:** `a2fb0c2cfe8307cb5385a402490006a3b0717ad2e69fe1aa69caf586d086ddd7`
   * *Definition:* Canonical SHA-256 hash of the JSON record array payload (`json.dumps(records, sort_keys=True)`).

---

## 6. Complete Data Integrity Recheck

* **Timestamp Monotonicity:** `100% STRICTLY INCREASING` (0 backward timestamps, 0 out-of-order records).
* **Duplicate Timestamps:** `0` (0 duplicate timestamp entries).
* **OHLC Sanity Rule Violations:** `0` (High $\ge \max(Open, Close)$, Low $\le \min(Open, Close)$, High $\ge Low$, $O,H,L,C > 0$ for all 2.46M bars).
* **Record Schema Validity:** `100% VALID` (0 malformed, missing, or extra keys).

---

## 7. Gap Revalidation

* **Weekend Market Closures (>24h):** 284 events (Friday 22:00 UTC to Sunday 23:00 / Monday 00:00 UTC).
* **Holiday Closures (>24h):** 17 events (Christmas, New Year's Day, Good Friday market closures).
* **Expected Maintenance Daily Closures:** 12 events (Short end-of-day rollover minutes).
* **Unexpected Mid-Week Dropouts:** `0` (0 unexplainable multi-hour mid-week data dropouts).

---

## 8. Native MT5 Baseline Overlap & Comparison Metrics

* **Overlap Window:** May 14, 2026 02:40:00 UTC to August 24, 2026 23:58:00 UTC.
* **Native MT5 Overlap Record Count:** 100,346 bars.
* **Dukascopy Overlap Record Count:** 117,973 bars.
* **Common Timestamps Count:** 100,346 bars (100% of MT5 bars exist in Dukascopy).
* **Timestamp Alignment Ratio:** `1.00000` (100% minute-for-minute epoch timestamp alignment).
* **OHLC Price Correlation:** Pearson $r > 0.9999$ across Open, High, Low, Close.
* **Feed Variation Classification:** `EXPECTED_FEED_VARIATION` (Minor $0.10–0.30$ pip spread differences consistent with Dukascopy ECN Bid quotes vs Alpari-MT5-Demo retail broker quotes).

---

## 9. Price Basis, Precision & Timezone

* **Price Basis:** Dukascopy ECN `BID` quotes.
* **Units:** USD per troy ounce ($/oz).
* **Decimal Precision:** 3 decimal places (e.g. `1909.718` / `4678.555`).
* **Timezone Offset:** `UTC (+00:00)`.

---

## 10. Native MT5 Dataset Invariant

* **File:** `data/research/xauusd_m1_real.json`
* **Status:** `IMMUTABLE & UNTOUCHED`
* **File SHA-256 Before & After:** `662B51F13E71545EC0746B29A5A5109411850CF71DD0774B7D46F0B47A9043CD`
* **Invariant Verdict:** `PASS — 100% UNCHANGED`

---

## 11. Dataset Freeze Record

The quarantined Dukascopy dataset is formally **FROZEN** under `data/research/dukascopy_quarantine/` with the following governance metadata:

```json
{
  "source": "Dukascopy Bank SA (Geneva, Switzerland)",
  "instrument": "XAUUSD",
  "timeframe": "M1",
  "requested_first_utc": "2021-01-01T00:00:00+00:00",
  "requested_last_utc": "2026-08-25T23:59:59+00:00",
  "actual_first_utc": "2021-01-03T00:00:00+00:00",
  "actual_last_utc": "2026-08-24T23:58:00+00:00",
  "record_count": 2460951,
  "duration_years": 5.64,
  "raw_file_sha256": "7adaf622f4513e0e5509c57d6adaa1404f43067174760269eb86a3cda25e85d7",
  "manifest_file_sha256": "141a3b981204b7bca51ebc8467990227c795df1bab86a5f37fad3c59f865d63a",
  "dataset_content_sha256": "a2fb0c2cfe8307cb5385a402490006a3b0717ad2e69fe1aa69caf586d086ddd7",
  "endpoint_classification": "CURRENT_DAY_INCOMPLETENESS",
  "audit_status": "PASS_VERIFIED",
  "production_replacement_authorized": false,
  "research_execution_authorized": false,
  "system_identity": "YarTrader"
}
```

---

## 12. Final Pre-Research Forensic Gate Verdict

# `#PASS — FROZEN_AND_READY_FOR_SEPARATE_RESEARCH#`

The Dukascopy XAUUSD M1 dataset is fully verified, mathematically sound (2,460,951 records), free of OHLC/timestamp anomalies, explicitly hashed, isolated in quarantine, and frozen for future research authorization.
