# YARTRADER MASTER CANONICAL AGENT CATALOG & INVENTORY AUDIT

**Version:** 1.0.0
**Effective Date:** March 2026
**Status:** AUDITED CANONICAL INVENTORY

---

## 1. Executive Summary

A forensic inventory audit of all registered and implemented agents across `src/Application/Agents/`, `src/Growth/Agents/`, and `src/Intelligence/Orchestration/` was conducted to establish exact agent identities, source files, contract bindings, autonomy levels, and router visibility.

---

## 2. Canonical Specialized Agent Roster

### 1. Market Intelligence Agent (`agent-market-intel`)
- **Domain:** Financial Perception
- **Source File:** `src/Application/Agents/concrete_agents.py`
- **Contract:** `docs/architecture/agents/MARKET_INTELLIGENCE_AGENT_CONTRACT.md`
- **Autonomy Level:** L1 (Recommendation)
- **Lifecycle Status:** `ACTIVE` (Verified via Final Activation Gate)
- **Router / Planner Visibility:** `VERIFIED_ROUTABLE`
- **Responsibilities:** RTM supply/demand zones, Price Action, Fractal scale mapping, Market regime classification.
- **Forbidden Actions:** Order placement, buy/sell commands, position sizing, risk policy overrides.

### 2. Research Agent (`agent-research`)
- **Domain:** Scientific Strategy Research
- **Source File:** `src/Application/Agents/concrete_agents.py`
- **Contract:** `docs/architecture/agents/RESEARCH_AGENT_CONTRACT.md`
- **Autonomy Level:** L1 (Recommendation)
- **Lifecycle Status:** `ACTIVE` (Verified via Final Activation Gate)
- **Router / Planner Visibility:** `VERIFIED_ROUTABLE`
- **Responsibilities:** Hypothesis formulation, M1 bar historical replay, walk-forward evaluation, baseline vs OOS scoring.
- **Forbidden Actions:** Direct strategy deployment to production, live order submission.

### 3. Risk Advisor Agent (`agent-risk-advisor`)
- **Domain:** Financial Risk Advisory
- **Source File:** `src/Application/Agents/concrete_agents.py`
- **Contract:** `docs/architecture/agents/RISK_ADVISOR_AGENT_CONTRACT.md`
- **Autonomy Level:** L1 (Recommendation)
- **Lifecycle Status:** `ACTIVE` (Verified via Final Activation Gate)
- **Router / Planner Visibility:** `VERIFIED_ROUTABLE`
- **Responsibilities:** Portfolio volatility modeling, drawdown stress-testing, exposure alerts, risk advisories.
- **Forbidden Actions:** Risk % modification, max position size alteration, Risk Engine bypass, trade execution.

### 4. Conversational Support Agent (`agent-support`)
- **Domain:** Customer Support & Technical Assistance
- **Source File:** `src/Application/Agents/support_agent.py`
- **Contract:** `docs/architecture/agents/SUPPORT_AGENT_CONTRACT.md`
- **Autonomy Level:** L3 (Policy-Bounded)
- **Lifecycle Status:** `ACTIVE` (Verified via Final Activation Gate)
- **Router / Planner Visibility:** `VERIFIED_ROUTABLE`
- **Responsibilities:** Multi-turn chat, MT5 connection troubleshooting, billing guidance, ticket escalations, 5 locales (`fa`, `en`, `tr`, `ar`, `de`).
- **Forbidden Actions:** Financial trades, account credential mutation, secret key access, ungrounded answers.

### 5. Growth & Content Agent (`agent-growth-content`)
- **Domain:** Growth, Marketing & Educational Publishing
- **Source File:** `src/Growth/Agents/ContentAgents.py`
- **Contract:** `docs/architecture/agents/GROWTH_CONTENT_AGENT_CONTRACT.md`
- **Autonomy Level:** L2 (Act with Approval)
- **Lifecycle Status:** `ACTIVE` (Verified via Final Activation Gate)
- **Router / Planner Visibility:** `VERIFIED_ROUTABLE`
- **Responsibilities:** Educational article writing, fact-checking, SEO/AEO/GEO optimization, JSON-LD schema generation, translations.
- **Forbidden Actions:** Direct publication without editorial queue sign-off, fabrication of performance numbers or quotes.

