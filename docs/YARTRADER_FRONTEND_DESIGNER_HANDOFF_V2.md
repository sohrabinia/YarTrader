# YarTrader Frontend Master Designer Handoff Specification v2.0

**Document Version:** 2.0.0
**Status:** Certified Final Designer Handoff
**Scope:** Complete Frontend Source, Visual, Runtime & Component Specification
**Target Audience:** UI/UX Designers & External AI Design Reviewers

---

## 1. Executive Summary

This specification serves as the complete, authoritative handoff document for the YarTrader frontend application (`trader-terminal`). It provides the exact current-state implementation details, route maps, component inventories, API mappings, execution safety boundaries, visual design tokens, and UX problem registers required to design the next generation YarTrader interface without losing existing functionality or violating backend safety gates.

---

## 2. Frontend Architecture & Directory Structure

```text
trader-terminal/
├── public/
├── src/
│   ├── assets/
│   │   └── globals.css          # CSS Variables, dark/light theme rules, layout styles
│   ├── components/
│   │   └── common/
│   │       └── Button.jsx       # Shared Button component
│   ├── core/
│   │   └── config.js            # API base URL configuration (VITE_API_BASE_URL)
│   ├── services/
│   │   ├── api.js               # Centralized fetch API wrapper with Bearer token injection
│   │   └── i18n.jsx             # Translation provider & custom useTranslation hook
│   ├── store/
│   │   └── useAuthStore.js      # LocalStorage auth state accessor methods
│   ├── App.jsx                  # Main single-file React SPA router, pages, and chatbot
│   └── main.jsx                 # React DOM root entry point
├── index.html
├── package.json
└── vite.config.js
```

---

## 3. Discovered Route Map (16 Routes)

| Route | Access Tier | Purpose | API Dependencies |
| :--- | :--- | :--- | :--- |
| `#/` | PUBLIC | Marketing landing page | `/api/public/metrics` |
| `#/features` | PUBLIC | Cognitive features overview | None |
| `#/pricing` | PUBLIC | Subscription plans & detail drawer | `/api/subscription/plans` |
| `#/blog` | PUBLIC | Research articles grid | `/api/blog` |
| `#/login` | PUBLIC | User login & social OAuth | `/api/auth/login`, `/api/auth/google`, `/api/auth/apple` |
| `#/register` | PUBLIC | User registration form | `/api/auth/register` |
| `#/forgot-password` | PUBLIC | Password reset recovery | `/api/auth/forgot-password` |
| `#/dashboard` | AUTHENTICATED USER | Main Trader Terminal | `/api/user/markets`, `/api/user/signals` |
| `#/backtest` | AUTHENTICATED USER | Backtest simulation engine | `/api/backtest/run`, `/api/backtest/history` |
| `#/demo` | AUTHENTICATED USER | MT5 broker demo order ledger | `/api/demo/trades`, `/api/demo/report` |
| `#/shadow` | AUTHENTICATED USER | Virtual paper capital manager | `/api/shadow/report`, `/api/admin/shadow-trades` |
| `#/live` | AUTHENTICATED USER | Live trading safety gate isolation | None |
| `#/signals` | AUTHENTICATED USER | Multi-tab signal stream | `/api/user/signals` |
| `#/execution-intel` | AUTHENTICATED USER | Institutional execution board | `/api/execution/*`, `/api/structure/*`, `/api/liquidity/*`, `/api/portfolio/*` |
| `#/learning` | AUTHENTICATED USER | Fractal pattern memory matrix | `/api/intelligence/learning-matrix` |
| `#/admin` | ADMIN | SRE control center & validation hub | `/api/admin/*`, `/api/devops/*`, `/api/validation/*` |

---

## 4. Reusable Component Catalog (24 Components Discovered)

