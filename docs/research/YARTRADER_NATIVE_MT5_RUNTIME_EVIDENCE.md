# YarTrader Native MT5 Runtime Evidence

```text
YarTrader Native MT5 Runtime Evidence

Execution Environment:
Native Windows Server Host (C:\Projects\YarTrader) & Jules Execution Sandbox

Native Windows MT5 Status:
  - MT5 Build: 6140
  - Server / Broker: Alpari-MT5-Demo
  - Symbol: XAUUSD
  - Timeframe: M1
  - Connection State: CONNECTED
  - Read-Only Mode: ENFORCED (LIVE_TRADING_ENABLED=False)

Requested Coverage:
  - Start: 2021-01-01 00:00:00 UTC
  - End:   2026-08-25 23:59:59 UTC
  - Target Duration: ~5.6 Years

Actual Acquired Coverage:
  - First M1 Record: 2026-05-14 02:40:00 UTC (Unix timestamp: 1778726400)
  - Last M1 Record:  2026-08-25 18:30:00 UTC (Unix timestamp: 1787682600)
  - Acquired Bar Count: 100,346 authentic M1 bars
  - Actual Duration: ~103.6 calendar days (~0.28 years)
  - Coverage Classification: REAL_HISTORICAL_PARTIAL

Data Source Forensic Root Cause Analysis:
  - Broker Feed Horizon Limitation: The demo broker trade server (Alpari-MT5-Demo) strictly restricts online M1 history depth to ~100,000 bars (~3.4 calendar months) for real-time demo accounts.
  - Terminal Memory Configuration: Terminal `maxbars` is set to 3,000,000, but historical rate requests prior to May 14, 2026 return 0 bars directly from the trade server.
  - Truthfulness Policy Compliance: In strict accordance with the Non-Negotiable Truthfulness Policy, missing historical bars between 2021-01-01 and 2026-05-13 are NOT fabricated, backfilled, or interpolated.

Dataset Artifacts & Hashes:
  - Output File: data/research/xauusd_m1_real.json
  - Manifest File: data/research/xauusd_m1_manifest.json
  - Dataset Content SHA-256: e76968bf8e15ed0fcaeccdf211e0106cc2d0ea280901ba2a7f7aabd3e6a84304 (Hash of sorted record array)
  - Dataset File SHA-256: 662B51F13E71545EC0746B29A5A5109411850CF71DD0774B7D46F0B47A9043CD (Hash of JSON byte stream)
  - Manifest Status: COMPLETED_PARTIAL_COVERAGE

Research Pipeline Execution:
  - Research Executed: YES (GoldFractalIntelligenceEngine executed against xauusd_m1_real.json)
  - Research Consumed Dataset Content SHA-256: e76968bf8e15ed0fcaeccdf211e0106cc2d0ea280901ba2a7f7aabd3e6a84304
  - Hash Verification: PASS (Exact Content SHA-256 Match)
  - Research Result Classification: RESEARCH_RESULT_BASED_ON_PARTIAL_REAL_HISTORICAL_DATA

Safety & Compliance Verification:
  - Read-Only Safety: PASS (LIVE_TRADING_ENABLED=False enforced, 0 order_send calls)
  - Indicator-Free Integrity: PASS (0 active technical indicators, 0% Fibonacci dependencies)
  - Look-Ahead Safety: PASS (Prospective validation strictly isolates future price bars)
  - Research Unit Tests: 37/37 PASS
  - Frontend Build: PASS (Vite v5.4.21 production build succeeds)
  - YarTrader Brand Compliance: PASS (100% compliance; 0 new non-compliant brand references)

FINAL GATE:
BLOCKED
```

---

## Forensic Audit & Gate Decision Summary

1. **Forensic Explanation of 100,346-Bar Dataset:**
   - **Requested Period:** `2021-01-01 -> 2026-08-25` (~5.6 years).
   - **Actual Period Acquired:** `2026-05-14 02:40:00 UTC -> 2026-08-25 18:30:00 UTC` (100,346 bars, ~0.28 years).
   - **Root Cause:** The `Alpari-MT5-Demo` trade server maintains an online M1 buffer limit of approximately 100,000 bars for demo accounts. Earlier historical rates prior to May 14, 2026 are not stored on the broker's demo server feed.

2. **Non-Negotiable Truthfulness Policy Decision:**
   - Because the acquired dataset spans 103.6 calendar days instead of the requested 5.6 years, the dataset is truthfully classified as `REAL_HISTORICAL_PARTIAL`.
   - The Final Gate is set to **`BLOCKED`** with the explicit blocking reason: `NATIVE MT5 BROKER DEMO FEED DOES NOT PROVIDE 2021-2026 M1 HISTORY (SERVES MAX ~100,000 M1 BARS / MAY 14, 2026 - AUGUST 25, 2026)`.
