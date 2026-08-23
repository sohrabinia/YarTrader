# YarTrader Design System & UI Consistency Review v1.0

**Date:** August 23, 2026
**Author:** Jules — Lead Systems & Frontend Engineer
**Scope:** Review of `src/design-system/` component library usage, color token consistency, typography, spacing scales, dark mode styling, and RTL layout direction.

---

## 1. Design System Component Verification

Evaluating the 17 core design system components:

1. `MetricCard`: Standardized card widget for quantitative KPI displays.
2. `IntelligenceCard`: Card container for AI research inferences and signal feeds.
3. `RiskCard`: Card container for portfolio heat, drawdown levels, and risk budget gauges.
4. `DecisionCard`: Card container for advisory trade plans (Entry, SL, TP, R:R).
5. `ChartContainer`: Canvas wrapper for TradingView Lightweight Charts with timeframe controls.
6. `StatusBadge`: Pill badge for posture and status (`BUY`, `SELL`, `PASSED`, `FAILED`, `WAIT`).
7. `ConfidenceBadge`: Confidence rating indicator pill ($0\% - 100\%$).
8. `HealthIndicator`: Pulsing live status indicator (`ONLINE`, `CONNECTED`, `DISCONNECTED`).
9. `TimelineStepper`: Horizontal step-by-step progress indicator for onboarding & execution.
10. `PositionTimelineStepper`: 5-phase position lifecycle stepper (`Created → Validated → Opened → Managed → Closed`).
11. `AuditTimeline`: Chronological audit trail event stream with detail inspector drawer.
12. `DataTable`: High-performance data table wrapper powered by `@tanstack/react-table`.
13. `FeatureToggle`: Switch component for feature flags and system toggles.
14. `ConfigPanel`: Admin parameter configuration container with inputs and sliders.
15. `EmptyState`: Standardized empty state feedback card with icon and description.
16. `LoadingSkeleton`: Animated skeleton loader placeholder.
17. `ErrorState`: Error boundary card with error message and retry button.

---

## 2. Institutional Visual Token Consistency

* **Primary Accent:** Amber `#E3A83B` used consistently for primary buttons, active tab indicators, and brand logos.
* **Background Canvas:** Dark Slate `#0B1420` (Base) and `#121E2C` (Surface) eliminate visual glare during long trading sessions.
* **Signaling Color Scale:**
  * Success / Gain: `#10B981` (Green).
  * Critical / Live Blocked: `#EF4444` (Red).
  * Warning / Small N Sample: `#E3A83B` (Amber).
  * Signal / Structure: `#4FB6C7` (Cyan).
  * AI Cognitive Engine: `#8B5CF6` (Violet).

---

## 3. Typography & Spacing Audit

* **Typography:** `Vazirmatn` font for body text and labels; `Fira Code` monospace with `font-variant-numeric: tabular-nums` for prices, ticket IDs, and percentages.
* **RTL Compliance:** Dynamic `document.body.dir = isRTL ? 'rtl' : 'ltr'` updates margin and border alignments across all cards, forms, and tables.

---

*Design System Review certified by Jules — Lead Systems & Frontend Engineer.*
*YarTrader Autonomous Financial Intelligence Platform.*