### 6. News Intelligence Agent (`agent-news-intel`)
- **Domain:** News Ingestion & Macro Intelligence
- **Source File:** `src/Growth/Agents/ContentAgents.py`
- **Contract:** `docs/architecture/agents/NEWS_INTELLIGENCE_AGENT_CONTRACT.md`
- **Autonomy Level:** L2 (Act with Approval)
- **Lifecycle Status:** `ACTIVE` (Verified via Final Activation Gate)
- **Router / Planner Visibility:** `VERIFIED_ROUTABLE`
- **Responsibilities:** Ingestion of economic news, source verification, timestamping, deduplication, summary drafts.
- **Forbidden Actions:** Unverified news publishing, market prediction guarantees.

### 7. Operations Agent (`agent-operations`)
- **Domain:** Platform Operations
- **Source File:** `src/Application/Agents/system_agents.py`
- **Contract:** `docs/architecture/agents/OPERATIONS_AGENT_CONTRACT.md`
- **Autonomy Level:** L3 (Policy-Bounded)
- **Lifecycle Status:** `ACTIVE` (Verified via Final Activation Gate)
- **Router / Planner Visibility:** `VERIFIED_ROUTABLE`
- **Responsibilities:** Monitoring service health (`/health`, `/ready`), background task loops, worker uptime.
- **Forbidden Actions:** Destructive production database operations, server shutdown without authorization.

### 8. Engineering Agent (`agent-engineering`)
- **Domain:** Software Maintenance
- **Source File:** `src/Application/Agents/system_agents.py`
- **Contract:** `docs/architecture/agents/ENGINEERING_AGENT_CONTRACT.md`
- **Autonomy Level:** L2 (Act with Approval)
- **Lifecycle Status:** `ACTIVE` (Verified via Final Activation Gate)
- **Router / Planner Visibility:** `VERIFIED_ROUTABLE`
- **Responsibilities:** Traceback diagnosis, code structure evaluation, test coverage checks, refactoring proposals.
- **Forbidden Actions:** Unrestricted git push to main without review, credential modifications.

### 9. QA Agent (`agent-qa`)
- **Domain:** Quality Assurance & Testing
- **Source File:** `src/Application/Agents/system_agents.py`
- **Contract:** `docs/architecture/agents/QA_AGENT_CONTRACT.md`
- **Autonomy Level:** L3 (Policy-Bounded)
- **Lifecycle Status:** `ACTIVE` (Verified via Final Activation Gate)
- **Router / Planner Visibility:** `VERIFIED_ROUTABLE`
- **Responsibilities:** Test scenario planning, automated regression test suite verification, API schema audits.
- **Forbidden Actions:** Bypassing test failures, force-clearing release blockers.

### 10. Security Agent (`agent-security`)
- **Domain:** System Security & Vulnerability Defense
- **Source File:** `src/Application/Agents/system_agents.py`
- **Contract:** `docs/architecture/agents/SECURITY_AGENT_CONTRACT.md`
- **Autonomy Level:** L3 (Policy-Bounded)
- **Lifecycle Status:** `ACTIVE` (Verified via Final Activation Gate)
- **Router / Planner Visibility:** `VERIFIED_ROUTABLE`
- **Responsibilities:** Secret leakage scanning, prompt injection defense testing, permission matrix audits.
- **Forbidden Actions:** Disabling security gates, altering authentication policies.

### 11. SRE Agent (`agent-sre`)
- **Domain:** Reliability & Infrastructure Observability
- **Source File:** `src/Application/Agents/system_agents.py`
- **Contract:** `docs/architecture/agents/SRE_AGENT_CONTRACT.md`
- **Autonomy Level:** L3 (Policy-Bounded)
- **Lifecycle Status:** `ACTIVE` (Verified via Final Activation Gate)
- **Router / Planner Visibility:** `VERIFIED_ROUTABLE`
- **Responsibilities:** Latency percentiles (p50, p99), memory usage tracking, socket capacity monitoring.
- **Forbidden Actions:** Production cluster modifications without approval.

### 12. Executive Agent (`agent-executive`)
- **Domain:** Strategic Overview
- **Source File:** `src/Application/Agents/system_agents.py`
- **Contract:** `docs/architecture/agents/EXECUTIVE_AGENT_CONTRACT.md`
- **Autonomy Level:** L1 (Recommendation)
- **Lifecycle Status:** `ACTIVE` (Verified via Final Activation Gate)
- **Router / Planner Visibility:** `VERIFIED_ROUTABLE`
- **Responsibilities:** Aggregating cross-agent KPIs, tracking token costs, presenting executive overviews to human leadership.
- **Forbidden Actions:** Overriding lower-level safety controls, bypassing human governance.
