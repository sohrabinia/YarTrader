# Content Layer Implementation Priority Plan

This document establishes the strategic, structured prioritization plan for the **TradeYar AI Content Intelligence Layer**. It maps the completed audit metrics into action items, detailing effort estimates, dependency chains, and precise classification matrices to guide upcoming developmental phases.

---

## 1. Component Priority Decision Matrix

The 7 core components are classified into four distinct maturity categories:
* **Production Ready:** Fully functioning code with 100% test coverage and active API routes.
* **Needs Completion:** Partial implementation exists; requires wiring or additional handlers.
* **Needs New Implementation:** Design/stubs exist, but actual business logic is missing.
* **Blocked:** Depends on unbuilt core modules.

| Component | Current Status Classification | Existing Code Location | Missing Work / Blockers | Priority (P0/P1/P2) | Effort Level |
|---|---|---|---|---|---|
| **AI Content Agent** | **Needs Completion** | `src/Growth/Agents/ContentAgents.py` | - No dynamic background loop to pull from Core Market Brain.<br>- Needs direct query triggers on session boundaries. | **P1** | **Medium** |
| **Article Generator** | **Needs Completion** | `src/Growth/Agents/MarketIntelligenceAgents.py` | - High-fidelity long-form template expansion.<br>- Draft storage tables / SQLite schema integrations. | **P1** | **Medium** |
| **Social Content Generator** | **Production Ready** | `src/Growth/Agents/ContentAgents.py` | - Integration with external Telegram/Twitter APIs is mocked (requires client wrapper implementation). | **P2** | **Small** |
| **Newsletter Agent** | **Needs Completion** | `src/Growth/Agents/DistributionAgents.py` | - Lacks SMTP/ESP (SendGrid/Mailgun) dispatch loop.<br>- Needs dynamic HTML template design. | **P2** | **Medium** |
| **SEO Agent** | **Needs Completion** | `src/Growth/Agents/ContentAgents.py`, `src/Growth/Agents/DistributionAgents.py` | - Replace deterministic string rules with live web crawler or third-party Search API queries. | **P2** | **Large** |
| **Publishing Pipeline** | **Needs Completion** | `src/Application/Services/growth_api_router.py` | - Needs persistent database model mapping (e.g. `ApprovalQueue` SQL table).<br>- CMS connection REST clients. | **P0** | **Medium** |
| **Trust Review Layer** | **Production Ready** | `src/Growth/Agents/TrustLearningAgents.py` | - Hard interceptor checkgate is 100% complete.<br>- Expand regex rules to semantic-aware LLM compliance audits (optional). | **P0** | **Small** |

---

## 2. Component Dependency Graph

In order to implement the missing layers systematically and securely, components must be developed in an order that respects their architectural dependencies:

```
[Core Market Brain / SRE Database]
              │
              ▼
    [Trust Review Layer]  <── (Hard Security & Claims Validation)
              │
              ▼
    [Publishing Pipeline] <── (PostgreSQL/SQLAlchemy Draft & Queue Tables)
         ┌────┼───────────────────────┐
         │    ▼                       ▼
         │  [AI Content Agent]     [Article Generator]
         │    │                       │
         ▼    ▼                       ▼
   [Social Generator]          [Newsletter Agent]
                                      ▲
                                      │
                                [SEO Agent] (Metadata, keyword scores & linking suggestions)
```

### Dependency Narrative:
1. **Trust Review Layer** is already production-ready and serves as the primary gateway for all content.
2. **Publishing Pipeline** represents the next critical foundation. It introduces SQL database tables to persist the content queues, without which the other agents remain stateless in-memory stubs.
3. **AI Content Agent** and **Article Generator** consume active Core Market Brain data and pass formatted drafts into the Publishing Pipeline.
4. **Social Generator** and **Newsletter Agent** format the approved assets dispatched from the pipeline.
5. **SEO Agent** provides metadata score evaluations and content suggestions to optimize the Newsletter and Article pipelines.

---

## 3. Recommended Implementation Order

To ensure high-fidelity, regression-free SRE transitions, the recommended rollout sequence is split into three incremental phases:

### Phase 1: Database Persistence & Core Pipeline Wiring (Priority: P0)
* **Goal:** Create PostgreSQL/SQLite database schemas to store drafts, queues, and dispatch logs.
* **Steps:**
  1. Define database tables: `ContentDraft`, `ContentApprovalQueue`, and `PublishedArchive`.
  2. Rewrite the FastAPI router endpoints in `growth_api_router.py` to persist data, replacing in-memory singleton lists.
  3. Wire the existing `TrustComplianceAgent` to scan all posts prior to database insertion.

### Phase 2: Active AI Synthesis & Long-Form Expansion (Priority: P1)
* **Goal:** Replace programmatic string templates with dynamic LLM generation and automate triggers.
* **Steps:**
  1. Integrate an LLM provider client (e.g. Anthropic Claude or OpenAI GPT-4) inside `ContentIntelligenceAgent` and `ResearchPublisherAgent`.
  2. Implement an automated daemon worker loop that triggers report/brief compilation at market session closes (e.g. NY close or Daily close).

### Phase 3: External Clients & Distribution Hooks (Priority: P2)
* **Goal:** Bridge the simulated routing flows to real external social channels and search APIs.
* **Steps:**
  1. Implement a Telegram Bot API wrapper to publish approved alerts directly to the TradeYar Community channel.
  2. Implement SMTP or ESP client integration to email weekly digests to registered users.
  3. Wire search trend scraper inputs into the SEO evaluation engine.
