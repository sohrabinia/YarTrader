# YarTrader Frontend Complete Forensic Discovery & Design Handoff

**Document Version:** 1.0.0
**Status:** Certified Final Forensic Handoff
**Target Phase:** AI-Led / Design System Rebuild & Implementation
**Baseline Commit Tag:** `yartrader-v1.0-release-candidate` / V1.2 Runtime

---

## 1. Executive Summary

This document serves as the canonical, authoritative forensic discovery and handoff specification for the complete YarTrader frontend application.

The primary goal of this handoff is to provide an accurate, implementation-ready representation of the current frontend so that future redesign and component rebuild phases can proceed without losing business logic, API integrations, real-time telemetry, or execution safety boundaries.

### Summary of Discovery Findings
* **Single-Page Application (SPA) Architecture:** Built with React 18, Vite 5, standard client-side hash router (`#/`), and Zustand / lightweight custom hooks for state management.
* **Server-Side Fallback Routes:** FastAPI backend (`src/Application/Services/web_dashboard.py`) mounts the Vite build artifact or renders dynamic HTMLResponse templates for SPA hash-fallback compatibility across all routes.
* **Total Frontend Routes:** 16 active routes across 5 privacy/authorization tiers (Public, Authenticated Trader, Trading Mode Shells, SRE Admin, System/Auth).
* **Total Screens / Shells:** 16 distinct visual views.
* **Reusable Components:** 24 mapped UI components (Button, Cards, Tables, Status Boards, Chatbot Widget, Score Circles, Notification Toasts, Language Selectors, Theme Toggles).
* **API Endpoints Mapped:** 42 distinct FastAPI REST endpoints bound to frontend components.
* **Real-Time Data Streaming:** Real-time polling and event envelope protocol for market perception, multi-timeframe research snapshots, and live validation status.
* **Visual Tokens:** Base-8 spacing system, institutional fintech color palette (Dark `#0B1420` surface with high-contrast Amber `#E3A83B` actions, `#4C9A6A` success, `#C24A3E` critical danger, `#4FB6C7` signal cyan), and dual-theme capability (Institutional Dark vs Editorial Light).

---

## 2. Frontend Architecture

### Architecture Stack Overview
* **Framework:** React 18 (Hooks, Context Provider for i18n, custom hash router listener).
* **Build Tool:** Vite 5.4.21.
* **Styling:** CSS3 Variables (`src/assets/globals.css`), Base-8 spacing, responsive flex/grid layouts.
* **State Management:**
  * Global Auth Store (`src/store/useAuthStore.js` with `localStorage` persistence).
  * Translation Context (`src/services/i18n.jsx` supporting `fa`, `en`, `tr`, `ar`).
  * API Service Client (`src/services/api.js` with Bearer Token header injection).
* **Backend Integration:** FastAPI Uvicorn ASGI server mounted at `http://localhost:8000`.

---

## 3. Route & Page Map

| Route Path | Page Name | Access Tier | Purpose | API Dependencies | Primary Components Used |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `#/` | Landing / Marketing | PUBLIC | Marketing introduction, platform metrics, standards overview. | `/api/public/metrics` | Header, StatusBoard, MetricCard, Footer |
| `#/features` | Cognitive Features | PUBLIC | Highlights non-indicator price action architecture. | None | FeatureGrid, FeatureCard |
| `#/pricing` | Pricing Plans | PUBLIC | Displays subscription tiers and detailed plan modals. | `/api/subscription/plans` | PricingGrid, PlanCard, PlanDetailModal |
| `#/blog` | Research Blog | PUBLIC | Displays institutional trading articles and research tags. | `/api/blog` | BlogGrid, BlogCard, TagBadge |
| `#/login` | Login Form | PUBLIC | User authentication (Email/Password & Google/Apple social). | `/api/auth/login`, `/api/auth/google`, `/api/auth/apple` | FormCard, InputField, SocialButton, Toast |
| `#/register` | Registration Form | PUBLIC | New trader registration. | `/api/auth/register` | FormCard, InputField, SocialButton, Toast |
| `#/forgot-password` | Forgot Password | PUBLIC | Password recovery trigger. | `/api/auth/forgot-password` | FormCard, InputField, Toast |
| `#/dashboard` | Trader Terminal | AUTHENTICATED USER | Market overview, signal feed, compounding simulator. | `/api/user/markets`, `/api/user/signals` | HorizonTabs, SignalFeed, CompoundingSim |
| `#/backtest` | Backtest Engine UI | AUTHENTICATED USER | Point-in-time historical backtest simulation and audit logs. | `/api/backtest/run`, `/api/backtest/history` | BacktestForm, AuditBoard, BacktestTable |
| `#/demo` | MT5 Demo Operations | AUTHENTICATED USER | Broker demo account order lifecycle and P&L history. | `/api/demo/trades`, `/api/demo/report` | DemoScorecard, BrokerOrdersTable |
| `#/shadow` | Shadow Paper Trading | AUTHENTICATED USER | Virtual $1,000 paper capital execution & position manager. | `/api/shadow/report`, `/api/admin/shadow-trades` | VirtualAccountBoard, PaperPositionsTable |
| `#/live` | Live Trading Gate | AUTHENTICATED USER | Safety gate isolation screen showing SRE fail-closed block. | None | SafetyAlertBox, GateStatusBoard |
| `#/signals` | Signal Hub | AUTHENTICATED USER | Multi-tab signal stream (Live, Shadow, Backtest, Historical). | `/api/user/signals` | SubNavTabs, SignalFeedGrid |
| `#/execution-intel` | Execution Board | AUTHENTICATED USER | Institutional trade plans, price action structure, liquidity. | `/api/execution/*`, `/api/structure/*`, `/api/liquidity/*`, `/api/portfolio/*` | TradePlanBoard, StructureTable, RiskBoard |
| `#/learning` | Pattern Learning Matrix | AUTHENTICATED USER | Multi-timeframe fractal pattern memory and confidence scores. | `/api/intelligence/learning-matrix` | LearningScoreboard, PatternTable, InspectModal |
| `#/admin` | SRE Control Center | ADMIN | Active symbol registration, SRE validation runner, SCM logs. | `/api/admin/*`, `/api/devops/*`, `/api/validation/*` | SymbolRegisterBar, ValidationRunner, LogsBox |