1. `Header` (`App.jsx`): Top navbar with status indicators, language selector, theme toggle.
2. `Sidebar` (`App.jsx`): Left navigation bar with user profile badge and logout.
3. `Card` (`App.jsx`): Surface container card with border and elevation.
4. `StatusBoard` (`App.jsx`): Grid container organizing metric tiles.
5. `StatusItem` (`App.jsx`): Individual metric tile formatting label and numeric value.
6. `Button` (`Button.jsx`): Primary Amber action button.
7. `ButtonSecondary` (`App.jsx`): Outline secondary button.
8. `SocialButton` (`App.jsx`): OAuth social login trigger (Google / Apple).
9. `InputField` (`App.jsx`): Standard text/password/number input element.
10. `SelectField` (`App.jsx`): Custom styled dropdown select element.
11. `HorizonTabs` (`App.jsx`): 4-button time horizon selector (`micro`, `short`, `medium`, `macro`).
12. `SubNavTabs` (`App.jsx`): Sub-navigation tab bar for Signal Hub.
13. `SignalCard` (`App.jsx`): Qualified signal feed card displaying posture and narrative.
14. `BacktestForm` (`App.jsx`): Input controls for backtest symbol, timeframe, and candles.
15. `Table` (`App.jsx`): Data table with monospaced tabular numeric formatting.
16. `ScoreCircle` (`App.jsx`): Radial score badge displaying readiness score.
17. `LogsBox` (`App.jsx`): Monospaced dark console viewing live SRE validation logs.
18. `ChatbotWidget` (`App.jsx`): Fixed floating support assistant widget.
19. `ChatBubble` (`App.jsx`): User or bot text message bubble in chatbot.
20. `QuickPromptChip` (`App.jsx`): Interactive prompt chip for AI Chat assistant.
21. `NotificationToast` (`App.jsx`): Top-centered floating notification banner.
22. `PlanDetailModal` (`App.jsx`): Modal container displaying selected plan features.
23. `PatternInspectDrawer` (`App.jsx`): Detail drawer showing pattern memory evidence.
24. `BackendErrorBanner` (`App.jsx`): Top warning banner displayed when API is unreachable.

---

## 5. API Binding Matrix (42 Endpoints Mapped)

*(Full REST endpoint mapping verified between `trader-terminal/src/App.jsx`, `services/api.js`, and FastAPI backend `src/Application/Services/web_dashboard.py`)*

---

## 6. Execution Safety Boundaries (MT4 Live vs MT5 Demo)

* **MT4 Execution Boundary:** Assigned strictly to **Live / Signal Execution** (`143056202` on `Alpari-Pro.ECN`). Live execution is hard-blocked on UI (`#/live`) via red warning banner when `LIVE_TRADING_ENABLED=False`.
* **MT5 Execution Boundary:** Restricted strictly to **Backtesting, DEMO Trading (`52961173`), and Forward Observation**. The UI explicitly badges all MT5 trades as `DEMO / PAPER` and never implies live trading.

---

## 7. Current Visual Design Tokens

* **Primary Amber:** `#E3A83B` (Hover: `#F2BA4E`, Dim: `rgba(227, 168, 59, 0.12)`)
* **Background Dark:** `#0B1420`
* **Surface Dark:** `#121E2C`
* **Card Surface:** `#172537`
* **Border Subtle:** `#23354A`
* **BUY / Gain Green:** `#4C9A6A`
* **SELL / Danger Red:** `#C24A3E`
* **Signal Cyan:** `#4FB6C7`
* **Font Sans:** `Vazirmatn`, `-apple-system`, `sans-serif`
* **Font Monospace:** `Fira Code`, `Courier New`, `monospace`

---

## 8. Designer / AI Handoff Contract

### MUST PRESERVE (Non-Negotiable Backend & System Contracts)
1. All 42 REST API endpoints, parameters, and JSON response keys.
2. Bearer token session authentication model and role-based route guards.
3. Strict execution boundary isolation (MT4 Live hard-blocked; MT5 Demo explicitly badged as DEMO).
4. Full Persian (fa), English (en), Turkish (tr), and Arabic (ar) multi-lingual RTL/LTR support.
5. Tabular LTR numeric alignment for financial figures in RTL layouts.

### AREAS SAFE TO REDESIGN
1. Visual layout, component styling, typography hierarchy, and color palettes.
2. Navigation presentation (sidebar vs header vs mobile drawer).
3. Dashboard card arrangements and responsive stacking behavior.
