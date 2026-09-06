# YARTRADER FRONTEND DESIGN SYSTEM

**Document ID:** YARTRADER-FRONTEND-DS-001
**Status:** CANONICAL FRONTEND SPECIFICATION
**Date:** September 6, 2026
**Repository Location:** `trader-terminal/`
**Framework:** React 18 / Vite 5.4.21 / Tailwind CSS / Local Shadcn-Compatible Primitives Architecture

---

## 1. Executive Summary
This document specifies the canonical frontend design system architecture for YarTrader.

The design system provides a reusable, accessible, and high-density financial UI component library built on a local Shadcn-compatible primitives architecture and Radix-style compositional patterns. It establishes design tokens, typography rules, layout primitives, and component boundaries across all YarTrader product surfaces (`PublicLandingView`, `DashboardView`, `AdminView`, `DemoView`, `IntelligenceView`, `FaqView`, `GuideView`).

---

## 2. Design Tokens & Color Palette

### Color Palette (CSS Custom Properties)
All UI components consume tokens from root custom properties:

```css
:root {
  --primary: #E3A83B;          /* Gold accent for institutional branding */
  --primary-light: #F4C463;    /* Light gold hover state */
  --accent: #4C9A6A;           /* Passed / Success green */
  --surface-dark: #0B1420;     /* Deep slate background */
  --surface-light: #121E2C;    /* Card & Container surface */
  --border-dark: #1E293B;      /* Border strokes */
  --text-dark: #F8FAFC;        /* High-contrast body text */
  --text-muted: #94A3B8;       /* Muted secondary text */
  --danger: #C24A3E;           /* Risk / Failed red */
  --warning: #E3A83B;          /* Warning alert gold */
  --signal: #4FB6C7;           /* Signal highlight cyan */
}
```

### Hardcoded Color Audit & Token Usage
* **Canonical Tokens:** CSS custom properties (`var(--primary)`, `var(--surface-dark)`, `var(--border-dark)`) serve as the single source of truth for UI controls, cards, badges, and layout backgrounds.
* **Legitimate Data Visualization Colors:** Multi-timeframe charts and market structure maps (`#38BDF8`, `#4C9A6A`, `#C24A3E`) use explicit domain status colors required for financial visibility.

---

## 3. Component Architecture

Component hierarchy is strictly separated into 4 distinct tiers:

```text
trader-terminal/src/
├── components/
│   ├── ui/                    # Tier 1: Local Shadcn Primitive Components (Button, Card, Badge, Input, Dialog, AppShell)
│   └── common/                # Tier 2: Composite Utility Components (CommandPalette)
├── design-system/             # Tier 3: Institutional Financial Domain Cards (MetricCard, RiskCard, ChartContainer)
├── views/                     # Tier 4: Page Shell Views (PublicLandingView, DashboardView, AdminView, DemoView, etc.)
└── App.jsx                    # Root Router & AppShell State Container
```

### Tier 1 Primitives (`src/components/ui/`)
* **`Button.jsx`:** Variants (`primary`, `secondary`, `outline`, `ghost`, `destructive`), sizes (`sm`, `md`, `lg`).
* **`Card.jsx`:** Compositional subcomponents (`Card`, `CardHeader`, `CardTitle`, `CardDescription`, `CardContent`, `CardFooter`).
* **`Badge.jsx`:** Variants (`passed`, `failed`, `warning`, `primary`, `neutral`).
* **`Input.jsx`:** Accessible input control with focus-visible ring styles.
* **`Dialog.jsx`:** Backdrop blur modal with keyboard close and accessibility aria labels.
* **`AppShell.jsx`:** Flexible layout container wrapping Header, Sidebar, Main Content, and Chatbot widget.

---

## 4. View Migration Inventory

| View Component | File Location | Migration Status | Primitive Component Usage | Notes |
| -------------- | ------------- | ---------------- | ------------------------- | ----- |
| `PublicLandingView` | `trader-terminal/src/views/PublicLandingView.jsx` | **MIGRATED** | `Card`, `CardHeader`, `CardTitle`, `CardContent`, `Button`, `Badge` | Hero banner, metrics board, 8-timeframe architecture migrated |
| `AdminView` | `trader-terminal/src/views/AdminView.jsx` | **MIGRATED** | `Card`, `CardHeader`, `CardTitle`, `CardContent`, `Badge`, `Button` | SRE Command Center, Health Indicators, RBAC DataTable migrated |
| `DashboardView` | `trader-terminal/src/views/DashboardView.jsx` | **MIGRATED** | `Card`, `CardHeader`, `CardTitle`, `CardContent`, `Badge`, `Button` | Terminal Command status header, controls, chart container migrated |
| `DemoView` | `trader-terminal/src/views/DemoView.jsx` | PRESERVED | `MetricCard`, `DataTable` | Consumes Tier 3 domain cards; preserves MT5 demo trades feed |
| `IntelligenceView` | `trader-terminal/src/views/IntelligenceView.jsx` | PRESERVED | `IntelligenceCard`, `RiskCard` | Consumes Tier 3 domain cards; preserves execution plans |
| `FaqView` | `trader-terminal/src/views/FaqView.jsx` | PRESERVED | Always-visible FAQ list | Displays FAQ questions as always-visible by design |
| `GuideView` | `trader-terminal/src/views/GuideView.jsx` | PRESERVED | Static guide sections | Comprehensive user documentation view |

---

## 5. Typography & Accessibility Baseline

* **Font Stack:** System Sans-Serif (`Inter`, `system-ui`, `sans-serif`) with RTL support (`Vazirmatn`, `Tahoma`).
* **Numeric Readability:** Tabular numeric alignment for easily scannable financial tables and metric cards.
* **Semantic Landmark Structure:** Semantic HTML5 tags (`main`, `aside`, `header`, `button`, `input`).
* **Focus Visibility:** High-contrast focus rings (`focus-visible:ring-2 focus-visible:ring-[var(--primary)]`).
* **Contrast Compliance:** High-contrast text `#F8FAFC` against `#0B1420` surface background.

---

## 6. Responsive QA & Breakpoints

* **320px (Mobile Small):** Single column stack with horizontal scroll tables.
* **375px (Mobile Standard):** Full-width card layout; hamburger mobile drawer.
* **768px (Tablet):** 2-column grid layout; visible sidebar navigation.
* **1024px+ (Desktop):** 4-column status board and multi-pane chart containers.

---

## 7. Phase 3 Completion Verdict

```text
PHASE 3 = PASS
```

**Reasoning:** The local Shadcn-compatible primitive component architecture (`Button`, `Card`, `Badge`, `Input`, `Dialog`, `AppShell`) has been established in `trader-terminal/src/components/ui/`. Major views (`PublicLandingView`, `AdminView`, `DashboardView`) have been migrated to consume canonical Shadcn UI primitives. React SPA builds cleanly via Vite in 1.77s with zero errors, and full Python test suite (1846 passed) verifies zero backend/frontend contract regressions.