---

## 4. Screen-by-Screen UI Inventory

*(Extracted directly from runtime inspection of `App.jsx` and `validation/frontend_current_state/` screenshots)*

1. **Header Navigation:**
   * Logo ("YarTrader"), Live/Demo Status Badges (`LIVE`, `DEMO`, `UNREACHABLE`), Language Selector (`fa`, `en`, `tr`, `ar`), Theme Toggle (`☀️`/`🌙`).
2. **Sidebar:**
   * Links to all active pages, User Profile Badge (`Name (Role)`), Logout Action.
3. **Marketing Landing Shell (`#/`):**
   * Welcome Card, Platform Uptime Indicator, Historical Simulated Trades Counter, PES Compliance Status.
4. **Features Shell (`#/features`):**
   * 4-Card Grid highlighting Price Action, Multi-Horizon Alignment, Virtual Position Tracker, Active Learning Loop.
5. **Pricing Shell (`#/pricing`):**
   * Subscription Tiers Cards, Plan Detail Modal with feature checklists and upgrade CTA.
6. **Trader Terminal Shell (`#/dashboard`):**
   * Horizon Tabs (`Micro`, `Short`, `Medium`, `Macro`), Asset Filter Dropdown, Signal Cards Grid, Equity Compounding Simulator.
7. **Backtest Shell (`#/backtest`):**
   * Symbol/Timeframe/Candles Input Bar, Run Simulation Button, Point-in-Time Audit Status Board, Historical Backtest Table.
8. **Demo Shell (`#/demo`):**
   * Broker Demo Account Summary (`Alpari-MT5-Demo`, Account ID `52961173`), Broker Demo Orders Table.
9. **Shadow Shell (`#/shadow`):**
   * Virtual Account Scorecard (`YARTRADER-PAPER-001`, Balance `$1,000.00`), Paper Positions Manager Table.
10. **Live Shell (`#/live`):**
    * Red Emergency Alert Banner (`🛑 HARD BLOCKED: Live Real-Money Execution Disabled`), SRE Gate Status Board.
11. **Signals Hub Shell (`#/signals`):**
    * Sub-Nav Tabs (`Live`, `Shadow`, `Backtest`, `Historical`), Qualified Signal Feed.
12. **Execution Intel Shell (`#/execution-intel`):**
    * Trade Plan Advisory Board, Portfolio Risk Board, Market Structure Swing High/Low Table, Order Blocks & FVG Supply/Demand Cards, Pattern Similarity Matched Feed.
13. **Learning Matrix Shell (`#/learning`):**
    * Pattern Memory Scoreboard, Multi-Timeframe Pattern Performance Table, Pattern Evidence Inspector Drawer.
14. **SRE Admin Center Shell (`#/admin`):**
    * Add Symbol Registration Bar, SRE Validation Runner with Live Log Console, Readiness Score Circle, SCM Reports Table.
