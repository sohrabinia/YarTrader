# YarTrader Current Visual & UX Audit Register v2.0

**Document Version:** 2.0.0
**Status:** Certified Visual Audit Register
**Scope:** Forensic UX & Visual Problem Register

---

## Issue Classification Tiers

* **P0 — Critical:** Usability or safety issues that could lead to user error or execution confusion.
* **P1 — Major:** Significant visual/UX defects affecting daily trading workflows.
* **P2 — Moderate:** Moderate layout, spacing, or responsive inconsistencies.
* **P3 — Cosmetic:** Minor visual refinements.

---

## 1. Issue Register

### P0 — Critical Usability & Safety Issues

| Issue ID | Screen / Route | Component | Description & Current Behavior | Evidence Screenshot | Suggested Direction |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **P0-1** | Live Gate (`#/live`) | `SafetyAlertBox` | Hard safety block message requires higher visual contrast to ensure no user confuses demo/paper mode with live trading. | `12_live_gate.png` | Implement distinct red emergency border styling with explicit MT4 Live vs MT5 Demo account tags. |
| **P0-2** | Execution Intel (`#/execution-intel`) | `TradePlanBoard` | Advisory trade plans and risk status are rendered side-by-side without clear visual distinction between advisory vs automated actions. | `14_execution_intel.png` | Add explicit `ADVISORY ONLY (NON-AUTOMATED)` status badge above trade plans. |

### P1 — Major Visual & UX Problems

| Issue ID | Screen / Route | Component | Description & Current Behavior | Evidence Screenshot | Suggested Direction |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **P1-1** | Trader Terminal (`#/dashboard`) | `HorizonTabs` | Horizon filter tabs (`micro`, `short`, `medium`, `macro`) lack clear visual distinction when unselected. | `08_terminal_dashboard.png` | Apply distinct border highlights and active Amber fill for selected horizon tab. |
| **P1-2** | Signal Hub (`#/signals`) | `SubNavTabs` | Signal category tabs (`Live`, `Shadow`, `Backtest`, `Historical`) overlap on narrow mobile viewports. | `13_signals.png` | Enable horizontal touch scrolling wrapper for mobile tab bars. |
| **P1-3** | Learning Matrix (`#/learning`) | `Table` | Sample size $N < 30$ warning text is rendered as small muted subtext under row numbers. | `15_learning.png` | Elevate $N < 30$ status to a prominent Amber warning badge ("Small N / Unproven"). |

### P2 — Moderate Layout & Responsive Problems

| Issue ID | Screen / Route | Component | Description & Current Behavior | Evidence Screenshot | Suggested Direction |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **P2-1** | SRE Admin (`#/admin`) | `LogsBox` | Monospaced console logs box has a fixed 250px height that causes excessive scrolling on long log streams. | `16_admin.png` | Expand log viewer height to 350px and add clear filter/search input. |
| **P2-2** | Pricing (`#/pricing`) | `PlanCard` | Plan detail drawer opens inline below cards rather than as an overlay modal on desktop. | `03_pricing.png` | Standardize as an overlay drawer or centered backdrop modal. |

### P3 — Cosmetic Refinements

| Issue ID | Screen / Route | Component | Description & Current Behavior | Evidence Screenshot | Suggested Direction |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **P3-1** | Marketing Landing (`#/`) | `StatusBoard` | Metric cards use fixed min-width causing minor gap inconsistency on 1024px tablet viewports. | `01_landing.png` | Adjust CSS grid auto-fit minmax threshold to `160px`. |
