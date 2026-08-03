# TradeYar AI — Subscription Edge Cases & Error Recovery UX
*Document Reference: TY-REV-EDG-06*
*Category: UX Resilience & Exception Handling Specs*

---

## 1. Exception Handling Philosophy: No Dead Ends

TradeYar AI's subscription ecosystem must treat error conditions and transaction failures with the same precision as standard happy-path checkout journeys. No error page should ever present a blank screen, a raw JSON stack trace, or an unhelpful generic "An error occurred" message.

Every exceptional state must deliver three core components:
1. **Clear, Humanized Status Message:** Inform the user exactly what went wrong without using technical backend jargon.
2. **Actionable Next Action:** Present a single, high-contrast action button that resolves the bottleneck.
3. **Recovery Path/Fallback:** Provide alternative options (e.g., support chat, dashboard fallback, retry options) to keep the user inside the active workspace.

---

## 2. Granular Edge Case Scenarios & UX Solutions

---

### Scenario A: Failed Payment
- **Description:** User submits checkout but the bank/gateway declines the transaction (e.g., insufficient funds, fraudulent flag, general decline).
- **UX Flow:**
  - The payment loader halts, and the button reverts to its default clickable state.
  - An inline crimson alert box is displayed above the primary button: *"Transaction Declined: The card was declined by your bank. Please verify your funds, ensure international transactions are enabled, or try a different payment card."*
  - The form preserves all user data (name, email) to prevent frustrating re-entries.
- **Action Buttons:**
  - Primary Action: `[ Retry with Current Card ]`
  - Secondary Action: `[ Add Alternative Payment Method ]`

---

### Scenario B: Expired Card
- **Description:** A recurring subscription fails automatic billing because the linked card has crossed its expiration date.
- **UX Flow:**
  - Upon the first automated decline, the account is moved to `AWAITING_PAYMENT` state with standard workspace features remaining active during a 3-day grace period.
  - A persistent notification bar is pinned to the top of `/dashboard/*`: *"Action Required: Your subscription renewal is on hold because your credit card has expired. Please update your billing details within the next 48 hours to prevent any workspace interruptions."*
- **Action Buttons:**
  - Primary Action: `[ Update Credit Card Details ]`
  - Secondary Action: `[ Dismiss Notice ]`

---

### Scenario C: User Cancels Subscription
- **Description:** The user clicks "Cancel Subscription" in their billing settings center to prevent future automated billing.
- **UX Flow:**
  - **Retention Step:** Present a subtle survey modal showing why they are canceling (e.g. "Too expensive", "Missing features", "Difficulty using the system"). Offer a temporary 1-month 50% discount if they choose to pause instead.
  - If cancellation is confirmed, the account status updates to `CANCELLED_PENDING_EXPIRATION`.
  - The user **retains complete access** to their Professional features until the exact end of their current billing cycle (e.g., if canceled on day 15, access remains active for the remaining 15 days).
  - Clear text on status: *"Your subscription will end on 12 March 2027. You will not be billed again. Your historical patterns will remain archived."*
- **Action Buttons:**
  - Primary Action: `[ Revoke Cancellation (Resume Access) ]`

---

### Scenario D: User Returns After Expiration
- **Description:** An expired user returns to the platform after months of inactivity and wants to restore advanced capabilities.
- **UX Flow:**
  - Logged-in dashboard displays a clean "Welcome Back" greeting banner: *"It's great to see you again! Your historical backtests, shadow portfolio logs, and cognitive memories are safely preserved. Restore Professional Reasoning to pick up exactly where you left off."*
- **Action Buttons:**
  - Primary Action: `[ Reactivate Professional Tier ($19/mo) ]`
  - Secondary Action: `[ Browse Basic Free Terminal ]`

---

### Scenario E: Upgrade During Active Subscription (Pro-Rata)
- **Description:** An active Professional user ($19/mo) wants to immediately upgrade to Advanced Trader ($49/mo) on day 15 of their cycle.
- **UX Flow:**
  - The billing engine calculates the pro-rata credit: the user has consumed exactly $9.50 of value, leaving a credit of $9.50.
  - The checkout screen displays a clear, prorated calculation summary:
    - *New Tier Price:* $49.00 / month
    - *Active Professional Credit:* -$9.50
    - *Immediate Total Due:* **$39.50 USD**
    - *Subsequent Monthly Price:* $49.00 / month (starts in 30 days)
  - Upon checkout completion, all Advanced capabilities are activated instantly.
- **Action Buttons:**
  - Primary Action: `[ Confirm Pro-Rata Upgrade ]`

---

### Scenario F: Downgrade Before Renewal
- **Description:** An Advanced Trader user ($49/mo) wants to downgrade to Professional ($19/mo) mid-cycle.
- **UX Flow:**
  - To prevent complex refund configurations, the downgrade is schedule-delayed.
  - The user's advanced capabilities remain fully active for the remaining duration of their active billing cycle.
  - Visual notification: *"Downgrade Scheduled: Your account will transition to the Professional Tier on 12 March 2027. Your subsequent billing rate will be adjusted to $19.00 / month."*
  - Detail features that will be lost upon transition (e.g. "Active symbols ceiling will decrease from 20 to 15, and unlimited backtests will be capped to 50/month").
- **Action Buttons:**
  - Primary Action: `[ Confirm Downgrade Schedule ]`

---

### Scenario G: Duplicate Payment Attempt
- **Description:** The user clicks the "Complete Payment" button multiple times rapidly, or attempts concurrent checkout sessions in multiple browser tabs.
- **UX Flow:**
  - **Debounce Protection:** Upon the first click of the submit button, the button transitions immediately to disabled state with active spinner.
  - **Transaction Locks:** The server establishes a temporary, redis-backed or token-backed transactional lock on the specific payment session.
  - If a duplicate attempt is caught, the secondary screen redirects to checkout summary displaying a clear alert: *"Transaction in Progress: Your payment is already being processed on a secure channel. Please do not close this window or click refresh."*

---

### Scenario H: Network Failure During Checkout
- **Description:** The internet connection drops mid-transaction, leaving the user unaware of whether their payment was processed or if they have been charged.
- **UX Flow:**
  - The local client intercepts fetch errors and transitions the UI to a dedicated connection recovery card.
  - Display alert: *"Connection Interrupted: We lost communication with our billing servers. Do not submit payment again. We are validating your transaction state automatically."*
  - Background polling checks the user's local database record on `runtime_logs/auth.json` every 5 seconds. If the status updates to `PAID`, redirect directly to the success page.
  - If validation fails after 5 attempts, display a resolution CTA: *"Transaction pending validation. If you notice a charge on your statement, do not checkout again. Simply contact SRE workspace support with your transaction reference number."*
- **Action Buttons:**
  - Primary Action: `[ Validate Connection State ]`
  - Secondary Action: `[ Contact Workspace Support ]`