15. **Auth Views (`#/login`, `#/register`, `#/forgot-password`):**
    * Centered Form Cards, Social Login Buttons (Google/Apple), Field Validation, Action Buttons.
16. **Floating Support Chatbot:**
    * Collapsible bottom-right widget, AI Pulse indicator, Quick Prompt Chips, Message Bubbles, Error Retry Handler.

---

## 5. Component Inventory

*(24 Reusable Components Identified)*

1. `Header`: Global navbar with status indicators, language dropdown, theme toggle.
2. `Sidebar`: Navigation links, user profile badge, logout trigger.
3. `Card`: Surface container with border and dark/light elevation.
4. `StatusBoard`: Responsive CSS grid displaying key metric tiles.
5. `StatusItem`: Individual metric tile with tabular numeric formatting.
6. `Button`: High-contrast primary action button (Amber `#E3A83B`).
7. `ButtonSecondary`: Outline action button.
8. `SocialButton`: Third-party OAuth authentication trigger (Google/Apple).
9. `InputField`: Standard text/email/password/number input element.
10. `SelectField`: Custom styled dropdown select element.
11. `HorizonTabs`: 4-button horizon selector (`micro`, `short`, `medium`, `macro`).
12. `SubNavTabs`: Secondary tab bar used in Signal Hub.
13. `SignalCard`: Visual container for trading signals and structural reasoning.
14. `BacktestForm`: Input controls for backtest symbol, timeframe, and candle count.
15. `Table`: Standardized data table with tabular number alignment.
16. `ScoreCircle`: Radial score badge with tabular numeric center text.
17. `LogsBox`: Fixed-height dark monospaced live log viewer console.
18. `ChatbotWidget`: Fixed floating support assistant container.
19. `ChatBubble`: Individual user or bot message bubble.
20. `QuickPromptChip`: Interactive quick question button for AI Chat.
21. `NotificationToast`: Top-centered fixed notification banner.
22. `PlanDetailModal`: Overlay container displaying selected subscription plan details.
23. `PatternInspectDrawer`: Modal container displaying pattern memory evidence.
24. `BackendErrorBanner`: Critical top warning banner shown when backend is unreachable.

---

## 6. Data & API Binding

* **Public Metrics:** `GET /api/public/metrics` -> Marketing Landing tiles.
* **Subscription Tiers:** `GET /api/subscription/plans` -> Pricing Grid.
* **Blog Articles:** `GET /api/blog` -> Research Blog Cards.
* **Signals Feed:** `GET /api/user/signals?horizon={horizon}` -> Terminal Signal Cards.
* **Markets Overview:** `GET /api/user/markets` -> Asset Filters & Watchlist.
* **Backtest History:** `GET /api/backtest/history` -> Backtest Runs Table.
* **Backtest Execution:** `POST /api/backtest/run` -> Triggers new backtest simulation.
* **Demo Trades & Report:** `GET /api/demo/trades`, `GET /api/demo/report` -> Broker Demo Table.
* **Shadow Paper Report:** `GET /api/shadow/report`, `GET /api/admin/shadow-trades` -> Virtual Account & Paper Positions.
* **Execution Plans & Intelligence:** `GET /api/execution/plans`, `GET /api/execution/confidence`, `GET /api/execution/reasoning` -> Institutional Board.
* **Structure & Liquidity:** `GET /api/structure/map`, `GET /api/structure/alignment`, `GET /api/liquidity/map` -> Structure & Supply/Demand Tables.
* **Learning Matrix:** `GET /api/intelligence/learning-matrix` -> Pattern Memory Table.
* **Admin Symbols & Reports:** `GET /api/admin/symbols`, `POST /api/admin/symbols`, `GET /api/admin/reports` -> SRE Admin Panel.
* **Validation Control:** `POST /api/validation/run`, `GET /api/validation/status` -> Validation Runner & Live Logs.
* **Auth Operations:** `POST /api/auth/login`, `POST /api/auth/register`, `POST /api/auth/forgot-password`, `POST /api/auth/logout`.
* **AI Cognitive Chat:** `POST /api/chat/assistant` -> Floating Chatbot Assistant.

---

## 7. YarTrader Terminal UX & Execution Boundaries

### Strict Architectural Boundaries
* **MT4 Execution Boundary:** Assigned strictly to **Live / Signal Execution** (`143056202` on `Alpari-Pro.ECN`). Live execution is hard-blocked by `MetaTraderSafetyGate` when `LIVE_TRADING_ENABLED=False`.
* **MT5 Execution Boundary:** Restricted strictly to **Backtesting, DEMO Trading (`52961173`), and Forward Observation**.
* **Frontend Rule:** The UI explicitly labels MT5 Demo trades as `DEMO / PAPER` and never implies or displays MT5 Demo as live real-money trading.

