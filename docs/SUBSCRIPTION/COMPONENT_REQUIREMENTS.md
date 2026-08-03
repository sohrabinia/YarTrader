# TradeYar AI — Component Requirements & Design System Specification
*Document Reference: TY-REV-COMP-05*
*Category: UI Components Specifications & Design Tokens Compliance*

---

## 1. Design System & Token Compliance

In strict alignment with the **Frontend Design Engineering Package v1.0**, all subscription components must maintain a Bloomberg/TradingView style dark theme. No new colors or non-standard radius variables may be introduced.

### Core Design Token Variables:
- **Primary Theme Colors:**
  - Deep Dark Background: `--color-background: #0D0F12`
  - Elevated Card Background: `--color-card-bg: #15181C`
  - Neon Accent / Status OK: `--color-primary-gold: #D4AF37`
  - Warning Accent / Attention: `--color-warning-amber: #F1C40F`
  - Alarm Accent / Limit Reached: `--color-alarm-crimson: #E74C3C`
  - Muted Text: `--color-text-muted: #8E9297`
  - Bright Text: `--color-text-bright: #F5F6F7`
- **Typography & Font Rules:**
  - Persian/Arabic Render: `font-family: 'Vazirmatn', sans-serif` (Dynamic RTL support).
  - English/Turkish Render: `font-family: 'Inter', sans-serif` (Dynamic LTR support).
- **Radius and Spacing Grids:**
  - Border Radius: Standardized at `var(--radius-md): 8px` and `var(--radius-lg): 12px`. No sharp corners or circular buttons (except for close buttons).
  - Layout Grid Spacing: Multiples of 4px (e.g. `gap-4: 16px`, `gap-6: 24px`, `p-6: 24px`, `p-8: 32px`).
- **Elevation and Shadows:**
  - Card Shadow: `var(--shadow-card): 0px 4px 20px rgba(0, 0, 0, 0.4)`
  - Glowing Status Ring: `var(--shadow-neon-gold): 0px 0px 12px rgba(212, 175, 55, 0.3)`

---

## 2. Subscription Components Inventory

---

### Component 1: `PricingCard`
- **Description:** Renders a subscription plan card.
- **Visual Design:** Dark elevated background (`#15181C`), thin golden top-border for the featured plan, large sharp price typography, bullet list with custom-aligned icon bullet points, and a prominent solid primary CTA button.
- **Props Input:**
  - `planName: String`
  - `brandIdentity: String`
  - `price: Number`
  - `billingCycle: String`
  - `featuresList: Array`
  - `ctaText: String`
  - `isFeatured: Boolean`
- **Interactive State Machine:**
  - *Default State:* Standard layout.
  - *Hover State:* Scales card size slightly (by 1.02x) and intensifies card shadow glow.
  - *Click State:* Triggers `onSelectPlan()` and updates button text to loading state with active spinner.

---

### Component 2: `PlanComparison`
- **Description:** An expandable comparison grid table displaying detailed technical limits and capabilities across all six subscription tiers.
- **Visual Design:** Alternating row colors (zebra striping using `#15181C` and `#1D2024`), clean borders (`#2A2E33`), and bright tick icons (`#D4AF37`) or muted crossmarks (`#3E444D`).
- **Interactive Behavior:** Clicking the main category header toggles visibility of underlying sub-feature rows with smooth height animations. Supports RTL layout swapping when user select Persian or Arabic language.

---

### Component 3: `CheckoutSummary`
- **Description:** Renders the transaction summary inside the secure billing shell `/checkout`.
- **Visual Design:** Compact, minimalist box layout, distinct bold sub-totals, clearly delineated tax elements ($0.00), and a highlighted lock icon indicating secure SSL transmission.
- **Props Input:**
  - `selectedPlanName: String`
  - `monthlyPrice: Number`
  - `discountApplied: Number`
  - `totalPrice: Number`
- **Validation Constraints:** Must verify standard form inputs before firing payment intents. Displays loading skeletons during active checkout connection states.

---

### Component 4: `SubscriptionStatusCard`
- **Description:** Displays the user's active billing status inside `/account/subscription`.
- **Visual Design:** High-contrast layout showing the active plan name (e.g., **Professional**) with a pulsating green status circle (`● ACTIVE`) and a clear display of the upcoming renewal date.
- **Interactive Elements:** Contains secondary buttons for "Modify Card" and "Cancel Subscription Renewal".

---

### Component 5: `UsageMeter`
- **Description:** Visual progress meter tracking analytical limits consumption against the plan ceiling.
- **Visual Design:** A horizontal progress bar track (`#212427`) filled with a solid gold status indicator (`#D4AF37`). If usage exceeds 90%, the bar turns amber; if it hits 100%, it flashes crimson.
- **Props Input:**
  - `quotaName: String` (e.g. "AI Assistant Queries")
  - `currentValue: Number`
  - `ceilingLimit: Number`

---

### Component 6: `UpgradeRecommendation`
- **Description:** Promotes the next maturity tier when usage exceeds capacity parameters.
- **Visual Design:** Sleek horizontal callout card with a high-contrast background (`#1C1E22`), dotted amber borders, and an active primary button to upgrade.
- **Interactive Behavior:** Reads current user status and dynamically populates recommendations based on the upgrade rules:
  - *Free / Explorer* -> Recommend *Professional*
  - *Professional* -> Recommend *Advanced Trader*
  - *Advanced Trader* -> Recommend *Professional Desk*

---

### Component 7: `RenewalNotification`
- **Description:** In-app warning banners alert the user to upcoming renewal dates or billing update requirements.
- **Visual Design:** Slim horizontal bar pinned to the global header. Colors adjust from slate gray (14-day notice) to warning gold (1-day notice). Includes close button (`×`) to dismiss.

---

### Component 8: `ExpirationState`
- **Description:** Graceful empty state displayed inside advanced modules when subscription expires.
- **Visual Design:** Uses a beautiful graphic icon of an archived vault, clean muted typography explaining that logs are preserved, and a primary action button pointing to reactivation checkout.
- **Accessibility Rule:** Must be readable by screen readers. Soft overlays are interactive, never causing locked browser frames or hidden focus traps.

---

### Component 9: `FeatureLock`
- **Description:** Lock overlay that disables advanced interaction panels.
- **Visual Design:** Absolute positioned container with frosted-glass blur filter (`backdrop-filter: blur(8px)`) and a glowing padlock icon overlaying the disabled components. Includes a dynamic "Learn More about this Feature" link.

---

### Component 10: `BillingHistory`
- **Description:** Renders a list of historical invoices for accounting and company record-keeping.
- **Visual Design:** Clean tabular structure displaying transaction date, reference ID, plan description, amount, and a downloadable PDF action link (`[ Download Invoice PDF ]`).
- **Data Contract Schema:** Matches standard REST output schemas, ensuring fields automatically handle locale currency transformations.
