# YarTrader Frontend Discovery Report (v1.1.0)

## Current Framework
- **Framework Name & Version:** React 18.3.1 (using Vite 5.4.1 for compilation and bundling).
- **Rendering Approach:** Pure Client-Side Rendering (CSR).
  - All pages and sections are compiled into static assets (`dist/assets/index-*.js` and `dist/assets/index-*.css`) loaded by `/trader-terminal/index.html`.
  - The client side utilizes native hash-based routing (`window.location.hash`) for view switching, which ensures 100% same-origin safety and simple deployment integration with standard Nginx or backend static-file routers without fallback redirects.
- **Build Tooling:** Vite (v5.4.1 as specified in `package.json`). No legacy Webpack or custom config layers exist, guaranteeing optimized ES build steps and super-fast Hot Module Replacement (HMR).

---

## Build Pipeline
- **Development Command:** `npm run dev` (spins up local Vite development server under port `5173`).
- **Production Build Command:** `npm run build` (compiles and bundles optimal vendor and asset chunks into the `dist/` directory).
- **Preview Command:** `npm run preview` (runs local server to preview production-built static assets).
- **Environment Configuration:**
  - Standard `.env` or system variables loaded via Vite's `import.meta.env`.
  - The API Base URL is dynamically bound inside `/trader-terminal/src/core/config.js` via `import.meta.env.VITE_API_BASE_URL` with a standard fallback to `window.location.origin` (ensuring same-origin configuration is automatically applied when deployed as a unified backend bundle).
  - Trailing slashes are programmatically sliced off to prevent API endpoint path-joining bugs.

---

## Application Entry Points
- **Main Application Entry:** `/trader-terminal/src/main.jsx`
  - Mounts the react root onto the `<div id="root">` element inside `/trader-terminal/index.html`.
- **Routing Entry & State:** `/trader-terminal/src/App.jsx`
  - Directs hash-routing flow using stateful tracking (`hash` hook synchronized with `window.location.hash`).
  - Implements dynamic conditional routing layouts based on hash patterns (e.g., `#/` for home, `#/dashboard` for terminal, etc.).
- **Providers:**
  - `I18nProvider` (defined in `/trader-terminal/src/services/i18n.jsx`): Wraps the entire application tree, providing translations (`t`), language state (`lang`), direction classes (`rtl` or `ltr`), and standard locale dictionaries fetched dynamically from `/locales/{lang}.json`.
- **Global Layouts:**
  - Implements a modern dual-sidebar/main-panel layout within `App.jsx`.
  - Features high-contrast typography, brand styling headers, a dynamic status bar, and collapsible chatbot interfaces.
- **Configuration Files:**
  - `/trader-terminal/src/core/config.js`: Establishes basic environment bindings (`apiBaseUrl`, `wsBaseUrl`) with trailing slash sanitization.

---

## API Integration Layer
- **API Clients & HTTP Libraries:**
  - Standard native `fetch` client wrapped inside `/trader-terminal/src/services/api.js` under `apiService`.
  - It exposes simple `get(endpoint)` and `post(endpoint, data)` wrappers.
- **Authentication Handling:**
  - Requests are automatically appended with the Bearer JWT token via the `getAuthHeaders()` helper reading `localStorage.getItem('yartrader_token')`.
  - If a token is not present, the `Authorization` header is cleanly excluded.
- **Data Fetching Patterns:**
  - Triggered inside React `useEffect` hooks linked to changes in the active router `hash` and dependencies like `activeHorizon` and `selectedAsset`.
  - Data points are subsequently stored in React state Hooks within `App.jsx`.
