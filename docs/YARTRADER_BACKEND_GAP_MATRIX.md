# YarTrader AI — Backend Gap Matrix

This document maps all missing, partial, or broken backend capabilities of the YarTrader AI platform. Every item is prioritized according to its production impact, coupled with exact implementation paths, required engineering work, dependencies, complexity, and blocking status.

---

## 1. P0 — Critical (Production Blockers)

These gaps represent critical security vulnerabilities, auth loop gaps, data integrity flaws, or system failures that absolutely block production.

| Capability | Current Status | Priority | Evidence | Required Work | Dependencies | Complexity | Blocking? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Social Sign-In Validation** | `🟢 REMEDIATED` | **P0** | `src/Application/Services/web_dashboard.py` (Endpoints `/api/auth/google`, `/api/auth/apple`), `src/Application/Dashboard/oidc_validator.py` | Replaced mock credentials with real OIDC verification of signed Google and Apple ID tokens, validating signatures against official JWKS keys, issuer, audience, and expiration. | JWT cryptography, Social Provider Developer accounts | Medium | **No** |
| **Database Credentials Integrity** | `🟢 REMEDIATED` | **P0** | `src/Infrastructure/Configuration/settings.py`, `src/Application/Dashboard/auth_repo.py` | Enforced complete environment extraction of all database paths and default passwords. Disabled weak fallback credential hashes completely in production mode and fail closed. | Secret Management / Environment config | Low | **No** |
| **Admin Lockout Audit Trail** | `🟢 REMEDIATED` | **P0** | `src/Application/Dashboard/auth_service.py` | Created a persistent, append-only, tamper-resistant administrative log table tracking failed logins, IP addresses, user agents, and progressive penalty events to prevent brute-force memory evasion. | AuthService, File/SQLite DB | Low | **No** |

---

## 2. P1 — Required Before Production

Important capabilities required to complete a professional, usable SaaS platform before launch.

| Capability | Current Status | Priority | Evidence | Required Work | Dependencies | Complexity | Blocking? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Subscription Tier Gating** | `🟡 PARTIAL` | **P1** | `src/Growth/Agents/SecurityCostAgents.py` (`TierEntitlementMiddleware`) | Integrate `TierEntitlementMiddleware` as an active FastAPI Router dependency across `/api/user/*` endpoints to enforce symbol limits, timeframe horizons, and features per user tier. | FastAPI router, AuthService | Medium | **Yes** |
| **Password Reset Verification** | `🟡 PARTIAL` | **P1** | `/api/auth/forgot-password` in `web_dashboard.py` | Implement cryptographically secure token generation with an expiration TTL, persist tokens securely, and configure actual SMTP transport (e.g. Amazon SES) to deliver emails. | SMTP Service | Medium | **Yes** |
| **Email Verification Loop** | `🔴 MISSING` | **P1** | No backend code | Add an email confirmation state to the user schema. Generate registration tokens, email them on signup, and restrict login until the email is verified. | SMTP Service, AuthRepository | Medium | **Yes** |
| **Backup and Restore Automation** | `🟡 PARTIAL` | **P1** | `docs/BACKUP_RECOVERY_PLAN.md` | Create automated cron scripts to take scheduled snapshots of the `runtime_logs/` JSON databases and write a script to restore them to verify backup integrity. | Operating System Cron, Storage | Medium | **Yes** |

---

## 3. P2 — Important (Post-Production)

Capabilities that should be completed shortly after launch to optimize platform operations, tracking, and customer experience.

| Capability | Current Status | Priority | Evidence | Required Work | Dependencies | Complexity | Blocking? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Double-Entry Financial Ledger** | `🔴 MISSING` | **P2** | No backend ledger files | Introduce relational database tables (e.g., SQLite/PostgreSQL) with strict constraints (credit, debit, transaction hashes) to track virtual balance adjustments immutably. | Database Engine | High | **No** |
| **SaaS Billing and Invoicing** | `🔴 MISSING` | **P2** | No billing files | Integrate Stripe or cryptocurrency payment gateways to handle real plan purchases, invoices, upgrades, downgrades, and billing renewals. | Payment Gateway API | High | **No** |
| **Support Ticketing System** | `🔴 MISSING` | **P2** | No ticketing files | Implement standard Support Ticket tables (ID, user, category, status, priority, responses array) to process customer requests from the frontend panel. | Database Engine | Medium | **No** |
| **Login Device Tracking** | `🔴 MISSING` | **P2** | `src/Application/Dashboard/auth_service.py` | Parse User-Agent headers on authentication to register active logged-in devices and display them in the user profile settings dashboard. | AuthService, UA-Parser | Low | **No** |
| **Revenue Business Analytics** | `🔴 MISSING` | **P2** | No revenue tracking files | Calculate and cache real MRR, ARR, active user churn, and customer lifetime values (LTV) from real billing logs to render business panels. | Stripe API, Database | Medium | **No** |

---

## 4. P3 — Enhancements

Minor optimizations or decorative features that can safely wait.

| Capability | Current Status | Priority | Evidence | Required Work | Dependencies | Complexity | Blocking? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Telegram OAuth Integration** | `🟡 PARTIAL` | **P3** | Simulated login only | Implement the official Telegram login widget handshake and hash validation algorithm in the backend. | Telegram API | Low | **No** |
| **Granular Admin Permissions** | `🔴 MISSING` | **P3** | Binary ADMIN role check only | Transition from binary ADMIN/USER roles to a granular RBAC schema supporting permission groups (e.g., SRE, Billing Analyst, Risk officer). | AuthService | Medium | **No** |
| **2FA Authentication** | `🔴 MISSING` | **P3** | No TOTP code | Implement Time-based One-time Password (TOTP) standards utilizing Google Authenticator algorithms for admin logins. | PyOTP library | Medium | **No** |
| **Data Export (GDPR Compliance)** | `🔴 MISSING` | **P3** | No export endpoints | Generate a compiled JSON package containing a user's profile, signal views, and shadow trade history upon self-service request. | AuthRepository, Zipfile | Low | **No** |
