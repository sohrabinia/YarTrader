# TradeYar AI — Subscription Experience Audit & Lifecycle Architecture
*Document Reference: TY-REV-AUD-01*
*Category: Revenue Operations & UX System Architecture*

---

## 1. Executive Summary

As TradeYar AI transitions to a comprehensive **Autonomous Market Intelligence Platform**, our subscription mechanics must evolve from a basic "payment-for-signals page" to a robust, enterprise-grade **Subscription Lifecycle Experience**.

This audit assesses the current state of our workspace subscription modules, highlights existing gaps across the user journey, and outlines the recommended multi-phase revenue architecture. All recommendations comply strictly with the **APES-FIN** non-trading guidelines, prioritizing education, simulated performance, and risk management over active transactional billing of live executions.

---

## 2. Current State Analysis

Based on our system reality report, existing JSON schema definitions, and frontend specification package, the following is a detailed audit of our current subscription modules:

### A. Existing Pricing Components
- **Current Visual Structure:** Basic pricing tables are defined in static locales (`locales/en.json`) representing three pricing tiers: *Basic Researcher ($0)*, *Professional Tier ($79)*, and *Institutional Tier ($299)*.
- **Limitation:** The visual structure lacks plan transition flows, clear upgrade paths, comparison matrices, and visual callouts for our brand-new intelligence-focused model (e.g. *Explorer ($5)*, *Professional ($19)*, *Advanced Trader ($49)*, *Professional Desk ($199)*, and *Enterprise (Custom)*).

### B. Existing Authentication Flow
- **Current Security Implementation:** Secure login, signup, and password recovery endpoints are mounted inside `src/Application/Services/web_dashboard.py` and routed through `/api/auth/*`. Hashes are verified via standard PBKDF2 (100k iterations) against `runtime_logs/auth.json`.
- **Limitation:** There is no "subscription intent" state integration. Users who select a paid tier on the landing page are redirected to a blank signup page without preserving their selected plan configuration, resulting in potential checkout abandonment.

### C. Existing User Profile/Subscription Pages
- **Current UI View:** Standard user dashboards reside under `/dashboard/*` but lack a dedicated, high-fidelity billing subscription center (`/account/subscription`) where users can monitor usage limits, view historical invoices, or manage active renewals.
- **Limitation:** The profile contains raw name and email fields but lacks active subscription tier statuses, current period end-dates, and usage-to-capacity metrics.

### D. Existing Payment Integration Points
- **Current Endpoint Mapping:** The system lists a simulated cryptocurrency gateway in `PaymentService` but lacks structured webhooks or API parameters to handle failed web checkout states, active subscription renewals, card updates, or downgrades.
- **Limitation:** No standard webhook event handler exists to transition a user account status automatically from pending-payment to active-paid states upon gateway confirmation.

### E. Existing API Contracts
- **Available Resources:** Endpoints like `GET /api/v1/demo/account` track simulated metrics such as balance, equity, and margin, and `GET /v1/dashboard/cognitive` maps learning stats.
- **Limitation:** There are no active REST APIs for mapping billing records, retrieving usage quotas (e.g., chatbot queries remaining, backtest runs used, active monitored symbols), or requesting an immediate mid-cycle upgrade pro-rata calculation.

### F. Gaps in Missing Lifecycle States
The existing setup completely lacks the following critical lifecycle transitions:
1. **The Intent State:** No mechanism to carry forward selected subscription parameters through the registration form.
2. **The Usage Warning Threshold State:** No notification banners to alert users when they approach 70%, 90%, or 100% of their analytical limits.
3. **The Grace Period State:** No automatic retry or billing retry attempts if a subscription renewal fails.
4. **The Safe Downgrade (Soft Expiration) State:** Expiration causes immediate lockouts rather than a graceful fallback to a read-only basic platform.

---

## 3. Recommended Revenue Lifecycle Architecture

We recommend deploying a thread-safe, modular subscription lifecycle state machine. This architecture tracks and manages the user's progress through exactly nine distinct stages:

```
[ 1. User Discovery (Pricing Page) ]
                |
                v
[ 2. Plan Selection & Intent Capture ]
                |
                v
[ 3. Secure Unified Authentication ]
                |
                v
[ 4. Payment processing & Security Gateway ] <---+ (Failed Payment Retry)
                |                                 |
                v                                 |
[ 5. Subscription Activation (Instant Workspace) ]-+
                |
                v
[ 6. Workspace Access & Usage Intelligence ]
                |
                v
[ 7. Usage Capacity & Renewal Notifications ]
                |
                v
[ 8. Renewal Processing / Pro-Rata Upgrades ]
                |
                v
[ 9. Expiration (Safe Read-Only Downgrade) / Reactivation ]
```

---

## 4. Architectural State Machine Matrix

The following state matrix details how each transition is governed, which database entries are affected in our persistent configuration store (`runtime_logs/auth.json`), and the corresponding client-side UX behavior:

| Lifecycle State | DB/User Status Flag | Triggers / Requirements | Expected Client-Side UX |
| :--- | :--- | :--- | :--- |
| **GUEST_VISITOR** | `role: "GUEST"`, `tier: "FREE"` | Landing on public shell. | General pricing page access, active markets view, sitemap browsing. |
| **PLAN_INTENT** | `selected_tier: "PROF_19"` | Clicking CTA on Plan Card. | Temporary routing state; stores plan ID in local storage; redirects to sign up. |
| **PENDING_CHECKOUT** | `tier: "FREE"`, `billing_status: "AWAITING_PAYMENT"` | Submitting signup form with active intent. | Redirects to `/checkout` displaying selected plan summary, price, and payment methods. |
| **ACTIVE_SUBSCRIBER** | `tier: "PROFESSIONAL"`, `billing_status: "PAID"` | Gateway webhook dispatches positive signal. | Slide-in success animation; redirects to `/dashboard` with advanced analysis active. |
| **USAGE_WARNING** | `tier: "PROFESSIONAL"`, `usage_pct: >= 70%` | Cron job checks active usage counts. | Subtle informational toast notification in dashboard panel header. |
| **CAPACITY_CRITICAL** | `tier: "PROFESSIONAL"`, `usage_pct: >= 90%` | Usage triggers close-to-ceiling events. | Yellow warning bar with upgrade prompt; highlights value of next tier. |
| **LIMIT_REACHED** | `tier: "PROFESSIONAL"`, `usage_pct: 100%` | Quota exhausted. | Feature-lock overlays on advanced modules; CTA pointing to checkout upgrade. |
| **RENEWAL_ALERT** | `renewal_countdown: <= 14 days` | Daily database check on subscription end-date. | Dynamic badge in Account Settings displaying renewal date and next payment price. |
| **SOFT_EXPIRATION** | `tier: "FREE"`, `billing_status: "EXPIRED"` | Grace period ends without positive renewal signal. | Lock overlays on Shadow Trading and Backtesting; unlocks "Restore Capabilities" checkout CTA. |

---

## 5. Next Steps for Implementation

To prepare for Phase 2 implementation, the following directories and files must be established to detail our complete UX, notification text library, component specs, and error boundaries:
- `docs/SUBSCRIPTION/SUBSCRIPTION_USER_FLOW.md`
- `docs/SUBSCRIPTION/PRICING_EXPERIENCE.md`
- `docs/SUBSCRIPTION/LIFECYCLE_NOTIFICATIONS.md`
- `docs/SUBSCRIPTION/COMPONENT_REQUIREMENTS.md`
- `docs/SUBSCRIPTION/EDGE_CASES.md`

All files must adhere strictly to the color, spacing, typography, and shadow system guidelines outlined in our v1.0 design engineering packages.