- **Existing API Contracts Consumed:**
  - `POST /api/auth/login` - Submits credential object and retrieves authentication payload containing `session_token`, user info, and role.
  - `POST /api/auth/register` - Registers a new user.
  - `POST /api/auth/forgot-password` - Requests reset password email.
  - `POST /api/auth/logout` - Logs out current user session.
  - `GET /api/public/metrics` - Obtains platform public status (active markets, historical trades, uptime).
  - `GET /api/subscription/plans` - Pulls monetization subscription tiers.
  - `GET /api/blog` - Fetches marketing and research blog articles.
  - `GET /api/user/markets` - Lists active markets.
  - `GET /api/user/signals?horizon={horizon}` - Retrieves signals filtered by horizon values.
  - `GET /api/intelligence/learning-matrix` - Obtains pattern outcomes and sample sizing matrices.
  - `GET /api/execution/plans` - Obtains passive advisory plans.
  - `GET /api/execution/confidence` - Obtains confidence metrics.
  - `GET /api/execution/reasoning` - Obtains XAI logic explanations.
  - `GET /api/structure/map` - Retrieves Swing Highs/Lows list.
  - `GET /api/structure/alignment` - Retrieves trend alignment state.
  - `GET /api/structure/narrative` - Retrieves text-based SCM synthesis narrative.
  - `GET /api/liquidity/map` - Obtains Order Block and FVG details.
  - `GET /api/liquidity/events` - Retrieves recent order block events.
  - `GET /api/pattern/similarity` - Obtains matched cognitive pattern details.
  - `GET /api/portfolio/risk` - Obtains overall heat, exposure limits, and SRE override checks.
  - `GET /api/portfolio/exposure` - Obtains current asset concentrations.
  - `GET /api/admin/symbols` - (Admin only) Lists raw registered symbol list.
  - `POST /api/admin/symbols` - (Admin only) Registers new custom symbols with timeframe parameters.
  - `GET /api/admin/reports` - (Admin only) Obtains deep SRE multi-timeframe analytics report.
  - `GET /api/devops/status` - (Admin only) System trace and connection health.
  - `GET /api/devops/metrics` - (Admin only) Process CPU/RAM.
  - `GET /api/validation/history` - (Admin only) SRE validation suite outcomes.
  - `GET /api/validation/status` - (Admin only) Real-time SRE status & metrics alignment.
  - `POST /api/validation/run` - (Admin only) Triggers manual execution loop.
  - `GET /api/shadow/metrics` - (Admin only) Obtains shadow trading outcome states.
- **Error Handling Approach:**
  - For `GET` requests: If response is not OK, raises an error string stating `API Error: status - statusText`.
  - For `POST` requests: Parses the JSON response; if not OK, attempts to extract `.detail` from payload to present customized validation messages before falling back to generic status codes.
  - Error messages are caught inside UI handlers and pushed onto the unified slide-in visual toast notification.

---

## Existing Dependencies
- **Core Engine Dependencies:**
  - `react` (^18.3.1) - UI library providing core virtual DOM elements and components.
  - `react-dom` (^18.3.1) - Renders Virtual DOM to the browser surface.
- **Development Tooling:**
  - `vite` (^5.4.1) - Hot-reloading development and high-efficiency compiler bundler.
  - `@vitejs/plugin-react` (^4.3.1) - React framework compilation plugin.
  - `typescript` (^5.5.3) - Stored in devDependencies for prospective typings compilation (unintegrated in runtime bundle).

---

## Current Problems & Technical Debt
1. **Lack of State Management Tooling:**
   - There is no central state management framework (e.g., Zustand or Redux). All states are held inside `App.jsx`, leading to a giant, single source file (800+ lines of markup and hooks) that is hard to audit, test, and maintain.
2. **Synchronous/Imperative Routing:**
   - The application lacks an enterprise router library (e.g., React Router). It uses state-tracked window hash listening which increases structural vulnerability to navigation shifts.
3. **No Charting Libraries Integrated:**
   - The UI does not contain active price graphs or chronological chart representations. All financial metrics are rendered via standard tabular text displays or simplified vertical indicators.
4. **No Real-Time WebSocket Listener Initialized:**
   - Despite `CONFIG.wsBaseUrl` being defined, the React client lacks an active WebSocket engine. It fetches information on page load or router hash shifts purely via HTTP-polling/imperative GET fetch cycles. This leads to stale data and limits live streaming tick visuals.
5. **No Robust Form Validation:**
   - Login and Register cards use basic HTML constraints. There is no client-side form schema validation engine (such as Zod).

---

## Frontend Backend Integration Analysis

