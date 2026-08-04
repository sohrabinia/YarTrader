# Trust Review System — Phase P0 Production Implementation

## 1. Implementation Status
* **Status:** `IMPLEMENTED` (Extensible Compliance Pipeline & Gate)

## 2. Production Code Architecture
* **File Paths:**
  * `src/Growth/ContentIntelligence/trust_engine.py` (Validation rules and scan manager)
  * `src/Application/Services/content_api_router.py` (FastAPI router)
* **Main Classes:**
  * `TrustReviewEngine`: Chained rule engine analyzing generated content across language channels.
* **API Integration:**
  * Every generated draft is dynamically processed by the `TrustReviewEngine` prior to saving, returning structured `ReviewResult` metadata and changing draft status to `APPROVED` or `REJECTED`.

## 3. Chained Rule Audits (Bilingual English & Persian Support)

### A. Financial Claim Detection (`FinancialClaimRules`)
Scans draft body and titles for guarantees, profit numbers, absolute win rate promises, or unverified hype.
* **English Violations:** Matches on terms like `guarantee`, `profit promise`, `100% profit`, `double your`, or daily returns `%`.
* **Persian Violations:** Matches on terms like `تضمین` (guarantee), `سود تضمین` (guaranteed profit), `۱۰۰٪` (100%), `درصد سود روزانه` (daily profit percent) using both standard Western and Persian digit character sets.

### B. Signal Language Detection (`SignalLanguageRules`)
Prevents signal selling prose and direct buying/selling commands.
* **English Violations:** Matches terms like `buy now immediately`, `sell now`, or `paid signals`.
* **Persian Violations:** Matches terms like `خرید فوری` (buy immediately), `فروش الان` (sell now), or `کانال سیگنال` (signals channel).

### C. Missing Disclosure Insertion (`DisclosureRules`)
Automatically formats and appends standard risk disclaimers based on target language:
* **English Disclosure:** Appends standard risk disclosures reminding readers of simulation-only environments.
* **Persian Disclosure:** Appends Persian disclaimers (`سلب مسئولیت...`) explaining the simulated educational nature of TradeYar AI insights.

### D. Source Verification (`SourceVerificationRules`)
Ensures every draft contains valid reference mapping back to its original underlying quant research ID.

---

## 4. Structured Review Log Output Schema
Every review yields a precise, structured audit log:
```json
{
  "status": "APPROVED | REJECTED | FLAGGED",
  "violations": [
    {
      "rule_id": "FinancialClaimRules",
      "severity": "REJECT",
      "message": "Profit guarantees or win rate promises are strictly prohibited."
    }
  ],
  "disclosures": [
    "DISCLAIMER: All TradeYar AI analyses are for simulated and educational purposes only..."
  ],
  "reviewed_at": "2026-08-20T14:30:00Z"
}
```
This structured schema guarantees 100% traceability for auditing.
