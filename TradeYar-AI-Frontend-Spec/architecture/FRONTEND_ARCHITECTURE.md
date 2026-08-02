# FRONTEND_ARCHITECTURE.md — Frontend Architecture & Implementation Roadmap

This document describes the core architecture, screen inventories, component relationships, data flow state strategies, and the implementation roadmap for the TradeYar AI Client Platform.

---

## 🏗️ 3-Shell Layout (Separation of Concerns)

To support distinct audiences with completely different security, visual, and operational requirements, TradeYar AI operates three strictly partitioned layout shells within the SPA:

```
                          ┌────────────────────────┐
                          │    Single Page App     │
                          │   (TradeYar AI v3.5)   │
                          └───────────┬────────────┘
                                      │
         ┌────────────────────────────┼────────────────────────────┐
         ▼                            ▼                            ▼
┌──────────────────┐        ┌──────────────────┐         ┌──────────────────┐
│  Public Shell    │        │  Terminal Shell  │         │    SRE Shell     │
│   (Marketing)    │        │     (Trader)     │         │    (Console)     │
├──────────────────┤        ├──────────────────┤         ├──────────────────┤
│ - Landing Page   │        │ - Market Matrix  │         │ - API Telemetry  │
│ - Long-form Blog │        │ - Multi-TF View  │         │ - SCM Services   │
│ - Pricing/Plans  │        │ - Shadow Engine  │         │ - Memory Audit   │
│ - Auth (Log/Reg) │        │ - AI Assistant   │         │ - Incident Logs  │
└──────────────────┘        └──────────────────┘         └──────────────────┘
```

### 1. The Public Marketing Website (Public Shell)
- **Primary Endpoint:** `/`, `/features`, `/pricing`, `/blog`
- **Language/Localization:** Four-language localization support (English, Persian, Turkish, Arabic). RTL/LTR dynamic rendering (Vazirmatn for Persian/Arabic, standard sans-serif for English/Turkish).
- **Authentication:** Unauthenticated guest users are allowed full browsing, cookie GDPR consent flow, and a guest/visitor "Demo Mode".

### 2. The Customer Financial Intelligence Terminal (Terminal Shell)
- **Primary Endpoint:** `/dashboard/*`
- **Theme:** High-fidelity, Bloomberg/TradingView style dark theme.
- **Components:** Interactive multi-timeframe grid (M1, M5, M15, H1, H4, D1, W1, MN1), floating/collapsible Persian/English AI Assistant chatbot widget, Virtual Position Manager, Shadow Trading execution telemetry.
- **Access Control:** Guarded by `AuthService` session token verification (roles: USER, PRO, PREMIUM, ADMIN).

### 3. The SRE Admin Control Console (Admin/SRE Shell)
- **Primary Endpoint:** `/admin/*`
- **Theme:** Utilitarian dark mode with high contrast neon statuses (Active, Degraded, Critical).
- **Components:** System trace monitoring, live MT5 connection health tracker, background workers monitoring (Research, Intelligence, Shadow Workers), CPU/RAM telemetry, database file parser status (`auth.json` and memory recovery), limit controls (max dynamic assets limit: 30 symbols ceiling).
- **Access Control:** Restricted to SRE Operator and Admin roles via JWT headers and PBKDF2 administrative credential locks.

---

## 📋 PART 1 — Screen & Capabilities Mapping

Below is the complete mapping of every visual screen to its respective APIs, WebSocket events, security roles, permissions, and constituent design system components:

### 1. Unified Trader Terminal (`/dashboard`)
*   **API Endpoints:**
    *   `GET /api/user/markets` (Lists active symbols)
    *   `GET /api/user/signals?symbol=XAUUSD` (Extracts current multi-TF posturing)
*   **WebSocket Events:** `market_update`, `signal_update`
*   **User Roles & Permissions:** `USER`, `PRO`, `PREMIUM`, `ADMIN` (Access read-only analytical signals and market streams)
*   **Required Components:** `SymbolSelector`, `MultiTimeframeGrid`, `SignalBadge`, `LanguageSelector`, `AssistantChatbot`

### 2. Research Intelligence Dashboard (`/dashboard/research`)
*   **API Endpoints:**
    *   `GET /api/research/latest` (Retrieves latest reports and candles)
    *   `GET /api/research/history` (Historical observations catalog)
    *   `GET /api/research/health` (Statistical QC engine health stats)
*   **WebSocket Events:** `market_update`
*   **User Roles & Permissions:** `USER` (Standard), `PRO` (Advanced details), `PREMIUM`, `ADMIN`
*   **Required Components:** `FeatureExtractionTable`, `StatisticalQCCard`, `PatternDiscoveryMatrix`, `LookbackBoundsMeter`

