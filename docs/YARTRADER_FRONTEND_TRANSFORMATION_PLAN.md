# YarTrader Frontend Transformation Master Plan v1.0

**Date:** August 23, 2026
**Author:** Jules — Lead Systems & Frontend Engineer
**Scope:** Phase 0 Architecture Audit, Migration Order, Risk Assessment, and Target Architecture Specification for transforming YarTrader into an **Autonomous Financial Intelligence Operating System**.

---

## Executive Overview

The purpose of the YarTrader frontend transformation is to visualize, explain, and control the complete **Autonomous Intelligence Lifecycle**:

$$\text{Real Market Data} \longrightarrow \text{Data Intel} \longrightarrow \text{Research} \longrightarrow \text{Market Intel} \longrightarrow \text{Fractal Intel} \longrightarrow \text{Regime Analysis} \longrightarrow \text{Decision Engine} \longrightarrow \text{Risk Engine} \longrightarrow \text{Demo Execution} \longrightarrow \text{Position Lifecycle} \longrightarrow \text{Journal} \longrightarrow \text{Performance} \longrightarrow \text{Learning Loop}$$

This transformation preserves all backend FastAPI contracts, SRE fail-closed live trading isolation (`LIVE_TRADING_ENABLED=False`), MT5 Demo execution (#52961173), and 4-locale translation parity (Fa, En, Tr, Ar).

---

## 1. Current vs Target Architecture Comparison

| Architectural Dimension | Current State (`trader-terminal`) | Target State (`YarTrader Design System`) |
| :--- | :--- | :--- |
| **Framework & Build System** | React 18 SPA + Vite 5.4.21 | React 18 SPA / Next.js + Vite + TypeScript + Tailwind CSS |
| **Component Architecture** | Monolithic `App.jsx` (~1,300 lines) | Modular domain features (`src/features/*`) + `shadcn/ui` primitives |
| **Styling & Design Tokens** | Custom CSS variables in `globals.css` | **YarTrader Design System** (`src/design-system/`) + Tailwind CSS |
| **State Management** | Local `useState` + `localStorage` helper | **Zustand** stores (`useAuthStore`, `useMarketStore`, `useAdminStore`) |
| **Data Fetching Layer** | Fetch wrapper (`apiService`) | **TanStack Query (React Query)** with caching, revalidation, and retry |
| **Financial Charting** | HTML Tables / Text Badges | **TradingView Lightweight Charts (`lightweight-charts`)** with OB/FVG canvas |
| **Real-time Connectivity** | `setInterval` HTTP Polling (1000ms) | Resilient WebSocket client (`ws://`) with HTTP polling fallback |
| **Navigation & Routing** | `window.location.hash` conditionals | Client-side Router with layout shells and nested route guards |

---

## 2. Phase-by-Phase Migration Roadmap & Execution Order

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 0 — MANDATORY AUDIT & BLUEPRINT (COMPLETED)                                │
│ • Complete route, component, API, and gap inventory                              │
│ • Publish transformation deliverables in docs/                                  │
└──────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 1 — FOUNDATION & DESIGN SYSTEM SETUP                                      │
│ • Initialize src/design-system/ and 17 core components                           │
│ • Set up Tailwind CSS + shadcn/ui primitives + institutional dark tokens         │
│ • Configure Zustand stores & TanStack Query client                               │
└──────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 2 — PUBLIC & AUTHENTICATION PORTAL                                         │
│ • Implement Public Landing (/), Features, Pricing, Docs, Blog, FAQ, Contact      │
│ • Implement Auth Split-Screen (/login, /register, /forgot-password, /profile)    │
└──────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 3 — USER INTELLIGENCE TERMINAL & CHARTING ENGINE                           │
│ • Deconstruct App.jsx into modular domain features (src/features/*)              │
│ • Integrate TradingView Lightweight Charts with Order Block & FVG overlay canvas │
│ • Build Command Center, Fractal Visualizer, Regime Meter, Risk Board, XAI Board │
└──────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 4 — TRADING MODES, POSITION LIFECYCLE & SAAS PLATFORM                      │
│ • Implement PositionTimelineStepper (Created → Validated → Opened → Managed → Closed) │
│ • Implement Trade Journal, Performance Center, Wallet Ledger, Billing Manager   │
│ • Enforce SRE Fail-Closed Safety Gate on /live (#143056202 hard-blocked)          │
└──────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 5 — SRE ADMIN CONTROL PLANE & ENTERPRISE TOOLS                             │
│ • Implement 17 Admin Subsections (Overview, Users, RBAC, AI Engines, Audit)    │
│ • Add Global Command Palette (shadcn Command pattern) & Notification Drawer     │
│ • Validate 100% 4-locale key parity (Fa, En, Tr, Ar) & dynamic RTL direction     │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Migration Risks & Mitigation Controls

| Risk Factor | Impact | Severity | Mitigation Strategy |
| :--- | :--- | :---: | :--- |
| **Backend API Incompatibility** | Breaking existing endpoints during refactoring | **CRITICAL** | Strict API abstraction layer (`src/services/api.js`); zero changes to FastAPI backend endpoints. |
| **Live Trading Accidental Trigger** | Real money risk on live broker accounts | **CRITICAL** | Hard-coded `LIVE_TRADING_ENABLED=False` in SRE Safety Gate (`MetaTraderSafetyGate`); `/live` remains hard-blocked. |
| **Localization & RTL Regression** | Broken Persian/Arabic layouts during UI overhaul | **HIGH** | Retain `I18nProvider` in `src/services/i18n.jsx` with dynamic `document.body.dir` enforcement and Vazirmatn font. |
| **Hydration Mismatch / Build Failure** | Production build crashes or bundle inflation | **MEDIUM** | Continuous Vite build validation (`npm run build`) after each feature domain migration. |
| **Chart Re-render Performance** | FPS drop during real-time market tick updates | **MEDIUM** | Decouple TradingView Lightweight Charts canvas from React render tree using refs and requestAnimationFrame. |

---

*Transformation Plan certified by Jules — Lead Systems & Frontend Engineer.*
*YarTrader Autonomous Financial Intelligence Platform.*
