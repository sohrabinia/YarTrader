# TradeYar AI — User Subscription Flow & Journey Map
*Document Reference: TY-REV-FLOW-02*
*Category: User Experience Design & Flow Mapping*

---

## 1. Complete Subscription Journey Diagram

Below is the complete customer lifecycle from a user's very first visit to the platform, through plan selection, secure payment processing, active analytical usage, warning thresholds, automatic renewal, and reactivation:

```
[ Visitor arrives on landing page ]
               |
               v
  [ Browses Pricing Comparison ]
               |
               v
   [ Clicks "Select Plan" CTA ] ---> (Captures select_plan in session)
               |
               v
  [ Unified Registration / Login ] <--- (Carries select_plan intent)
               |
               v
    [ Secure Checkout Summary ] <----+ (Failed payment redirects here)
               |                     |
               v                     |
      [ Payment Processing ] --------+ (If payment fails, display recovery UI)
               |
               +-----------------------------------+
               | (If payment succeeds)             |
               v                                   v
  [ Instant Account Activation ]         [ SRE Subsystem Updates ]
  - Writes tier to auth.json             - Rotates session logs
  - Displays Success Page                - Grants workspace bandwidth
               |
               v
 [ Enter Terminal / Active Usage ]
  - Monitors 8-timeframe grid
  - Performs similarity matches
  - Runs backtests & shadow trades
               |
               +------------+------------+
               |            |            |
               v            v            v
           [ Normal ]    [ Warn ]    [ Exceed ]
             (<70%)     (70%-90%)     (100%)
               |            |            |
               |            |            v
               |            |    [ Feature Lock Overlay ]
               |            |    - Backtesting disabled
               |            |    - Shadow trading frozen
               |            |    - Upgrade checkout prompt
               |            |            |
               +------------+------------+
                            |
                            v
                [ Subscription Renewal ]
                 - 14, 7, 1-day alerts
                 - Dispatch invoice PDF
                            |
                 +----------+----------+
                 |                     |
                 v (Renew Success)     v (Renew Fail / Cancel)
         [ Cycle Restarts ]     [ Grace Period (3 Days) ]
                                       |
                                       v
                                [ Downgrade State ]
                                - Active tier -> FREE
                                - Soft overlay locked modules
                                - Unlocks Reactivation CTA
```

---

## 2. Granular Step-by-Step Flow Specifications

---

### Step A: Discovery and Intent Capture (Pricing UI)
1. **Action:** The user visits `/pricing` or clicks "View Pricing" from the landing page.
2. **Interface Response:** The platform renders the 5-tier comparison grid (Free, Explorer, Professional, Advanced Trader, Professional Desk) highlighting "Maturity Levels" instead of raw limits.
3. **Trigger:** The user clicks `[ Select Professional ]` ($19/month).
4. **Local State Capture:** The client-side state store (`useTerminalStore`) captures `session_intent = { plan_id: "PROF_19", name: "Professional", price: 19.00 }` inside local browser storage.
5. **Redirection:** The user is dynamically routed to `/api/auth/register` or the visual signup shell.

---

### Step B: Unified Registration with Intent Retention
1. **Action:** The registration screen detects `session_intent` inside local storage.
2. **Interface Response:** The header updates dynamically:
   - *Message:* `"Register your credentials to initialize your Professional Intelligence Workspace ($19/mo)"`
3. **Form Submission:** The user enters name, email, password, and signs the APES-FIN passive-advisory compliance checkbox.
4. **Database Record Creation:** The server processes credentials using PBKDF2, writes the record to `runtime_logs/auth.json` with status `tier: "FREE"`, `selected_plan: "PROF_19"`, `billing_status: "AWAITING_PAYMENT"`.
5. **Redirection:** The client routes the user immediately to `/checkout`.

---

### Step C: Secure Checkout Experience
1. **Screen Location:** `/checkout`
2. **Interface Response:** Renders the `CheckoutSummary` component displaying:
   - Selected Plan: **Professional — $19.00 / month**
   - Subtotal: **$19.00** | Tax/Surcharge: **$0.00** | Total Due: **$19.00 USD**
   - Security Reassurance Banner: *"Fully encrypted SSL transmission. No credit card data is retained on our SRE servers."*
3. **User Action:** The user inputs payment details and clicks `[ Complete Payment Validation ]`.
4. **Processing State:** Button changes to a pulsing progress spinner: `[ Verifying Cryptographic Ledger... ]`. Standard UI elements are disabled to prevent double-payment submissions.

---

### Step D: Payment Confirmation & Workspace Activation
1. **Background Action:** The payment gateway returns a validated transaction signal.
2. **Backend Execution:** The `PaymentService` automatically updates `runtime_logs/auth.json`:
   - `tier` -> `"PROFESSIONAL"`
   - `billing_status` -> `"PAID"`
   - `period_start` -> `current_date`
   - `period_end` -> `current_date + 30 days`
   - Resets usage limits: `backtests_remaining: 50`, `symbols_allowed: 15`.
3. **Client-side Notification:** WebSocket fires event `subscription_activated` to the open client session.
4. **Redirection:** The page transitions immediately to `/checkout/success` with a dark, high-vibe glowing dashboard introduction.

---

### Step E: Instant Success Landing Page
1. **Screen Location:** `/checkout/success`
2. **Interface Response:** Display a clean neon status check:
   - *Title:* `"Your Intelligence Workspace is Active."*
   - *Active Plan:* **Professional Tier ($19 / month)**
   - *Next Billing Date:* **[Current Date + 30 Days]**
   - *Primary CTA:* `[ Open Multi-Timeframe Signal Grid ]`
   - *Secondary CTA:* `[ Tour the Cognitive Assistant ]`

---

### Step F: Active Usage & Limit Threshold Monitoring
1. **Active State:** The user works inside `/dashboard/*`.
2. **Client Loop:** In the background, `useTerminalStore` queries `GET /api/v1/demo/account` and custom usage endpoints.
3. **Capacity Thresholds:**
   - **70% Capacity:** Display a gentle informational toast alert: *"Workspace usage notice: You have completed 35 out of 50 allocated backtest cycles for this billing period."*
   - **90% Capacity:** Highlight a golden caution header banner inside the terminal: *"Warning: Workspace approaching ceiling limits. Upgrading to Advanced Trader unlocks unrestricted backtests and multi-asset correlation analytics."*
   - **100% Capacity:** Replace the Backtest and Shadow panels with an elegant blur filter and render a crisp `FeatureLock` overlay card containing a secure, 1-click checkout upgrade option.

---

### Step G: Subscription Expiration & Safe Downgrade
1. **Background Action:** The billing period ends, and automatic payment renewal fails twice.
2. **Grace Period:** The account enters a 3-day grace period with warning alerts active: *"Renewal failed. We will retry in 24 hours. Keep your workspace access uninterrupted."*
3. **Downgrade Execution:** If retry attempts fail, the server updates `auth.json`:
   - `tier` -> `"FREE"`
   - `billing_status` -> `"EXPIRED"`
4. **Client-side Response:** The next login redirects to `/dashboard` with a safe downgrade message:
   - *Banner:* `"Your Professional Intelligence access has expired. Your historical logs remain safely archived. Upgrade anytime to restore Advanced Reasoning, Backtesting, and simulated Shadow Trading."*
   - Locked modules are replaced with passive read-only previews. Standard market observation features remain active, preventing a broken or crash-vulnerable UX.