### 3. Strategy Intelligence Panel (`/dashboard/strategy`)
*   **API Endpoints:**
    *   `POST /api/backtest/run` (Initiates simulated backtest parameter check)
    *   `GET /api/replay/learning-status` (Chronological strategy progress metrics)
*   **WebSocket Events:** None
*   **User Roles & Permissions:** `PRO`, `PREMIUM`, `ADMIN` (Hidden or blocked for basic `USER` role)
*   **Required Components:** `StrategyConfidenceMeter`, `BacktestConfigForm`, `HistoricalPerformanceChart`, `EvaluationResultCard`

### 4. Risk Intelligence Guard (`/dashboard/risk`)
*   **API Endpoints:**
    *   `GET /api/portfolio/risk` (Calculates active exposure values)
    *   `GET /api/portfolio/exposure` (Drawdown levels and constraints)
*   **WebSocket Events:** `shadow_update`
*   **User Roles & Permissions:** `USER`, `PRO`, `PREMIUM`, `ADMIN` (Ensures clients see safety boundary checks)
*   **Required Components:** `PortfolioRiskScorecard`, `ExposureLimitsMeter`, `RiskPolicyChecklist`, `WarningNotificationBanner`

### 5. Execution Passive Advisor (`/dashboard/execution`)
*   **API Endpoints:**
    *   `GET /api/execution/plans` (Retrieves passive execution advisory logs)
    *   `GET /api/execution/confidence` (Confidence metrics score)
    *   `GET /api/execution/reasoning` (XAI logic)
    *   `GET /api/shadow/metrics` (Virtual portfolio P&L metrics)
*   **WebSocket Events:** `shadow_update`
*   **User Roles & Permissions:** `USER`, `PRO`, `PREMIUM`, `ADMIN` (Advisory-only. Strictly passive with zero order execution capabilities)
*   **Required Components:** `AdvisoryPlanCard`, `ShadowPositionsTable`, `ExecutionSimulator`, `AuditTrailTimeline`

### 6. Learning Intelligence Dashboard (`/dashboard/learning`)
*   **API Endpoints:**
    *   `GET /v1/dashboard/cognitive` (Provides experience consolidation rates, pattern memories, concepts learned)
    *   `GET /api/replay/training-monitor` (Training loop telemetry)
*   **WebSocket Events:** None
*   **User Roles & Permissions:** `USER`, `PRO`, `PREMIUM`, `ADMIN`
*   **Required Components:** `ExperiencePromotionPipeline`, `PatternMemoryMap`, `ConceptsLearnedList`, `ConfidenceDecayChart`

### 7. SRE Admin Dashboard (`/admin`)
*   **API Endpoints:**
    *   `GET /api/v1/health` (Process liveness, API response states, dependency check)
    *   `GET /api/devops/metrics` (CPU/RAM telemetry, active worker counts)
    *   `POST /api/control` (Worker restart, backup triggers)
    *   `POST /api/risk/emergency_stop` (Immediate virtual risk shutdown)
*   **WebSocket Events:** `sre_telemetry`, `incident_alert`
*   **User Roles & Permissions:** `SRE_OPERATOR`, `ADMIN` strictly (Guarded by PBKDF2 authentication credentials; hidden from standard traders)
*   **Required Components:** `SreTelemetryCard`, `WorkerLifecycleTracker`, `EmergencyStopButton`, `SreAuditTimeline`, `IncidentCard`

---

## 🗂️ PART 2 — Component Hierarchy

The architectural rendering of component relationships:

```
┌────────────────────────────────────────────────────────────────────────┐
│                              AppShell                                  │
│   (AuthStore Integration, Language Context & Global Notification)      │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                           ShellLayoutWrappers                          │
│     (Dynamic Sidebars, Topbars, and Route Guards/Permissions Check)     │
├─────────────────────┬───────────────────────────┬──────────────────────┤
│    PublicLayout     │      TerminalLayout       │     SreLayout        │
└──────────┬──────────┴─────────────┬─────────────┴──────────┬───────────┘
           ▼                        ▼                        ▼
     ┌───────────┐            ┌───────────┐            ┌───────────┐
     │LoginPage  │            │Dashboard  │            │SreConsole │
     │Register   │            │(Research) │            │Workers    │
     │Pricing    │            │(Strategy) │            │Limits     │
     │Blog       │            │(Risk)     │            └─────┬─────┘
     └───────────┘            │(Learning) │                  │
                              └─────┬─────┘                  ▼
                                    │                ┌──────────────┐
                                    ▼                │SreAuditLogs  │
                              ┌───────────┐          │Incidents     │
                              │Assistant  │          └──────────────┘
                              │ShadowTrade│
                              └───────────┘
```

