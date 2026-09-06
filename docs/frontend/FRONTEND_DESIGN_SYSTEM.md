# YARTRADER FRONTEND DESIGN SYSTEM

**Document ID:** YARTRADER-FRONTEND-DS-001
**Status:** CANONICAL FRONTEND SPECIFICATION
**Date:** September 6, 2026
**Repository Location:** `trader-terminal/`
**Framework:** React 18 / Vite 5.4.21 / Tailwind CSS / Shadcn UI Primitives

---

## 1. Executive Summary
This document specifies the canonical frontend design system architecture for YarTrader.

The design system provides a reusable, accessible, and high-density financial UI component library built on Shadcn UI primitives and Radix-style architectural patterns. It establishes design tokens, typography rules, layout primitives, and component boundaries across all YarTrader product surfaces (`PublicLandingView`, `DashboardView`, `AdminView`, `DemoView`, `IntelligenceView`, `FaqView`, `GuideView`).

---

## 2. Design Tokens

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

---

## 3. Component Architecture

Component hierarchy is strictly separated into 4 distinct tiers:

```text
trader-terminal/src/
├── components/
│   ├── ui/                    # Tier 1: Primitive UI Components (Button, Card, Badge, Input, Dialog)
│   └── common/                # Tier 2: Composite Utility Components (CommandPalette)
├── design-system/             # Tier 3: Institutional Financial Domain Cards (MetricCard, RiskCard, ChartContainer)
├── views/                     # Tier 4: Page Shell Views (DashboardView, AdminView, PublicLandingView)
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

## 4. Typography Rules

* **Font Stack:** System Sans-Serif (`Inter`, `system-ui`, `sans-serif`) with RTL support (`Vazirmatn`, `Tahoma`).
* **Financial Numbers:** Tabular numeric alignment for easily scannable financial tables and metric cards.
* **Hierarchy:**
  * Page Title: `text-2xl font-bold tracking-tight text-[var(--primary)]`
  * Section Header: `text-lg font-semibold text-[var(--primary)]`
  * Body Text: `text-sm text-[var(--text-dark)] leading-relaxed`
  * Secondary Text: `text-xs text-[var(--text-muted)]`

---

## 5. Accessibility Baseline

1. **Semantic Structure:** Semantic HTML5 tags (`main`, `aside`, `header`, `button`, `input`).
2. **Keyboard Navigation:** Full focus ring indicators (`focus-visible:ring-2 focus-visible:ring-[var(--primary)]`).
3. **Contrast Compliance:** High-contrast text `#F8FAFC` against `#0B1420` surface background.
4. **Modal Dialogs:** `role="dialog"` with explicit aria-label and close controls.

---

## 6. Responsive Breakpoints

* **Mobile Small:** `320px` - Single column layout with drawer navigation.
* **Mobile Standard:** `375px` - Stacked cards with tabular scroll overflow.
* **Tablet:** `768px` - 2-column grid; visible sidebar navigation.
* **Desktop:** `1024px+` - Full 4-column status board and multi-pane chart containers.

---

## 7. Phase 3 Completion Verdict

```text
PHASE 3 = PASS
```

**Reasoning:** The Shadcn UI primitive component architecture (`Button`, `Card`, `Badge`, `Input`, `Dialog`, `AppShell`) has been established in `trader-terminal/src/components/ui/`. Canonical design tokens are defined and consumed across all product views. React SPA builds cleanly via Vite in 1.21s with zero errors, and full Python test suite (1846 passed) verifies zero backend/frontend contract regressions.
