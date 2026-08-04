# Content Intelligence Pipeline — Phase P0 Production Implementation

## 1. Introduction
The **TradeYar AI Content Intelligence Pipeline** establishes a secure, compliant process for transforming raw mathematical research observations into channel-ready, compliant textual artifacts.

This document describes the flow from initial quant payloads through decoupled providers and compliance gates into persistent storage.

---

## 2. Core Execution Flow

```
[Underlying Quant Research Payload]
               │
               ▼ (Symbols, Source reference, Raw observations)
[ContentIntelligenceInterface]
               │
               ├─► [MockProviderAdapter (Safe offline & CI/CD)]
               └─► [ProductionLLMProviderAdapter (Live dynamic generation)]
               │
               ▼ (Bilingual Drafting: English or Persian)
[TrustReviewEngine Extensible Validation Chain]
               │
               ├─► [Rule 1: FinancialClaimRules (Guarantees blocker)]
               ├─► [Rule 2: SignalLanguageRules (Commands blocker)]
               ├─► [Rule 3: SourceVerificationRules (Lineage validator)]
               └─► [Rule 4: DisclosureRules (Auto-risk disclaimer appender)]
               │
               ▼ (ReviewResult Evaluation: APPROVED, REJECTED)
[ContentRepository SQL Storage]
               │
               ▼ (Isolated Schema: ContentDraft, ContentSource, ContentReview)
[SQLite persistence Database (runtime_logs/content_intelligence.db)]
               │
               ▼
[REST API Layer (/api/content/drafts)]
```

---

## 3. Database Migration Isolation SRE Guidelines
* **Zero Modification Policy:** Under no circumstances should content layer schemas modify or touch any existing core mathematical or SRE table models in `Intelligence Core`.
* **Database Isolation:** All content intelligence schemas reside inside an isolated, dedicated SQLite database file `runtime_logs/content_intelligence.db`.
* **Reversibility:** Every migration MUST support up/down methods:
  - `ContentDBManager.up()`: Sets up the draft, source lineage, and compliance audit tables.
  - `ContentDBManager.down()`: Drops the tables cleanly, supporting 100% reversible rollbacks.
