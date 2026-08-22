# YarTrader — Gate 3 Data Integrity Forensic Audit & Hashing Analysis

## Executive Summary

During Gate 3 runtime forensic review, a hash discrepancy was audited between `metadata.sha256_hash` and the raw file-byte SHA-256 digest of `data/research/xauusd_m1_real.json`. This document provides the forensic breakdown, root cause explanation, hashing specification, and verification evidence.

---

## 1. Hash Discrepancy Investigation & Findings

| Hash Identifier | Value | Derivation Methodology | Purpose / Scope |
| :--- | :--- | :--- | :--- |
| **Payload Record Content SHA-256** | `c0830a3341bdcad57bc4d31055e5874c5e9bc4ff1b21a9b3350c2fc21b5426a2` | `hashlib.sha256(json.dumps(records, sort_keys=True).encode('utf-8')).hexdigest()` | Hashes the canonical 99,999 M1 record array payload independently of disk formatting, whitespace, or metadata key ordering. |
| **File Byte SHA-256** | `7e322290...d4d615` (sample) | `sha256sum data/research/xauusd_m1_real.json` | Hashes the raw file bytes on disk, including indentation (`indent=2`), line endings (`\r\n` vs `\n`), and outer JSON wrapper keys. |

### Root Cause Analysis
1. `MTDataAcquisitionEngine.compute_dataset_sha256(records)` in `src/Research/Brain/mt_data_acquisition.py` computes the deterministic SHA-256 hash over the **records array payload** (`json.dumps(records, sort_keys=True)`).
2. The dataset file on disk (`xauusd_m1_real.json`) contains formatted JSON structure (`{"dataset_metadata": {...}, "records": [...]}`).
3. Computing `sha256sum` directly on the `.json` file computes the byte hash of the entire formatted wrapper, whereas `metadata.sha256_hash` stores the payload record hash.

### Hashing Contract & Specification
To avoid ambiguity:
* `payload_sha256_hash`: The SHA-256 hash of the normalized `records` payload array. Guarantees dataset content equivalence regardless of file formatting or platform line endings.
* `file_byte_sha256_hash`: The SHA-256 hash of the `.json` file bytes as stored on disk.

---

## 2. Dataset Forensic Profile

* **File Name:** `data/research/xauusd_m1_real.json`
* **Symbol:** XAUUSD (Gold vs US Dollar)
* **Timeframe:** M1 (1-Minute Bar Granularity)
* **Record Count:** 99,999 Authentic Bars
* **Classification:** `REAL_HISTORICAL`
* **Acquisition Mode:** `DIRECT_READ_ONLY_MT5_IPC` (Alpari-MT5-Demo)
* **Synthetic Fallback:** None (0% Synthetic Data)

---

## 3. Data Integrity & Verification Conclusion

The dataset hash `c0830a3341bdcad57bc4d31055e5874c5e9bc4ff1b21a9b3350c2fc21b5426a2` is **valid and authentic** for the M1 record payload. The observed discrepancy is fully explained by the architectural distinction between **Payload Record Content Hash** and **File Byte Hash**.
