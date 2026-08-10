# YARTRADER — COMPREHENSIVE PRODUCT ROADMAP (PHASE 0 & PHASE 1)

## OVERVIEW
The YarTrader product direction is locked against unvalidated or decorative engineering. This Roadmap specifies exactly what needs to be built across six logical phases to transition YarTrader from a robust algorithmic simulation suite into a professional, commercially viable, and high-trust user-facing SaaS platform.

---

## PHASE 0 — Product Foundation
Ensure absolute integrity of the existing infrastructure, security models, and system resource boundaries.

* **Objective:** Establish a rock-solid, crash-free operational system base.
* **User Outcome:** Users enjoy deterministic workspace allocations and consistent system responses.
* **Required Backend Capability:**
  * Resolve the 30/50 symbol discrepancy by synchronizing the `SymbolRegistry` limit, the Admin API, and `system_limits.yaml` to an authoritative maximum ceiling of `30` symbols.
  * Implement standard, queryable, append-only security logs recording administrative logins, failed password attempts, and system configuration overrides.
* **Required Frontend Capability:**
  * Cleanly restrict symbol management and SRE validation controls from ordinary customer routes, isolating them entirely inside the **SRE Admin Control Console** (`#/admin`).
* **Evidence Required:**
  * Comprehensive test suite passes with 100% success rate.
  * Database file `runtime_logs/symbols_registry.json` contains exactly synchronized ceiling metrics matching `system_limits.yaml`.
* **Acceptance Criteria:**
  * Registering symbols beyond `30` is blocked at the gateway level with an explicit `HTTP 400 Bad Request`.
  * Attempting to access SRE validation loops or logs as a standard user triggers `HTTP 403 Forbidden`.

---

## PHASE 1 — Vercel Site Availability (COMPLETE)
Make the complete existing YarTrader website accessible and functional from the production Vercel URL.

* **Objective:** Ensure absolute web routing integrity, smooth asset deliveries, and seamless production API proxy routing.
* **User Outcome:** Users successfully access, load, refresh, and utilize all public and authenticated pages of YarTrader.
* **Required Backend Capability:**
  * Support secure CORS headers and dynamic reverse proxy rewrites from Vercel edge to production API servers (`tradeyar.ai`).
* **Required Frontend Capability:**
  * Robust same-origin dynamic base API selection to automatically self-heal against proxy configurations.
  * Complete routing layout using hash-based window change hooks in `App.jsx`.
* **Evidence Required:**
  * Deployed SPA at `https://yartrader.vercel.app/` passes all direct open, refresh, asset loading, and auth gate audits (100% PASS).
  * `vercel.json` rewrite configuration verified.
* **Acceptance Criteria:**
  * Entering any existing route directly from browser URL bar loads the correct view.
  * No localhost references or uncaught exceptions remain in the frontend builds.

---

## PHASE 2 — Core User Value & Gated Horizons
Bridge the gap between raw statistical signals and an authentic, high-trust consumer terminal.

* **Objective:** Deliver verified chronological price-action insights directly to logged-in users.
* **User Outcome:** Customers receive secure, real-time trading setups with explicit multi-timeframe confirmations.
* **Required Backend Capability:**
  * Mount the pre-existing `TierEntitlementMiddleware` as an active FastAPI dependency on all user endpoints, verifying workspace limitations against current user subscription statuses.
  * Integrate SMTP mailers with verification token generation to require email validation on all new registrations before granting access to user panels.
* **Required Frontend Capability:**
  * Render an "Unverified Account" lock screen for registered users who have not completed email verification.
  * Display explicit workspace limit statuses (e.g. "Active Symbols: 3/10 used") depending on the active subscription tier.
* **Evidence Required:**
  * Production mock SMTP logs show generated email templates with secure, hashed verification links.
* **Acceptance Criteria:**
  * Unverified registrations fail-closed upon login.
  * Active tier boundaries (symbol counts, timeframe horizons) are strictly enforced at the API layer.

---

