# YarTrader Frontend Master Design Specification v1.0

**Document Version:** 1.0.0
**Status:** Certified Design Specification (Foundation Package)
**Scope:** Design System, UX Architecture & Visual Guidelines
**Target Implementation:** YarTrader Professional Trading Terminal Rebuild

---

## 1. Brand Identity & Visual Positioning

YarTrader is visually positioned as a **Hybrid Institutional Financial Intelligence & Autonomous Cognitive Trading Terminal**.

### Brand Personality
* **Institutional & Precise:** Clean, dark high-contrast interface modeled after Bloomberg Terminal and MetaTrader Pro, prioritizing financial clarity over consumer eye-candy.
* **AI Cognitive Transparency:** Explainable AI (XAI) trade reasoning, multi-timeframe perception, and fractal memory visualization without fake neural-network animations or speculative graphics.
* **Execution Boundary Safety:** Clear, un-ambiguous visual separation between **MT4 Live Trading** (`143056202`), **MT5 Demo Trading** (`52961173`), **Backtesting**, and **Shadow Paper Trading**.

---

## 2. Institutional Color Palette

| Token Category | Token Name | HEX / Value | Purpose / Role |
| :--- | :--- | :--- | :--- |
| **Brand Primary** | `--color-primary` | `#E3A83B` | High-contrast Amber for primary actions, active tabs, and key brand callouts. |
| **Primary Hover** | `--color-primary-hover` | `#F2BA4E` | Lightened Amber state for button hover. |
| **Primary Dim** | `--color-primary-dim` | `rgba(227, 168, 59, 0.12)` | Subtle Amber background glow for active sidebar items & bot chat bubbles. |
| **Background Base** | `--color-bg-base` | `#0B1420` | Deep midnight dark background for high contrast and reduced eye strain. |
| **Background Surface** | `--color-bg-surface` | `#121E2C` | Surface container for top header, sidebar, and control panels. |
| **Card Surface** | `--color-bg-card` | `#172537` | Content card background with 1px subtle borders. |
| **Border Subtle** | `--color-border-subtle` | `#23354A` | 1px border lines separating panels, tables, and inputs. |
| **Signaling Success** | `--color-success` | `#4C9A6A` | Muted institutional green for BUY signals, positive P&L, and passed checks. |
| **Signaling Critical** | `--color-critical` | `#C24A3E` | Muted institutional red for SELL signals, negative P&L, and hard safety blocks. |
| **Signaling Warning** | `--color-warning` | `#E3A83B` | Amber alert state for caution or unproven sample sizes. |
| **Signal Cyan** | `--color-signal` | `#4FB6C7` | Cyan accent reserved for paper shadow positions and real-time event pulses. |
| **Text Dark Mode** | `--color-text-dark` | `#F1F5F9` | High-legibility off-white text for dark theme. |
| **Text Muted** | `--color-text-muted` | `#9AA1B9` | Secondary muted text for timestamps and descriptions. |

---

## 3. Typography & Localization System

### Font Families
* **Primary Sans-Serif (Multi-lingual):** `Vazirmatn`, `-apple-system`, `BlinkMacSystemFont`, `Segoe UI`, `Roboto`, `sans-serif`.
* **Financial Numbers & Monospace:** `Fira Code`, `Courier New`, `Courier`, `monospace`.

### Typography Scale
* **Display / Title:** 24px (`1.5rem`), Weight 700, Line-height 1.3
* **Heading 1:** 20px (`1.25rem`), Weight 700, Line-height 1.4
* **Heading 2:** 16px (`1.0rem`), Weight 600, Line-height 1.4
* **Body Regular:** 14px (`0.875rem`), Weight 400, Line-height 1.5
* **Caption / Small:** 12px (`0.75rem`), Weight 400, Line-height 1.4
* **Monospace Numeric:** 14px (`0.875rem`), Tabular-nums (`font-variant-numeric: tabular-nums`).

### Localization Rules (EN, FA, AR, TR)
* **Persian (fa) & Arabic (ar):** Dynamic `dir="rtl"`, primary font `Vazirmatn`.
* **English (en) & Turkish (tr):** Dynamic `dir="ltr"`, primary font `-apple-system` / `Vazirmatn`.
* **Financial Number Stability:** Numbers, prices, currency figures ($1,000.00), and percentages (+63.1%) retain LTR directional formatting inside tabular cells to prevent layout corruption during RTL rendering.