---

## 💾 PART 3 — State Management Strategy

All clients must partition state into structured stores to maximize speed, preventing duplicate state rendering loops:

1.  **TerminalStore (`useTerminalStore`):**
    *   Saves active symbol matrix configurations (max 30 assets).
    *   Receives real-time prices via WebSocket `market_update` event and updates active table tickers.
    *   Maintains the active selected symbol context across sub-intelligence tabs.
2.  **SreStore (`useSreStore`):**
    *   Stores worker lifecycle heartbeats and connection states.
    *   Subscribes to `sre_telemetry` and `incident_alert` and pushes active incident warnings.
3.  **AuthStore (`useAuthStore`):**
    *   Tracks user session token and PBKDF2 credential roles.
    *   Caches daily remaining AI Chatbot queries (syncs with `runtime_logs/auth.json` on execution).

---

## 🔄 PART 4 — Real-time & Authentication Flows

### Real-time Data Flow (WebSocket Client Loop):
1.  **Handshake:** Connection opened to `ws://localhost:8000/api/v1/ws`.
2.  **Telemetry:** Pings dispatched every 25s; pongs expected within 5s or connection falls back to `RECONNECTING` state.
3.  **Event Router:**
    *   If `market_update` received: dispatch payload to `TerminalStore.updateTick()`.
    *   If `signal_update` received: update visual trend postures and intelligence scores.
    *   If `shadow_update` received: update active virtual positions list, SL/TP bounds, and play signal tones.

### Secure Authentication Flow:
1.  **Form Submission:** Plaintext credentials securely delivered over HTTPS to `/api/auth/login`.
2.  **PBKDF2 Execution:** Server hashes credentials using PBKDF2 (100k iterations) and checks records in `runtime_logs/auth.json`.
3.  **Token Issuance:** Client receives cryptographic session token and caches user permissions context.
4.  **Route Guard Interceptor:** Checks role context on every path alteration. Triggers immediate redirections to `/403` or `/login` on unauthorized attempts.

---

## 🚀 PART 5 — Implementation Phases & Segmentation

### MVP Phase (Immediate Release Gate)
*   **Screens:** Landing Page, Registration/Login, Unified Trader Terminal (`/dashboard`), Research Intelligence (`/dashboard/research`).
*   **Focus:** Establish real-time WebSocket tick display, localized Persian/English widgets, core 8 timeframe layout tables, and static MT5 status banners.

### Phase 2 (Analytical Scaling)
*   **Screens:** Risk Intelligence Panel (`/dashboard/risk`), Advisory Execution Panel (`/dashboard/execution`), Strategy Confidence Panel (`/dashboard/strategy`).
*   **Focus:** Integrate Virtual position tracking table, backtest configurations forms, and dynamic chat queries with daily subscription checks.

### SRE & Advanced Shell (Operational Hardening)
*   **Screens:** Unified SRE Console (`/admin`), Worker Lifecycle Control (`/admin/workers`), System Limits Configuration (`/admin/limits`).
*   **Focus:** Core system telemetry sparklines, active worker manual reset buttons, live structured log streams, and the double-check emergency stop safety button.

---

## 🗺️ PART 6 — Dependency Mapping & Technical Risks

### Dependency Matrix:
1.  **UI Core:** Next.js / Tailwind CSS / Vazirmatn Font.
2.  **Data Graphing:** TradingView Lightweight Charts (pure price action candles with no subjective EMAs or MACDs).
3.  **Networking:** Axios Interceptor + Native WebSocket Client wrapper.

### Technical Risks & Mitigations:
*   **Risk 1: UI Lag during Intensive Websocket Pushes (30 symbols x 8 timeframes).**
    *   *Mitigation:* Use React memoization, throttle render ticks to 250ms intervals, and hide non-visible timeframe columns on small screens.
*   **Risk 2: Silent WebSocket Disconnection.**
    *   *Mitigation:* Strict 25s ping-pong heartbeat and exponential backoff retry policy with random jitter to prevent target server flooding.
*   **Risk 3: RTL/LTR Layout Shift Flashing.**
    *   *Mitigation:* Load localized files during server SSR or mount a blocking fallback skeletons component during initial storage evaluation.
*   **Risk 4: Unauthorized Role Climbing on Client.**
    *   *Mitigation:* Enforce redundant server-side JWT verification. The client checks roles to hide components, but the API rejects unauthorized actions with HTTP 403.