## PHASE 3 — Evidence & Trust
Establish unmatched credibility and regulatory transparency for the trading intelligence core.

* **Objective:** Replace statically rendered benchmark examples with historical, dynamically updated, and audited performance evidence.
* **User Outcome:** Users evaluate platform performance with maximum trust, backed by a real mathematical track record.
* **Required Backend Capability:**
  * Create a public-facing dynamic performance API summarizing past shadow trades directly from `pattern_outcomes.json`.
  * Compute daily rolling win rates, profit factors, drawdown histories, and average risk/reward achievements.
* **Required Frontend Capability:**
  * Overhaul the dashboard to display dynamic statistical matrices connected to the backend performance API.
  * Retain the required `APES-FIN` compliance disclaimers beneath all visual stats boards.
* **Evidence Required:**
  * Real-time calculation of win rate matches active database outcomes exactly.
* **Acceptance Criteria:**
  * The terminal metrics dynamically update upon new shadow trade closes.
  * Users can search, filter, and inspect detailed historical shadow trades and pattern outcomes.

---

## PHASE 4 — Monetization
Activate physical, self-service payment flows and financial integrity layers.

* **Objective:** Enable frictionless, self-service commercialization of the product catalog.
* **User Outcome:** Users seamlessly purchase subscriptions and add-on products with immediate provisioning of benefits.
* **Required Backend Capability:**
  * Integrate Stripe payment gateway checkout sessions and sandbox webhook listeners.
  * Deploy a double-entry financial ledger schema tracking transactions in integer micro-units (cents) to prevent double-spending or unauthorized balance manipulation.
  * Wire user roles to update dynamically on Stripe renewal/cancel webhooks.
* **Required Frontend Capability:**
  * Connect plan CTA buttons to initialize Stripe Checkout sessions on click.
  * Render an immutable billing history/invoicing drawer in user settings.
* **Evidence Required:**
  * Double-entry balancing balance check: `total debits == total credits` across all user ledger tables.
* **Acceptance Criteria:**
  * Completing a Stripe payment instantly upgrades user workspace entitlements.
  * Failed checkouts or chargebacks fail-closed, reverting the profile to the free tier immediately.

---

## PHASE 5 — Growth
Incentivize active community acquisition and distribution loops.

* **Objective:** Scale organic user acquisition through automated newsletters, referrals, and localized social channels.
* **User Outcome:** Active traders earn platform credits and interactive credits by referring new members.
* **Required Backend Capability:**
  * Deploy the `DistributionAgents.py` and `TrustLearningAgents.py` growth agents to automate newsletter dispatches.
  * Formulate referral codes linked to the double-entry financial ledger.
* **Required Frontend Capability:**
  * Integrate an interactive "Refer a Friend" panel showing available credits.
  * Add self-service GDPR export options allowing users to zip and download their personal trade journals and settings.
* **Evidence Required:**
  * Generation of download package zips containing verified user profiles and signal history.
* **Acceptance Criteria:**
  * Referred signups credit the referrer with $10 in virtual credits atomically inside the ledger.
  * GDPR export requests deliver complete JSON archives securely via email or instant download.

---

## PHASE 6 — Future Products
Expand commercial offerings into elite B2B enterprise services and customized prop assistants.

* **Objective:** Secure long-term institutional enterprise contracts.
* **User Outcome:** Institutional clients leverage custom white-labeled cognitive servers or private cloud APIs.
* **Required Backend Capability:**
  * Support OAuth2 token exchange flows (Authlib) for custom API integrations.
  * Develop Prop Challenge compliance managers to monitor real-time daily drawdown limits and trading rule adherence.
* **Required Frontend Capability:**
  * Construct dedicated Prop Challenge dashboard cards showing active metric compliance progress.
* **Evidence Required:**
  * SRE server health monitoring logs show isolated container structures for white-labeled instances.
* **Acceptance Criteria:**
  * API requests with valid developer tokens are authenticated, metered, and restricted according to rate limits.