### 1. Backend Connection Points
- **Base URLs:** Configured in `trader-terminal/src/core/config.js` pointing to `import.meta.env.VITE_API_BASE_URL` with auto-fallback to origin. It slices off trailing slashes so routes like `${CONFIG.apiBaseUrl}/api/user/markets` do not result in double slashes.
- **Client Configuration:** Centralized in `/trader-terminal/src/services/api.js` using `apiService`. It encapsulates common header insertions, specifically Bearer token generation.
- **Environment variables:** Built via Vite prefix standard (`VITE_`).

### 2. Data Contracts (DTO Structures)
- **Authentication Payload:**
  - Request: `{ "email": "...", "password": "..." }`
  - Response: `{ "session_token": "...", "role": "...", "user": { "name": "...", "role": "..." } }` (or similar aliases).
- **Public Metrics Contract:**
  - Response: `{ "active_markets_count": 30, "historical_simulated_trades": "125k+", "platform_uptime_pct": "99.9" }`
- **Signals Feed Contract:**
  - Response: List of `{ "symbol": "XAUUSD", "timeframe": "H1", "confidence": 88, "posture": "BULLISH", "entry_zone": "...", "target_zone": "...", "invalidation_level": "...", "narrative": "..." }`
- **SRE Validation Status:**
  - Response: `{ "passed": 120, "failed": 0, "skipped": 5, "warnings": 2, "readiness_score": "100.0%", "phase": "SUCCESS", "component": "PredictiveShadowEngine", "test": "...", "logs": [...] }`

### 3. Frontend Data Consumption
- **App.jsx** serves as the primary and only container. All REST calls are fired inside unified page-level `useEffect` callbacks triggered by navigation updates or filter adjustments.
- **Loading states:** Represented on the translation level via `loading` variables but lack discrete component skeleton overlays.
- **Data refresh patterns:** Highly manual. Fired only on route shifts or clicking interactive triggering buttons (such as 'Run Validation').

### 4. Authentication Integration
- **Session Handling:** Stores `yartrader_token`, `yartrader_role`, and `yartrader_name` inside `localStorage`.
- **Protected routes:** Guarded in `App.jsx` by checking if `token` is set prior to rendering `#/dashboard`, `#/execution-intel`, `#/learning`, or `#/admin`. Unauthorized attempts trigger instant redirection back to `#/login` with warning alerts.

### 5. Real-Time Integration Gaps
- **Missing WebSocket Implementation:** While `wsBaseUrl` is defined, the frontend currently does not instantiate any `new WebSocket` connections. Real-time telemetry is lacking, relying entirely on REST polling.

---

## Recommended Frontend Backend Integration Plan

> **⚠️ CRITICAL WARNING: This plan is strictly for future architectural reference and preparation. DO NOT write code, implement connections, or modify files during Phase 0.**

1. **Implement Central Zustand Stores:**
   - Establish `useAuthStore.js` to manage session token validation, permissions, and roles.
   - Establish `useTerminalStore.js` to handle real-time streaming tickers, selected market contexts, and multi-horizon alignments.
   - Establish `useWebSocketStore.js` to govern connection state, reconnect timeouts, ping/pong validation, and event routing.

2. **Establish the WebSocket Connection Core:**
   - Integrate native `WebSocket` logic inside a decoupled hook or middleware layer.
   - Subscribe to the backend stream at `${CONFIG.wsBaseUrl}/api/v1/ws`.
   - Dispatch events like `market_update` and `signal_update` directly to Zustand store slices to update UI values instantly without layout stuttering.

3. **Integrate TradingView Lightweight Charts:**
   - Integrate the pure-price action charting library for gold, bitcoin, and euro symbols.
   - Fetch historical candle datasets via a standard HTTP REST API, and feed real-time ticks straight from the WebSocket connection.

4. **Add Standard DTO Validation Layer:**
   - Use strict TypeScript typings or Zod schemas to parse and validate incoming REST and WebSocket payloads at runtime, failing safely when an unexpected API structure is detected.
   - Gracefully route unhandled API contract changes into warning notifications to protect the terminal interface from crashes.
