# YarTrader Frontend Architecture Map (v1.1.0)

This document diagrams the visual layout boundaries, system routing flows, component hierarchy maps, and global state topologies of the YarTrader Client Platform.

---

## Routing Map

The application leverages a lightweight client-side Hash Router based on window state changes (`window.location.hash`). This is ideal for secure, single-origin packaging with zero server redirection hazards.

### Route Configuration Matrix:

| Route Path | Layout Shell | Default Theme | Security Guard Role | Data Endpoints Consumed |
| :--- | :--- | :--- | :--- | :--- |
| `#/` | Public Marketing | Light Editorial | Guest (Unauthenticated) | `/api/public/metrics` |
| `#/features` | Public Marketing | Light Editorial | Guest (Unauthenticated) | None |
| `#/pricing` | Public Marketing | Light Editorial | Guest (Unauthenticated) | `/api/subscription/plans` |
| `#/blog` | Public Marketing | Light Editorial | Guest (Unauthenticated) | `/api/blog` |
| `#/login` | Public Marketing | Light Editorial | Guest (Unauthenticated) | `/api/auth/login` |
| `#/register` | Public Marketing | Light Editorial | Guest (Unauthenticated) | `/api/auth/register` |
| `#/forgot-password`| Public Marketing | Light Editorial | Guest (Unauthenticated) | `/api/auth/forgot-password`|
| `#/dashboard` | Terminal Shell | Dark Institutional | Authenticated User | `/api/user/markets`, `/api/user/signals` |
| `#/execution-intel` | Terminal Shell | Dark Institutional | Authenticated User | `/api/execution/*`, `/api/structure/*`, `/api/liquidity/*`, `/api/pattern/*`, `/api/portfolio/*` |
| `#/learning` | Terminal Shell | Dark Institutional | Authenticated User | `/api/intelligence/learning-matrix` |
| `#/admin` | SRE Admin Shell | Dark SRE | Authenticated ADMIN | `/api/admin/*`, `/api/devops/*`, `/api/validation/*` |

---

## Layout Hierarchy

```
                             ┌────────────────────────┐
                             │       Index.html       │
                             │ (Imports Vazirmatn/CSS)│
                             └───────────┬────────────┘
                                         │
                                         ▼
                             ┌────────────────────────┐
                             │       App.jsx          │
                             │  (Loads I18nProvider)  │
                             └───────────┬────────────┘
                                         │
                 ┌───────────────────────┼───────────────────────┐
                 ▼                       ▼                       ▼
      ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
      │    Public Shell     │ │   Terminal Shell    │ │   SRE Admin Shell   │
      │  (Light Editorial)  │ │ (Dark Institutional)│ │      (Dark SRE)     │
      ├─────────────────────┤ ├─────────────────────┤ ├─────────────────────┤
      │ - Header            │ │ - Sidebar           │ │ - Sidebar           │
      │ - Main Panel        │ │ - Main Panel Grid   │ │ - SRE Header        │
      │ - Footer            │ │ - Chatbot Widget    │ │ - Validation Loop   │
      └─────────────────────┘ └─────────────────────┘ └─────────────────────┘
```

---

## Component Architecture

The physical codebase consists of a centralized layout architecture inside `/trader-terminal/src/`:

```
trader-terminal/src/
├── main.jsx (Render mount)
├── App.jsx (Master Controller, Routing, Presentation views)
├── assets/ (Visual stylesheets and fonts)
├── core/
│   └── config.js (API & WS configurations)
├── services/
│   ├── api.js (Standard HTTP Fetch Client)
│   └── i18n.jsx (Translation provider & RTL controller)
├── store/
│   └── useAuthStore.js (Helper for Session retrieval)
└── components/
    └── common/
        └── Button.jsx (Reusable custom UI button wrapper)
```

### Component Responsibilities:

- **I18nProvider (`services/i18n.jsx`):**
  - Manages translation dictionaries loaded dynamically from `/locales/{lang}.json`.
  - Determines page-level text direction (`rtl` or `ltr`) depending on active locale context (`fa` / `ar` are RTL; `en` / `tr` are LTR).
  - Automatically updates page titles and document base typography styling dynamically.
- **MainApp / Router Panel (`App.jsx`):**
  - Synthesizes the active router hash path, dynamically matching requested paths to the corresponding page shell.
  - Controls dynamic layout theme configuration rules (e.g. switches body styles from light to dark automatically).
  - Handles auth validation gates to redirect unauthenticated or low-privilege sessions immediately.
- **AI Floating Chatbot (`App.jsx`):**
  - Collapsible support panel providing instant explanations from `/api/chat/assistant`.
- **SRE Validation Center (`App.jsx`):**
  - Renders deep diagnostics indicators and triggers real-time test execution loops.

---

## Data Flow Map

The communication topology follows a synchronous unidirectional flow from client action to backend persistence:

```
User Action (e.g., Click "Run SRE Validation")
      │
      ▼
Component Event Handler (e.g., App.jsx: triggerValidation())
      │
      ▼
API Service Layer (services/api.js: apiService.post('/api/validation/run'))
      │
      ▼
HTTP Fetch Client (Appends Bearer token to Authorization headers)
      │
      ▼
FastAPI Gateway Router (web_dashboard.py: /api/validation/run)
      │
      ▼
Backend Execution Engine (Triggers SRE validation & updates runtime logs)
      │
      ▼
JSON/SQLite persistence databases
```

---

## State Flow & Typography Topography

- **Global State Representation:**
  - Standardized as React Hooks situated inside the `App.jsx` container, maintaining reactive inputs, user tokens, language states, and fetched response lists.
  - Localization is supported via context providers (`I18nContext`), and session variables are accessed from localStorage.
- **Design System Typography:**
  - All textual elements utilize proportional font family scaling (`Vazirmatn` for Persian and Arabic; `Segoe UI` or `Roboto` for English and Turkish).
  - Financial, numeric, and telemetry information is styled with monospace typography alongside tabular numerals (`font-variant-numeric: tabular-nums`). This guarantees alignment and prevents layout shifts during real-time updates.

---

## External Integrations

### 1. HTTP REST APIs
- All request endpoints are mapped to the FastAPI backend router (`/api/*`).
- Includes critical security checks: If deployed in a `production` environment, unauthenticated and mock-tokens are rejected immediately with `401` or `403` status codes, protecting admin routes.

### 2. WebSocket Protocol (Future Ready)
- Targeted socket connection point: `${CONFIG.wsBaseUrl}/api/v1/ws`.
- Standardized heartbeat loop is planned to execute a `25s ping-pong` sequence to handle reconnections and prevent socket stagnation.

### 3. Authentication Services
- Implements direct integration with backend PBKDF2 authentication databases (`runtime_logs/auth.json`) with brute-force delay penalty locks.
- Integrates mock buttons for Apple and Google OAuth simulations in non-production development environments.
