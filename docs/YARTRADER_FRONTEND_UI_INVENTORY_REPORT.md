# YarTrader Frontend Complete UI Inventory & Design Mapping Audit

**Date:** August 23, 2026
**Auditor:** Jules — Lead Systems & Frontend Engineer
**Purpose:** Comprehensive visual, product, and component inventory of the current YarTrader frontend (`trader-terminal`) to establish an exact blueprint for redesigning the platform using **shadcn/ui**, **Shadcn Fintech**, **Trading Dashboard**, and **Shadcn Dashboard** design foundations.

---

## 1. Complete Route & Page Inventory

Below is the complete catalog of every active frontend route currently implemented in `trader-terminal/src/App.jsx`:

| Route | Page Name | Purpose | User Type | Status | Main Components | API Dependencies | Current UI Quality | Redesign Priority |
| :--- | :--- | :--- | :--- | :---: | :--- | :--- | :---: | :---: |
| `#/` | **Public Landing Shell** | Platform presentation & key metrics | Anonymous | `ACTIVE` | Header, Sidebar, Card, StatusBoard, StatusItem | `GET /api/public/metrics` | Basic Card Grid | **P1 (High)** |
| `#/features` | **Features Overview** | Explains 4 core intelligence pillars | Anonymous | `ACTIVE` | Card, FeatureGrid, StatusItem | Static Content | Text Cards | **P2 (Medium)** |
| `#/pricing` | **Pricing & Plans** | Subscription plans & plan detail drawer | Anonymous / User | `ACTIVE` | PricingGrid, PlanCard, DetailModalDrawer | `GET /api/subscription/plans` | Functional Grid | **P0 (Critical)** |
| `#/blog` | **Research Blog** | Intelligence research article feed | Anonymous / User | `ACTIVE` | BlogGrid, ArticleCard, TagBadges | `GET /api/blog` | Basic Feed | **P2 (Medium)** |
| `#/login` | **User Authentication** | Email & Social OAuth sign-in form | Anonymous | `ACTIVE` | Form, InputField, SocialBtnContainer, Toast | `POST /api/auth/login`, `/google`, `/apple` | Form Card | **P0 (Critical)** |
| `#/register` | **User Registration** | New user sign-up form | Anonymous | `ACTIVE` | Form, InputField, SocialBtnContainer | `POST /api/auth/register` | Form Card | **P0 (Critical)** |
| `#/forgot-password` | **Password Recovery** | Account recovery dispatch form | Anonymous | `ACTIVE` | Form, InputField, ActionButton | `POST /api/auth/forgot-password` | Form Card | **P1 (High)** |
| `#/dashboard` | **Terminal Command Center** | Primary multi-horizon signals feed & simulator | Authenticated | `ACTIVE` | CommandHeader, HorizonTabs, AssetFilter, SignalGrid, CompoundingCard | `GET /api/user/markets`, `/api/user/signals` | Dense Text Cards | **P0 (Critical)** |
| `#/backtest` | **Backtest Simulation** | Runs backtests & displays history table | Authenticated | `ACTIVE` | FormBar, AuditBoard, BacktestRunsTable | `POST /api/backtest/run`, `GET /api/backtest/history` | Functional Table | **P1 (High)** |
| `#/demo` | **Demo Trading Center** | MT5 Demo account #52961173 order history | Authenticated | `ACTIVE` | StatusBoard, DemoTradesTable | `GET /api/demo/trades`, `/api/demo/report` | Functional Table | **P0 (Critical)** |
| `#/shadow` | **Paper Shadow Manager** | Virtual account ($1,000) positions | Authenticated | `ACTIVE` | StatusBoard, VirtualPositionsTable | `GET /api/shadow/report`, `GET /api/admin/shadow-trades` | Functional Table | **P1 (High)** |
| `#/live` | **Live Trading Safety Gate** | SRE fail-closed safety isolation notice | Authenticated | `HARD-BLOCKED` | DangerHeader, SafetyNoticeBox, StatusBoard | Static / SRE Safety Gate | Static Danger Box | **P0 (Critical)** |
| `#/signals` | **Signal Hub** | Categorized signal feeds (Live, Shadow, Backtest) | Authenticated | `ACTIVE` | SubNavTabs, SignalGrid, QualificationBadge | `GET /api/user/signals` | Basic Grid | **P1 (High)** |
| `#/execution-intel` | **Execution Intelligence** | 5-stage execution board, XAI reasoning trace, Structure map | Authenticated | `ACTIVE` | CascadeHeader, ExecutionBoard, RiskBoard, StructureTable, LiquidityGrid, FractalCard | `GET /api/execution/*`, `/api/structure/*`, `/api/liquidity/*`, `/api/pattern/*` | Rich Data Board | **P0 (Critical)** |
| `#/learning` | **Learning Matrix** | Multi-timeframe pattern performance & detail drawer | Authenticated | `ACTIVE` | ScoreboardBoard, PatternMatrixTable, PatternDetailDrawer | `GET /api/intelligence/learning-matrix` | Rich Matrix | **P1 (High)** |
| `#/admin` | **SRE Admin Control Center** | 8 operational monitoring & management sub-tabs | ADMIN Role | `ACTIVE` | AdminHeader, SubNavTabs, SearchInput, StatusBoard, AuditTable, LogStream | `GET /api/admin/*`, `/api/devops/*`, `/api/validation/*` | Tabbed Control | **P0 (Critical)** |

