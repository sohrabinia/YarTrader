# TradeYar AI — UX Component Mapping Specifications
*Document Reference: TY-UX-CMP-MAP-02*
*Category: UI Component Inventory & State Mappings*

---

## 1. Introduction

This document registers and maps the ten core subscription and lifecycle UI components to their exact locations, interactive behaviors, layout styles, and localization keys. All designs are strictly aligned with the dark-themed, gold-accented tokens of our Frontend Design Package v1.0.

---

## 2. Components Inventory Map

---

### 1. `PricingCard`
- **Purpose:** Renders a subscription plan card.
- **Location:** Mounted inside `#pricing-plans-container` on `/pricing` view.
- **Styles:** Glassmorphic card background (`#15181C`), gold top border for featured/recommended tiers, and crisp typography for pricing.
- **Interactive States:**
  - *Hover:* Scales card by 1.02x with gold shadow glow.
  - *Click:* Launches the selected registration/checkout flow.
- **Localization Integration:** Linked to plan identities like *Research Access*, *Daily Intelligence*, *Professional Reasoning*, *Advanced Intelligence*, and *Institutional Intelligence*.

---

### 2. `PlanComparison`
- **Purpose:** Renders a detailed grid comparing plan features and technical limits.
- **Location:** Expandable panel below pricing cards.
- **Styles:** High-contrast alternating table rows with clear, sharp checkmarks (`#10B981`) or crosses (`#EF4444`).
- **Interactive States:** Fully collapsible and supports RTL layouts dynamically when language is toggled to Persian or Arabic.

---

### 3. `CheckoutSummary`
- **Purpose:** Summarizes the selected subscription subtotal, discount codes, tax ($0.00), and final due price.
- **Location:** Mounted on `/checkout` view.
- **Styles:** Compact bounding border with an SRE secure SSL transaction lock icon.
- **Interactive States:** Disables checkout button and renders a pulsing loading spinner during transaction validation.

---

### 4. `SubscriptionStatusCard`
- **Purpose:** Displays the active subscription tier and upcoming billing renewal date.
- **Location:** Main status panel in `/account/subscription`.
- **Styles:** Features a pulsing green status dot (`● ACTIVE`) and elevated typography.
- **Interactive States:** Contains clear button links for "Modify Payment Card" and "Cancel Subscription".

---

### 5. `UsageMeter`
- **Purpose:** Tracks active consumption of symbols, backtests, and chatbot queries against plan ceilings.
- **Location:** Grid component under `/account/subscription`.
- **Styles:** Horizontal progress bar. Indicator color turns yellow at 90%, and flashes red at 100% (limit reached).
- **Interactive States:** Displays a hover tool-tip with the exact numerical fraction (e.g. `12 / 50 backtests completed`).

---

### 6. `UpgradeRecommendation`
- **Purpose:** Displays high-conversion, contextual upgrade prompts when capacity limits are approached.
- **Location:** Dynamic card below `UsageMeter` panels.
- **Styles:** Highlighted with a dotted golden border and gold-accented text.
- **Interactive States:** Clicking CTA opens Checkout with next maturity tier pre-selected.

---

### 7. `RenewalNotification`
- **Purpose:** Warning banner alerts users when automatic billing is coming up (14, 7, 3, or 1 day countdowns).
- **Location:** Top layout alert bar, pinned above navigation.
- **Styles:** Colors adjust dynamically from informational slate-gray to urgent warning yellow and emergency amber.
- **Interactive States:** Dissolves smoothly on close click (`×`) and caches dismissal in local storage.

---

### 8. `ExpirationState`
- **Purpose:** Safe empty state displayed inside locked modules upon subscription expiration.
- **Location:** Overlay container inside advanced modules (Backtesting/Shadow Trading panels).
- **Styles:** Grayscale-shaded backdrop representing a safe archived state. Explains that historical logs are fully preserved.
- **Interactive States:** Unlocks a prominent, secure reactivation button.

---

### 9. `FeatureLock`
- **Purpose:** Restricts access to advanced capabilities on lower subscription tiers.
- **Location:** Frosted glass overlay placed over locked tabs.
- **Styles:** Absolute positioned overlay (`backdrop-filter: blur(8px)`) with a glowing gold padlock.
- **Interactive States:** Presents an overlay card with a "Learn more about this Feature" link and upgrade CTAs.

---

### 10. `BillingHistory`
- **Purpose:** Lists past paid invoices with downloadable receipt links for user accounting.
- **Location:** Tabular panel inside `/account/subscription`.
- **Styles:** Minimalist dark table rows.
- **Interactive States:** Hover highlights rows; clicking download triggers invoice PDF generator simulation.