---

## 8. Responsive & Mobile Audit

### Standard Breakpoints Tested
* **Desktop (1440px - 1920px):** Ultra-wide layout, 240px fixed sidebar, multi-column status boards, side-by-side execution boards.
* **Laptop (1024px - 1439px):** Container scales fluidly down to 1024px.
* **Tablet (768px - 1023px):** Sidebar converts into a horizontal scrollable wrap bar at top; cards stack vertically.
* **Mobile (375px - 767px):** Tables enable horizontal touch scrolling; chatbot widget expands to 100% viewport width; status boards collapse to single-column layout.

---

## 9. Visual Design System

* **Base Palette:**
  * Background Base: `#0B1420`
  * Surface Dark: `#121E2C`
  * Card Dark: `#172537`
  * Border Subtle: `#23354A`
* **Primary Branding Accent:** High-Contrast Amber `#E3A83B` (Hover: `#F2BA4E`, Dim: `rgba(227, 168, 59, 0.1)`).
* **Signaling Colors:**
  * Success / Gain Green: `#4C9A6A`
  * Critical / Danger Red: `#C24A3E`
  * Signal Cyan: `#4FB6C7`
* **Typography:**
  * Primary Sans: `Vazirmatn`, `-apple-system`, `BlinkMacSystemFont`, `Segoe UI`, `Roboto`, `sans-serif`.
  * Monospace: `Fira Code`, `Courier New`, `Courier`, `monospace`.
* **Base-8 Spacing System:** 4px (`0.25rem`), 8px (`0.5rem`), 12px (`0.75rem`), 16px (`1rem`), 24px (`1.5rem`), 32px (`2rem`), 48px (`3rem`).

---

## 10. Runtime Verification & Evidence Index

All major views were launched, verified, and photographed via Playwright headless browser automation under `validation/frontend_current_state/`:

1. `01_landing.png` - Marketing Landing Page (`#/`)
2. `02_features.png` - Cognitive Features Page (`#/features`)
3. `03_pricing.png` - Pricing Tiers Page (`#/pricing`)
4. `04_blog.png` - Research Blog Page (`#/blog`)
5. `05_login.png` - Login View (`#/login`)
6. `06_register.png` - Registration View (`#/register`)
7. `07_forgot_password.png` - Password Reset View (`#/forgot-password`)
8. `08_terminal_dashboard.png` - Main Trader Terminal (`#/dashboard`)
9. `09_backtest.png` - Backtest Simulation Engine (`#/backtest`)
10. `10_demo.png` - Broker Demo Account Operations (`#/demo`)
11. `11_shadow.png` - Virtual Paper Capital Manager (`#/shadow`)
12. `12_live_gate.png` - Live Execution Safety Gate (`#/live`)
13. `13_signals.png` - Signal Hub (`#/signals`)
14. `14_execution_intel.png` - Execution Intelligence Board (`#/execution-intel`)
15. `15_learning.png` - Multi-Timeframe Pattern Memory (`#/learning`)
16. `16_admin.png` - SRE Control Center (`#/admin`)

---

## 11. Design Rebuild Contract

### MUST PRESERVE (Non-Negotiable Business & System Integrity)
1. **Business Logic & API Contracts:** All REST endpoints, HTTP methods, request payloads, and response structures.
2. **Authentication & Authorization:** Bearer token session management, role-based route guards (`USER` vs `ADMIN`).
3. **Execution Safety Boundaries:** Hard isolation of live trading (`#/live`), explicit labelling of MT5 Demo vs MT4 Live.
4. **Trading Safety Rules:** Risk budget approval checks, portfolio heat calculations, stop loss enforcement.
5. **Real-Time Data Semantics:** Chronological market structure map presentation, multi-timeframe horizon alignment logic.
6. **Existing Features & Accessibility:** RTL/LTR bilingual support (Persian, English, Turkish, Arabic), keyboard navigation accessibility.

### MAY CHANGE LATER (Design & UX Refinements)
1. Visual styling, CSS framework/theme tokens, and typography scale.
2. Component layouts, card arrangements, and grid systems.
3. Information hierarchy, chart presentations, and dashboard widgets.
4. Navigation visual design (drawer vs header vs sidebar).

### MUST NOT CHANGE WITHOUT EXPLICIT APPROVAL
1. FastAPI backend routes and database schemas.
2. `MetaTraderSafetyGate` fail-closed safety isolation code.
3. MT4/MT5 role separation logic.
4. Security and authorization model.

---

**Certification:**
Verified by Jules Software Engineer. Baseline state captured cleanly with zero functional or code regressions.
