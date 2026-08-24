# YarTrader Institutional Design System Specification v1.0

**Date:** August 23, 2026
**Author:** Jules — Lead Systems & Frontend Engineer
**Scope:** Master visual identity, dark institutional color tokens, typography rules, component library, and responsive RTL guidelines for `src/design-system/`.

---

## 1. Visual Identity & Brand Philosophy

YarTrader is an **Institutional Financial Intelligence Operating System** and AI Research Engine. Its visual identity must convey quantitative precision, security, and institutional authority:

* **Theme:** Dark Institutional Financial Intelligence (Dark Mode First).
* **Style:** Quant Platform, AI Research Laboratory, Sovereign Trading System.
* **Avoid:** Consumer crypto gamification, neon clutter, generic SaaS white templates.

---

## 2. Master Institutional Color Tokens

```css
:root {
  /* 1. Base Dark Backgrounds */
  --color-bg-base: #0B1420;        /* Main dark canvas background */
  --color-bg-surface: #121E2C;     /* Sidebar & header dark surface */
  --color-bg-card: #172537;        /* Widget & card surface */
  --color-bg-subtle: #1E2D3D;      /* Hover states & nested cards */

  /* 2. Institutional Borders */
  --color-border-subtle: #23354A;  /* Standard card & divider border */
  --color-border-glow: #384E66;    /* Active focus & highlighted border */

  /* 3. Primary Brand Accents (Gold / Amber) */
  --color-primary: #E3A83B;        /* Brand Primary Gold */
  --color-primary-hover: #F2BA4E;  /* Hover Primary */
  --color-primary-dim: rgba(227, 168, 59, 0.12); /* Subtle Gold highlight */

  /* 4. Functional Signaling & Status */
  --color-success: #10B981;        /* Positive Gain Green / Passed Status */
  --color-critical: #EF4444;       /* Danger Red / Live Blocked / Risk Alert */
  --color-warning: #E3A83B;        /* Amber Warning / Small N / Caution */
  --color-signal: #4FB6C7;         /* Cyan Signal / Market Structure */
  --color-ai-intel: #8B5CF6;       /* Violet Purple / AI Cognitive Engine */

  /* 5. Typography Colors */
  --color-text-main: #F1F5F9;      /* Primary high-contrast text */
  --color-text-muted: #9AA1B9;     /* Secondary muted labels */
  --color-text-dim: #565D73;       /* Disabled & background text */
}
```

---

## 3. Typography & Financial Number Formatting

* **Sans-Serif Font:** `Vazirmatn`, `-apple-system`, `BlinkMacSystemFont`, `Segoe UI`, `sans-serif`.
  * Used across all UI labels, headings, body text, and bilingual menus (Fa, En, Tr, Ar).
* **Monospace Font:** `Fira Code`, `Courier New`, `monospace`.
  * Mandatory for all numerical cells, prices, ticket IDs, retcodes, timestamps, and confidence percentages.
  * **Numeric Rule:** All tabular financial numbers MUST apply `font-variant-numeric: tabular-nums` to eliminate layout jitter during tick updates.

---

## 4. Design System Component Library (`src/design-system/`)

The design system standardizes 17 mandatory reusable UI components across the platform:

| Component Name | File Location | Purpose & Rendering Logic | Props / Modifiers |
| :--- | :--- | :--- | :--- |
| `MetricCard` | `src/design-system/MetricCard.jsx` | Displays key quantitative metrics, labels, sparkline trends, and status indicators. | `title, value, change, status, sparkline` |
| `IntelligenceCard` | `src/design-system/IntelligenceCard.jsx` | Highlights AI research inferences, multi-timeframe signals, and confidence scores. | `symbol, posture, confidence, narrative` |
| `RiskCard` | `src/design-system/RiskCard.jsx` | Renders portfolio heat, drawdown levels, and risk budget progress gauges. | `heat, riskBudget, drawdownLevel, approved` |
| `DecisionCard` | `src/design-system/DecisionCard.jsx` | Displays actionable advisory trade plans with entry, SL, TP, and R:R ratios. | `action, entry, stopLoss, takeProfit, rr` |
| `ChartContainer` | `src/design-system/ChartContainer.jsx` | Wrapper canvas container for TradingView Lightweight Charts with controls. | `symbol, timeframe, overlays, height` |
| `StatusBadge` | `src/design-system/StatusBadge.jsx` | Renders color-coded status badges (`BUY`, `SELL`, `PASSED`, `FAILED`, `WAIT`). | `variant, label, pulse` |
| `ConfidenceBadge` | `src/design-system/ConfidenceBadge.jsx` | Visual confidence rating pill ($0\% - 100\%$) with color gradient. | `score, showBar` |
| `HealthIndicator` | `src/design-system/HealthIndicator.jsx` | Live pulsing connection state indicator (`MT5`, `API`, `Ingestion`). | `state, latency, label` |
| `TimelineStepper` | `src/design-system/TimelineStepper.jsx` | Step-by-step horizontal progress tracker for execution and onboarding. | `steps, activeStep, status` |
| `AuditTimeline` | `src/design-system/AuditTimeline.jsx` | Chronological event inspector stream with expand/collapse details. | `events, onInspect` |
| `DataTable` | `src/design-system/DataTable.jsx` | High-performance tabular data grid wrapper powered by `@tanstack/react-table`. | `columns, data, sorting, pagination` |
| `FeatureToggle` | `src/design-system/FeatureToggle.jsx` | Switch control for administrative feature flags and system modes. | `enabled, onChange, label, disabled` |
| `ConfigPanel` | `src/design-system/ConfigPanel.jsx` | Parameter configuration panel with sliders, inputs, and reset actions. | `title, description, children` |
| `EmptyState` | `src/design-system/EmptyState.jsx` | Standardized empty state card displaying icon, message, and action CTA. | `icon, title, description, action` |
| `LoadingSkeleton` | `src/design-system/LoadingSkeleton.jsx` | Content loading skeleton placeholder matching widget dimensions. | `type, rows, height` |
| `ErrorState` | `src/design-system/ErrorState.jsx` | Error boundary feedback card displaying error detail and retry button. | `message, onRetry` |
| `PositionTimelineStepper` | `src/design-system/PositionTimelineStepper.jsx` | 5-phase position lifecycle stepper (`Created → Validated → Opened → Managed → Closed`). | `lifecycleState, retcode, timestamps` |

---

## 5. Responsive Layout & Dynamic RTL/LTR Rules

* **RTL Enforcement:** Managed dynamically via `I18nProvider`:
  ```javascript
  const isRTL = lang === 'fa' || lang === 'ar';
  document.body.dir = isRTL ? 'rtl' : 'ltr';
  document.body.style.fontFamily = isRTL ? "'Vazirmatn', sans-serif" : "'Segoe UI', Roboto, sans-serif";
  ```
* **Grid Breakpoints:**
  * Desktop ($> 1280\text{px}$): 3-column / 4-column widget grid.
  * Tablet ($768\text{px} - 1279\text{px}$): 2-column responsive layout, collapsible sidebar.
  * Mobile ($< 768\text{px}$): Single column layout, sticky header ticker, slide-over navigation drawer.

---

*Design System Specification certified by Jules — Lead Systems & Frontend Engineer.*
*YarTrader Autonomous Financial Intelligence Platform.*