---

## 2. User Facing Pages Audit

### 2.1 Public Marketing Pages
* **`/` (Landing Page):**
  * *Current Layout:* Global Header + Welcome hero card + 4-card status board (`Active Markets`, `Simulated Trades`, `Platform Uptime`, `PES Compliant`).
  * *Existing Widgets:* Public metrics status grid.
  * *Missing Widgets:* Product Hero Banner, Platform Architecture Pipeline diagram (`Data -> Research -> Signal -> Risk -> Execution`), Interactive Demo Preview, Testimonial/Trust Badges.
  * *Required Redesign Direction:* Rebuild using **Shadcn Fintech Landing Page** layout with dark hero, glowing accent borders (`#E3A83B`), and live metric ticker.
* **`/features` (Features Page):**
  * *Current Layout:* 4-column feature grid text cards.
  * *Required Redesign Direction:* Interactive 4-pillar showcase with tabbed feature previews.
* **`/pricing` (Pricing Page):**
  * *Current Layout:* 3 plan cards + slide-over plan details modal.
  * *Missing Widgets:* Billing interval toggle (Monthly / Annual), feature matrix comparison table, enterprise contact form.
  * *Required Redesign Direction:* Rebuild with **Shadcn Pricing Component** featuring highlighted recommended tier and comparison table.
* **`/docs`, `/faq`, `/contact` (Documentation, FAQ, Contact):**
  * *Status:* **MISSING IN UI.** Need dedicated routes and layouts.

### 2.2 Authentication Pages
* **`/login`, `/register`, `/forgot-password`:**
  * *Current Layout:* Centered single card form with Google & Apple social buttons.
  * *Missing Pages:* Dedicated `/reset-password` view, `/profile` management page, and `/security` (MFA setup & active sessions viewer).
  * *Required Redesign Direction:* Rebuild using **Shadcn Auth Split-Screen Layout** (Left: Financial visual/branding quotes, Right: Clean form card).

### 2.3 User Intelligence Platform Pages
Evaluating all 15 core user platform modules:

1. **Dashboard (`#/dashboard`):** Active. Needs replacement of text signal cards with **TradingView Lightweight Candlestick Chart** and interactive widget grid.
2. **Market Intelligence:** Partial (inside dashboard). Needs dedicated asset watchlist, tick volatility heatmaps, and news feed ticker.
3. **Research:** Partial (inside `#/blog`). Needs institutional daily market research reports view.
4. **Fractal Intelligence:** Partial (card in `#/execution-intel`). Needs dedicated `/fractal` page with multi-scale containment visualizer (x3/x4 families) and historical pattern similarity overlay.
5. **Regime Analysis:** Missing dedicated view. Needs volatility regime gauge and structural transition tracker.
6. **Decision Center:** Active (in `#/execution-intel`). Needs visual XAI decision timeline with evidence badges.
7. **Risk Dashboard:** Active (in `#/execution-intel`). Needs dedicated standalone `/risk` page with drawdown heatmaps, risk budget gauges, and emergency stop button (`/api/risk/emergency_stop`).
8. **Demo Trading:** Active (`#/demo`). Needs live PnL sparklines and MT5 connection health indicator.
9. **Positions:** Partial (split between `#/demo` and `#/shadow`). Needs unified multi-environment Position Lifecycle table.
10. **Trade Journal:** **MISSING.** Needs entry/exit screenshot attachment, MAE/MFE scatter plot, and trade tags.
11. **Performance:** Partial (`compounding` card in `#/dashboard`). Needs equity curve performance chart and Sharpe/Sortino metrics.
12. **Learning Center:** Active (`#/learning`). Needs feedback loop graph and pattern confidence weight adjuster.
13. **Reports:** Partial (in `#/backtest` and `#/demo`). Needs downloadable PDF/CSV audit report center.
14. **Notifications:** **MISSING.** Needs slide-over notification drawer with risk alerts and signal dispatches.
15. **Settings:** **MISSING.** Needs user preferences, language/RTL default, theme preferences, and API keys.