---

## 4. Spacing & Base-8 Layout Architecture

* **Spacing Grid:** Base-8 scale (`4px`, `8px`, `12px`, `16px`, `24px`, `32px`, `48px`).
* **Container Max-Width:** 1600px max-width container centered on ultra-wide desktop monitors.
* **Fixed Sidebar Width:** 240px fixed desktop sidebar collapsing to a top horizontal wrap navigation bar on tablet (<1024px) and mobile (<375px).
* **Grid Breakpoints:**
  * Desktop Ultra-Wide: 1440px - 1920px
  * Laptop Standard: 1024px - 1439px
  * Tablet: 768px - 1023px
  * Mobile: 375px - 767px

---

## 5. Reusable Component Specifications (24 Components)

### 1. Primary Action Button (`Button`)
* **Background:** `--color-primary` (`#E3A83B`)
* **Text Color:** `#07090E` (Dark high-contrast on Amber)
* **Hover State:** `--color-primary-hover` (`#F2BA4E`), translateY(-1px)
* **Focus State:** 2px solid border `--color-primary`
* **Disabled State:** Background `--color-text-muted`, cursor `not-allowed`

### 2. Secondary Outline Button (`ButtonSecondary`)
* **Background:** Transparent
* **Border:** 1px solid `--color-border-subtle`
* **Text Color:** `--color-text-dark`
* **Hover State:** Background `rgba(255, 255, 255, 0.05)`

### 3. Data Tables (`Table`)
* **Header:** Background `rgba(30, 41, 59, 0.4)`, font-weight 700
* **Cells:** 1px bottom border `--color-border-subtle`, tabular numeric formatting
* **Responsive Behavior:** Horizontal touch scroll wrapper (`overflow-x: auto`) on mobile viewports.

### 4. Floating Chatbot (`ChatbotWidget`)
* **Fixed Position:** Bottom 20px, Right 20px, Width 380px
* **Header:** Background `#E3A83B`, dark high-contrast title text, AI pulse animation
* **Error Retry Callback:** Inline retry button on error bubbles.

---

## 6. Terminal & Execution UX Hierarchy

### Terminal UX Cascade (`#/dashboard`)
```text
Top Bar: Live/Demo Status Badges + Backend Health Indicator
   ↓
Horizon Tabs: Micro (M1-M5) | Short (M15) | Medium (H1-H4) | Macro (D1-W1)
   ↓
Asset Filter: All Assets | Gold (XAUUSD) | Bitcoin (BTCUSD) | Euro (EURUSD)
   ↓
Qualified Signal Cards Grid: Posture, Confidence %, Entry, Target, Invalidation, Narrative
   ↓
Equity Compounding Simulator: Initial Capital, Monthly Yield %, Duration, Projected Return
```

---

## 7. Execution Safety Boundaries (MT4 vs MT5)

* **MT4 Live Boundary:** Assigned strictly to **Live Real-Money Trading** (`143056202`). Hard-blocked on UI (`#/live`) via red warning banner when `LIVE_TRADING_ENABLED=False`.
* **MT5 Execution Boundary:** Restricted strictly to **Backtesting, DEMO Trading (`52961173`), and Forward Observation**. The UI explicitly badges all MT5 trades as `DEMO / PAPER` and never implies live trading.

---

## 8. Intelligence UX & Explainability (XAI)

* **Multi-Timeframe Perception:** Real-time perception cards without decorative or fake neural network animations.
* **Reasoning Trace:** Bulleted chronological trade plan steps directly linked to `/api/execution/reasoning`.
* **Fractal Memory Scoreboard:** Sample size $N$ evaluation warnings when $N < 30$ ("Insufficient N / Unproven").

---

## 9. Accessibility & Compliance Standards (WCAG 2.2 AA)

* **Contrast Ratios:** Minimum 4.5:1 text-to-background contrast ratio (e.g., `#07090E` dark text on `#E3A83B` Amber).
* **Keyboard Focus:** Visible 2px outline focus indicators on interactive buttons, inputs, and tab selectors.
* **Touch Target Size:** Minimum 44x44px touch target padding on mobile viewports.
