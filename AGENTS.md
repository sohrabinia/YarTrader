# YarTrader Repository Agent Directives & Documentation Governance

This document establishes canonical operating instructions, safety invariants, and repository-level documentation governance for all AI agents (including Jules) and software engineering contributors working on `sohrabinia/YarTrader`.

---

## 1. MANDATORY DOCUMENTATION IMPACT REVIEW

**Permanent Repository Engineering Rule:**

> **Every PR and every code change MUST review documentation impact and update the relevant documentation whenever the change affects documented system behavior, architecture, security, APIs, configuration, deployment, data model, operations, or other recorded system decisions.**

Documentation review is an indispensable part of the Definition of Done. A PR or task is **incomplete** if code works and tests pass but a required documentation update was omitted.

---

## 2. JULES EXECUTION RULE

Every AI agent (Jules) task MUST execute a **Documentation Impact Review** before implementation is considered complete.

Jules must:
1. Inspect relevant repository documentation prior to completing work.
2. Determine whether system contracts, architecture, security, or behaviors were altered.
3. Update affected documentation in the same PR/branch when required.
4. Include the Documentation Impact Review declaration in every completion report.

---

## 3. MANDATORY IMPACT AREAS CHECKLIST

Every change must explicitly evaluate potential impact across these areas:

* **Architecture**: Components, services, boundaries, dependencies, data flow, authentication flow, internal service boundaries.
* **API**: Endpoints, request/response schemas, authentication requirements, status codes, public behavior, internal API contracts.
* **Authentication / Security**: Authentication methods, authorization rules, sessions, tokens, identity providers, security boundaries, secrets/configuration behavior, security invariants.
* **Data**: Database schemas, persistence formats, user identity, account ownership, data lifecycle, migrations.
* **Deployment / Operations**: Production runtime, Windows service hosting, IIS/ARR reverse proxy, environment variables, build processes, deployment scripts, runtime configuration, health checks.
* **Trading Safety**: Risk Engine, MT5/MT4 adapters, execution safety gates, daily loss kill switch, position/account isolation. *(Note: Do NOT modify Trading Core solely to satisfy documentation requirements).*
* **Testing**: Behavioral changes, security invariant changes, contract changes, deployment test requirements.
* **Product / User Behavior**: User-facing UI, localized strings, navigation routes, subscriber workflows.

---

## 4. REQUIRED PR DECLARATION

Every Pull Request description and final completion report MUST contain the following section:

```markdown
## Documentation Impact Review

- Documentation reviewed: YES
- Documentation updated: YES / NO
- Impact areas:
  - Architecture: YES / NO
  - API: YES / NO
  - Authentication/Security: YES / NO
  - Data: YES / NO
  - Deployment/Operations: YES / NO
  - Trading Safety: YES / NO
  - Testing: YES / NO
  - User-visible behavior: YES / NO

If documentation was not updated:
- Reason: <State concise, valid reason e.g. "No documented behavior, contract, or architecture changed.">
```

---

## 5. WHEN DOCUMENTATION UPDATE IS REQUIRED VS NOT REQUIRED

### Documentation Update REQUIRED
* **Authentication**: Changes to Google OIDC, session handling, password management, authorization guards, or token validation.
* **API Contracts**: New, modified, or removed endpoints, parameter schema updates, response code changes.
* **Deployment**: Changes to runtime configuration, environment variables, build steps, or Windows host scripts.
* **Architecture**: Changes to service boundaries, proxy rules, or inter-service contracts (e.g. YarOperator integration).
* **Security & ADRs**: Changes to security invariants or introduction of major architectural decisions.

### Documentation Update NOT REQUIRED (No Churn Policy)
* Typo corrections in internal code comments or variable names.
* Internal variable renames with provably zero external behavioral impact.
* Formatting, linting, or whitespace-only code changes.
* Adding new test cases that verify already-documented behavior.

When no update is required, the PR declaration must state:
`Documentation reviewed: YES`
`Documentation updated: NO`
`Reason: No documented behavior or contract changed.`

---

## 6. DOCUMENTATION ACCURACY & REALITY RULE

Documentation MUST accurately reflect real execution state at all times. Never claim:
* Implemented when only planned.
* Merged when only residing on a feature branch.
* Deployed when only verified in local development/sandbox.
* Production-verified when only verified via unit tests.

Documentation must explicitly distinguish between:
* `Implemented`
* `Staged locally`
* `Committed`
* `Merged`
* `Deployed`
* `Production verified`

---

## 7. PROVENANCE & HISTORICAL RECORDS

### Record Provenance
For system and security records, always document:
* Repository, Branch, Commit SHA, Date, Affected Files, Decision Rationale, Verification Evidence.
* **Zero Credential Exposure**: Never document raw passwords, client secrets, private keys, JWTs, or access tokens.

### Preserving Historical Forensic Records
Historical forensic reports (such as `docs/YARTRADER_CUSTOMER_AUTH_FORENSIC_RECORD.md`, `docs/YARTRADER_FINAL_FORENSIC_AUDIT_PR235.md`, etc.) are immutable historical audit records. Do NOT rewrite or delete historical forensic documents. Future changes must update active documentation or create new Architecture Decision Records (ADRs).

---

## 8. ARCHITECTURE DECISION RECORDS (ADRs)

For major architectural, design, or security decisions, create an ADR in:
`docs/decisions/ADR-NNN-<short-name>.md`

An ADR must contain:
1. Status (Proposed / Accepted / Superseded)
2. Date
3. Context
4. Decision
5. Security & Operational Implications
6. Alternatives Considered
7. Consequences

---

## 9. DEFINITION OF DONE — DOCUMENTATION CHECKLIST

- [ ] Relevant documentation inspected prior to code modification.
- [ ] Documentation Impact Review completed across all 8 impact areas.
- [ ] Architecture, API, Security, Data, Deployment, Safety, Testing, and Product impacts assessed.
- [ ] Required documentation updated in the same PR/branch.
- [ ] No unnecessary documentation churn for internal/trivial changes.
- [ ] Zero secrets, raw keys, or credentials documented.
- [ ] Execution state explicitly distinguished (Implemented / Staged / Committed / Merged / Deployed / Verified).
- [ ] Historical forensic records preserved intact.

---

## 10. PROTECTED TRADING CORE SAFETY INVARIANTS

* **Hard-Locked Demo Execution**: `LIVE_TRADING_ENABLED = False` is hard-locked across all adapters, gates, and workers. Real accounts (`is_real == True`) trigger immediate fail-closed rejection.
* **Daily 8% Loss Protection Kill-Switch**: Captures immutable account equity baseline at `01:35 Iran local time`.
* **Account Equity Fail-Closed Policy**: Position sizing strictly requires non-zero, non-NaN authoritative account equity.
* **Zero Mock Financial Facts in Production Paths**: Production execution paths strictly require real broker adapter facts.