---

## 3. Trading UI Inventory

| Component / Widget | Existing UI (`trader-terminal`) | Target UI (Shadcn Fintech & Trading Patterns) | Reusability / Notes |
| :--- | :--- | :--- | :--- |
| **Candlestick Chart Engine** | ❌ None (Presented as text tables) | **TradingView Lightweight Charts (`lightweight-charts`)** with OB/FVG overlay canvas | **MUST BUILD.** High priority requirement. |
| **Watchlist Bar** | Dropdown asset filter (`Gold`, `BTC`, `Euro`) | Sticky asset ticker bar with real-time price change %, 24h high/low, and mini sparklines | Rebuild as sticky header bar. |
| **Market Signal Cards** | Grid of text boxes with posture & confidence % | Compact Fintech cards with posture badge, entry/TP/SL levels, and mini chart preview | Refactor styling to shadcn card. |
| **Portfolio Risk Board** | Status board with Heat & Budget values | Radial progress gauges for Portfolio Heat & Risk Budget remaining | Upgrade text board to SVG circular gauges. |
| **Position Lifecycle Table** | HTML table with Ticket, Symbol, Side, Price, PnL | Interactive data table with row actions (Close, Modify SL/TP), status badge, and PnL sparkline | Wrap with shadcn data-table. |
| **Order History View** | HTML table in `#/demo` | Filterable order history with execution execution retcode classification | Wrap with shadcn data-table. |

---

## 4. Intelligence UI Inventory

* **Existing Intelligence Components:**
  1. *5-Stage Execution Cascade Header (`#/execution-intel`):* 5-step horizontal status bar tracking Signal -> Decision -> Risk -> Execution -> Result. (High reusability; refactor with Tailwind).
  2. *Reasoning Trace (XAI):* Bullet list of evidence steps explaining trade plan rationale. (Reusable; upgrade with expandable accordion).
  3. *Pattern Similarity Scorecard:* Displays cosine similarity score (e.g. 88.5%), matched pattern ID, and historical success rate. (Reusable; wrap in card).
  4. *Multi-Timeframe Structural Alignment:* Narrative summary text box with synthesis confidence %. (Reusable).
* **Missing Intelligence Components:**
  1. *Multi-Scale Containment Graph:* Visual hierarchy showing lower timeframe candle containment within higher timeframe base structures.
  2. *Regime Shift Gauge:* Visual meter displaying current regime state (`TRENDING_BULLISH`, `RANGING`, `HIGH_VOLATILITY_SWEEP`).

---

## 5. Risk UI Inventory

* **Existing Risk Components:**
  1. *Portfolio Heat & Budget Card (`#/execution-intel`):* Displays heat %, budget remaining, drawdown level, and SRE risk approval boolean.
  2. *Live Trading Hard Safety Gate (`#/live`):* Full-page danger banner with 🛑 warning text explaining fail-closed live trading isolation (`LIVE_TRADING_ENABLED=False`).
* **Target Institutional Risk Dashboard:**
  * Add live Exposure Bar Chart by asset class (Forex, Metals, Crypto).
  * Add Drawdown Limit Progress Bar with alert threshold lines.
  * Add Emergency Stop Action Button with double-confirmation dialog (`POST /api/risk/emergency_stop`).

---

## 6. Position Lifecycle UI Inventory

* **Target 5-Step Position State Model:**
  $$\text{Created} \longrightarrow \text{Validated} \longrightarrow \text{Opened} \longrightarrow \text{Managed} \longrightarrow \text{Closed}$$
* **Current UI State:** Demo trades and Paper Shadow positions render current status (`OPEN` / `CLOSED`) in a flat data table without displaying the intermediate `Validated` or `Managed` transition history.
* **Required Redesign:** Add an expandable row stepper component (`PositionTimelineStepper`) showing exact timestamps and retcodes for each lifecycle phase.

---

## 7. Learning UI Inventory

* **Existing Learning Components (`#/learning`):**
  1. *Learning Scoreboard:* 4 cards displaying Total Patterns Evaluated, Avg Win Rate %, Avg R:R, and OOS Audit Status.
  2. *Multi-Timeframe Pattern Matrix Table:* Data table listing Pattern Key, Name, Sample Count (N), Win Rate %, Avg R:R, MAE, MFE, OOS Status.
  3. *Pattern Detail Drawer:* Slide-over drawer showing evidence summary and confidence multiplier.
* **Target Redesign:** Retain matrix logic; upgrade table with **shadcn DataTable** featuring sortable columns, sample-size filtering ($N \ge 30$), and win-rate color scales.

---

## 8. Admin Control Center Audit (17 Subsections)

Evaluating current coverage across the 17 required admin control plane capabilities:

| Admin Section | Current UI Status | Existing Components in `#/admin` | Missing Capabilities / Redesign Need |
| :--- | :---: | :--- | :--- |
| **1. Overview** | `ACTIVE` | Executive metrics board, System health summary, Trading mode summary | Add live telemetry sparklines & system alert feed |
| **2. Users** | `PARTIAL` | Basic user accounts table (SRE Admin, Elite Trader) | Add user status toggles, password reset trigger, session revocation |
| **3. Roles** | `MISSING` | Role badge shown as text | Add RBAC matrix picker (`Owner`, `Admin`, `Operator`, `Analyst`, `Viewer`) |
| **4. Permissions** | `MISSING` | Inherited statically | Add granular permission checkbox list per role |
| **5. System Health** | `ACTIVE` | Operational status indicators (`API`, `MT5`, `Ingestion`, `Scheduler`) | Add auto-refresh interval toggle & service restart action |
| **6. Runtime Monitoring**| `PARTIAL` | SRE validation runner button & Live log stream box | Add CPU, RAM, Disk I/O, and Worker Queue depth gauge charts |
| **7. Services** | `PARTIAL` | Listed in system status | Add start/stop service control buttons |
| **8. AI Engines** | `MISSING` | Chatbot widget active; admin config missing | Add AI Provider Key Manager (`OpenAI`, `Gemini`, `Claude`, `Ollama`) |
| **9. Data Management** | `ACTIVE` | Tab 3 Data Ingestion stream table (`XAUUSD`, `BTCUSD`, etc.) | Add manual data sync trigger & candle gap repair tool |
| **10. Market Config** | `ACTIVE` | Register new symbol prompt button (`/api/admin/symbols`) | Add active symbol multi-select & timeframe toggle form |
| **11. Risk Config** | `MISSING` | Displayed statically | Add max drawdown limit slider & position sizing cap inputs |
| **12. Execution Settings**| `ACTIVE` | Fail-closed safety gate notice in Tab 4 | Add dynamic slippage & spread filter config inputs |
| **13. Feature Flags** | `MISSING` | Static env variables | Add feature flag toggle switches (`AUTONOMOUS_DEMO_TRADING`, etc.) |
| **14. Notifications** | `MISSING` | Toast notification overlay | Add admin broadcast message publisher & Telegram bot config |
| **15. Audit Logs** | `ACTIVE` | Tab 8 Audit Trail table with detail inspector drawer | Add date range picker, subsystem filter dropdown, CSV export |
| **16. Reports** | `ACTIVE` | Tab 5 Intelligence & SCM reports table | Add PDF report generator & historical report archive download |
| **17. System Settings**| `MISSING` | Theme & language switcher in header | Add global system parameters config form |

---

## 9. Business / SaaS Frontend Inventory

* **Subscription (`/pricing`, `/billing`):**
  * *Pricing:* `#/pricing` renders 3 plan cards with detail modal drawer.
  * *Billing:* **MISSING IN UI.** Needs user `/billing` dashboard showing current plan, renewal date, and invoice history (`GET /api/user/billing/subscription`).
* **Payment & Wallet (`/wallet`):**
  * *Wallet:* **MISSING IN UI.** Needs user `/wallet` view showing account balance, transaction ledger (`GET /api/user/ledger/balance`), and credit deposit form.
  * *Admin Ledger:* Admin API exists (`POST /api/admin/ledger/transaction`), needs admin ledger adjustment form.
* **Business Analytics (`/admin/analytics`):**
  * *Status:* **MISSING IN UI.** Backend revenue analytics endpoint exists (`GET /api/admin/analytics/revenue`), needs visual revenue & user growth charts in Admin Overview.

---

## 10. Component Library Inventory & Replacement Mapping

Cataloging all existing UI elements in `trader-terminal` and mapping them to target **shadcn/ui** components:

| Component Name | File Location | Used In | Reusable As Is? | Target shadcn/ui Component Replacement |
| :--- | :--- | :--- | :---: | :--- |
| `Button` | `src/components/common/Button.jsx` | All forms, modals, action triggers | `YES` | Standardize with `@/components/ui/button` (Tailwind variant props) |
| `Header` | `App.jsx` (inline) | Global layout top bar | `PARTIAL` | `@/components/common/Header` with NavigationMenu & ThemeToggle |
| `Sidebar` | `App.jsx` (inline) | Main container navigation | `PARTIAL` | `@/components/ui/sidebar` with collapsible sections |
| `Card` | `App.jsx` (inline) | Page containers, widgets | `NO` | `@/components/ui/card` (CardHeader, CardTitle, CardContent) |
| `StatusBoard` | `App.jsx` (inline) | Landing, Terminal, Admin | `NO` | Grid wrapper of `@/components/ui/card` metric widgets |
| `StatusItem` | `App.jsx` (inline) | Metric displays | `NO` | Metric Stat Widget component |
| `LogsBox` | `App.jsx` (inline) | Admin Tab 2 System Logs | `YES` | Terminal Log Console component with auto-scroll |
| `BlogGrid` | `App.jsx` (inline) | Pricing, Blog, Signals feed | `NO` | Grid wrapper of shadcn Cards |
| `SubNavTabs` | `App.jsx` (inline) | Signals, Admin tabs | `NO` | `@/components/ui/tabs` (TabsList, TabsTrigger, TabsContent) |
| `DrawerModal` | `App.jsx` (inline) | Pricing & Pattern details | `NO` | `@/components/ui/sheet` or `@/components/ui/dialog` |
| `NotificationToast` | `App.jsx` (inline) | Global toast alerts | `NO` | `@/components/ui/toast` / `@/components/ui/toaster` (Sonner) |
| `ChatbotWidget` | `App.jsx` (inline) | Fixed bottom-right chatbot | `YES` | Refactor into modular `FloatingAIAssistant` component |

---

## 11. Current Theme Audit

### 11.1 Color Palette Audit (CSS Variables in `globals.css`)
* **Primary Branding:** Amber `#E3A83B` (Primary), `#F2BA4E` (Hover), `rgba(227, 168, 59, 0.12)` (Dim). **KEEP.** Perfect institutional accent.
* **Background & Surfaces:** `#0B1420` (Base Dark), `#121E2C` (Surface), `#172537` (Card), `#23354A` (Subtle Border). **KEEP.** Provides excellent contrast for trading terminals.
* **Signaling Colors:** `#4C9A6A` (Success/Buy Green), `#C24A3E` (Critical/Sell Red), `#4FB6C7` (Signal Cyan), `#E3A83B` (Warning Amber). **KEEP.** Muted institutional scale prevents visual fatigue.

### 11.2 Typography & Spacing Audit
* **Fonts:** `Vazirmatn` (Sans-serif for Persian/Arabic/English) and `Fira Code` (Tabular monospace for prices/numbers). **KEEP.**
* **Financial Numbers:** `font-variant-numeric: tabular-nums` enforced across all tables and stat values. **KEEP.**
* **Spacing:** Base-8 spacing scale (`--space-1` to `--space-10`). Convert to standard Tailwind spacing classes (`p-2`, `p-4`, `p-6`).

### 11.3 Theme Modes & Localization
* **Dark Mode:** Default terminal theme. Fully supported.
* **Light Mode:** Supported via `body.light-theme` class with high-contrast editorial colors. **KEEP.**
* **RTL Support:** Enforced dynamically via `document.body.dir = isRTL ? 'rtl' : 'ltr'`. **KEEP.**

---

## 12. Template Migration Mapping

Direct mapping of existing YarTrader pages to target **shadcn/ui** and **Shadcn Fintech** design templates:

```
CURRENT FRONTEND PAGE                  TARGET REDESIGNED PAGE & TEMPLATE INSPIRATION
─────────────────────                  ──────────────────────────────────────────────
1. Landing Page (#/)                ──► YarTrader Public Portal
                                        Inspired by: Shadcn Fintech Hero & Metric Grid

2. Terminal (#/dashboard)           ──► YarTrader Autonomous Command Center
                                        Inspired by: Trading Dashboard + Lightweight Charts

3. Execution Intel (#/exec-intel)   ──► Institutional Execution & XAI Board
                                        Inspired by: Shadcn Dashboard Analytics + Stepper

4. Backtest (#/backtest)            ──► Quantitative Backtest Lab
                                        Inspired by: Shadcn Data Table + Parameter Sidebar

5. Demo Trading (#/demo)            ──► MT5 Broker Demo Terminal (#52961173)
                                        Inspired by: Shadcn Fintech Order Book & History

6. Shadow Trading (#/shadow)        ──► Virtual Capital Paper Manager ($1,000)
                                        Inspired by: Shadcn Fintech Portfolio Manager

7. Learning Matrix (#/learning)     ──► Pattern Memory & OOS Audit Matrix
                                        Inspired by: Shadcn Dashboard Data Matrix

8. Admin Control (#/admin)          ──► SRE Control Plane & Telemetry Center
                                        Inspired by: Shadcn Admin Dashboard (8 Sub-tabs)

9. Pricing (#/pricing)              ──► SaaS Subscription & Entitlements Portal
                                        Inspired by: Shadcn Pricing Cards & Feature Table

10. Auth (#/login, #/register)      ──► Secure Gateway & Identity Portal
                                        Inspired by: Shadcn Split-Screen Auth Card
```

---

## 13. Recommended New Navigation Structure

To accommodate all missing pages while maintaining clean separation between Public, User Trading, and Admin Control Plane, the following navigation tree is recommended:

```
YarTrader Platform Navigation Hierarchy
├── 🌐 Public Portal (Light Editorial / Dark Theme)
│   ├── /                      (Home / Platform Overview)
│   ├── /features              (4-Pillar Features)
│   ├── /pricing               (Subscription Plans & Comparison)
│   ├── /blog                  (Research Articles)
│   ├── /docs                  (API & System Documentation)
│   ├── /faq                   (Frequently Asked Questions)
│   └── /contact               (Contact & Enterprise Sales)
│
├── 🔐 Auth Portal
│   ├── /login                 (User Sign In)
│   ├── /register              (User Sign Up)
│   ├── /forgot-password       (Password Recovery)
│   └── /reset-password        (Password Reset)
│
├── 🏛️ User Financial Intelligence Platform (Dark Terminal Shell)
│   ├── /dashboard             (Command Center + Candlestick Chart)
│   ├── /signals               (Multi-Horizon Signal Hub)
│   ├── /execution-intel       (5-Stage Cascade & XAI Rationale)
│   ├── /fractal               (Multi-Scale x3/x4 Fractal Visualizer)
│   ├── /regime                (Market Regime Analysis)
│   ├── /risk                  (Portfolio Risk Dashboard & Emergency Stop)
│   ├── /trading/demo          (MT5 Demo Account #52961173)
│   ├── /trading/shadow        (Paper Execution Manager)
│   ├── /trading/backtest      (Simulation Runner & History)
│   ├── /positions             (Unified Position Lifecycle Stepper)
│   ├── /journal               (Trade Journal & MFE/MAE Scatter Plot)
│   ├── /learning              (Pattern Memory & OOS Audit)
│   ├── /reports               (Downloadable CSV/PDF Reports)
│   ├── /billing               (Subscription & Payment Invoices)
│   ├── /wallet                (User Credit Ledger & Balance)
│   ├── /support               (Support Tickets & Help Center)
│   └── /settings              (User Profile, Preferences & Security)
│
└── 🛡️ SRE Admin Control Center (Admin Sidebar Shell)
    ├── /admin/overview        (Executive Overview & Live Telemetry)
    ├── /admin/users           (User Account & RBAC Role Manager)
    ├── /admin/system          (Subsystem Health & SRE Validation Runner)
    ├── /admin/data            (Real-Time Ingestion Pipeline Monitor)
    ├── /admin/trading-safety  (Fail-Closed Safety Gate & Risk Bounds)
    ├── /admin/intelligence    (Model Performance & SCM Reports)
    ├── /admin/ai-engines      (AI Provider Key Manager & Prompt Config)
    ├── /admin/cms             (Blog, Docs & Announcement Publisher)
    ├── /admin/errors          (System Error Feed & Exception Log)
    └── /admin/audit           (Chronological Audit Trail & Event Inspector)
```

---

*Blueprint report certified by Jules — Lead Systems & Frontend Engineer.*
*YarTrader Autonomous Financial Intelligence Platform.*
