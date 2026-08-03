# TradeYar AI Frontend Design Engineering Package v1.0

Welcome to the **TradeYar AI Frontend Design Engineering Package (v1.0)**. This package contains the complete frontend engineering and architectural contract between the TradeYar AI core platform, SRE monitoring services, and any consuming client applications (Web, Desktop, or Mobile SPAs).

This package is optimized to be directly consumable by both **Frontend AI Coding Agents** (e.g., GPT, Claude, Copilot) and **Human Frontend Engineers** to implement a production-grade UI without requiring deep knowledge of backend internals.

---

## 📋 CURRENT PLATFORM STATUS REPORT

### 1. Existing Core Capabilities
*   **APES-FIN Pipeline Execution:** Safe, sequential execution from historical market feed research up to passive analytical decision posture alerts.
*   **Shadow Trading Engine:** Simulated active virtual position management (SL/TP executions, chronological virtual ledger storage) completely isolated per timeframe and symbol.
*   **Strict Independent Multi-Asset Multi-TF Lock:** System orchestrates 150+ isolated cognitive engines (30 active symbols max ceiling x 5 timeframes), verified by `SymbolRuntimeManager.py`.
*   **Quad-lingual SRE Dashboard Shells:** Dynamic localization files loaded from `/locales/` for Persian, English, Arabic, and Turkish, synchronized via dynamic DOM translate page triggers.
*   **SRE Observability:** Live heartbeat, process liveness check, and detailed API diagnostic telemetry exposed via dynamic status-aware `/health` endpoints.

### 2. Newly Added Validation Pipeline Components
*   **Safe Trading validation lifecycle:** Formal transition states (`BACKTEST_MODE` -> `SHADOW_MODE` -> `DEMO_TRADING_MODE` -> `LIVE_TRADING_MODE` (strictly blocked)).
*   **MT5 Demo Account Integration:** Active simulated execution connecting to broker Demo environments. Initial balance is configured at exactly **1194 USD** virtual capital.
*   **Dual Risk validation limits:**
    *   Learning Validation Risk Mode: **10%** daily loss limit (max daily loss calculation of 119.40 USD).
    *   Production Simulation Risk Mode: **2%** limit (max daily loss calculation of 23.88 USD).
*   **Cognitive Learning Loop Sync:** Every completed demo trade automatically feeds back into **Learning Memory** to update strategy scores and pattern confidence metrics.
*   **AI Decision Explanation:** Detailed entry reasons outlining detected patterns, timeframes, confidence levels, and active decision chains.

---

## 🌌 Platform Overview: APES-FIN Pipeline
TradeYar AI is a pure Cognitive Market Intelligence System that strictly follows the **APES-FIN** execution pipeline.

```
Market Data (MT5 / Feeds)
       ↓
Research Intelligence (Feature Extraction, Statistical QC)
       ↓
Strategy Intelligence (Rule-Based Framework, Confidence Engine)
       ↓
Risk Intelligence (Portfolio Exposure, Limit Checks, Stop-Out Policies)
       ↓
Decision Intelligence (Multi-Asset / Multi-Timeframe Signal Fusion)
       ↓
Execution Intelligence (Passive Advisory Plans, No Automated Actions)
       ↓
Learning Intelligence (Four-Layered Memory Consolidation, Judge Brain)
```

### ⚖️ Architectural Guardrails & Rules
1. **Passive-Advisory Only:** There is **zero automated trading** execution or automated order placement. The UI must represent shadow-trading simulations or passive analytical recommendations.
2. **Zero Subjective Indicators:** The platform does not use MACD, RSI, EMA, or other traditional lag indicators. It relies purely on raw price-action sequences, structural reaction zones, and pattern similarity search.
3. **Structured Context Isolation:** Multi-asset and multi-timeframe engines are completely isolated to prevent BTC memory contamination into XAUUSD, governed by `SymbolRuntimeManager.py`.

---

## 📁 Repository & Specification Map

This specification is organized as follows:

```
TradeYar-AI-Frontend-Spec/
├── README.md                           # This entrypoint & Current Platform Status
├── architecture/
│   ├── FRONTEND_ARCHITECTURE.md        # Single Page App architectural design & Priority Execution Plan
│   ├── APPLICATION_STRUCTURE.md        # Monorepo/Workspace layout rules
│   ├── STATE_MANAGEMENT.md            # Client-side stores, WebSocket and API synchronization
│   └── ROUTING_STRUCTURE.md            # Three-shell routing system (Public, Terminal, SRE Console)
├── design-system/
│   ├── DESIGN_TOKENS.md                # Global design system constants & CSS variables
│   ├── COLORS.md                       # Brand and diagnostic color tokens
│   ├── TYPOGRAPHY.md                   # Font hierarchy & numeric layouts
│   ├── SPACING.md                      # Layout spacing & responsiveness grids
│   └── SHADOWS.md                      # Floating panels, modal layers & diagnostic cards
├── components/
│   ├── COMPONENT_INVENTORY.md          # Visual components catalog (including Demo dashboards)
│   ├── COMPONENT_BEHAVIOR.md           # Interactive state machines
│   ├── ERROR_STATES.md                 # 404, 403, 503 error landing pages
│   └── LOADING_STATES.md               # Skeleton screens & progress indicators
├── pages/
│   ├── PAGE_MAP.md                     # Directory of pages in all shells
│   └── USER_FLOWS.md                   # Step-by-step user onboarding & operation flows
├── realtime/
│   ├── WEBSOCKET_SPEC.md               # WebSocket connection lifecycle specifications
│   ├── RECONNECT_POLICY.md             # Reconnection & backoff algorithms
│   └── EVENT_SCHEMA.md                 # Event payloads & JSON schemas (with Demo schema)
├── api/
│   ├── API_CONTRACTS.md                # Complete HTTP API mappings (including demo endpoints)
│   └── JSON_SCHEMAS/                   # Hard JSON schemas for payload validation
├── security/
│   ├── USER_ROLES.md                   # Permission matrix (Public User, Trader, Analyst, Admin, SRE)
│   ├── PERMISSIONS.md                  # Access-control rules & client-side route guard specs
│   └── AUDIT_VISUALIZATION.md          # Multi-channel SRE audit log display & timeline
├── observability/
│   ├── SYSTEM_STATUS_UI.md             # Pulsating neon cards & diagnostic signals
│   ├── LATENCY_THRESHOLDS.md           # API/WS Performance latency metrics & statuses
│   └── ALERT_DESIGN.md                 # System incidents & SRE notification components
└── validation/
    ├── FRONTEND_ACCEPTANCE_CHECKLIST.md# Master checklist for production launch readiness
    └── VALIDATION_REPORT.md            # Coverage audit report & Implementation Gap Analysis
```

---

## 🤖 Instructions for AI Coding Agents
If you are an AI agent hired to build or modify TradeYar AI frontends, you **MUST** follow these absolute guidelines:
- **Do NOT invent APIs:** Rely strictly on the endpoints mapped in `/api/API_CONTRACTS.md`.
- **Match design tokens:** Standardize on colors, spacing, and typography defined in `/design-system/`.
- **Enforce Security Boundaries:** Never expose API keys, internal configuration files, or broker credentials.
- **Implement Multilingual Support:** Support exactly four languages: **English (EN), Persian (FA), Turkish (TR), and Arabic (AR)**.
- **Zero Automated Execution:** Present trading signals purely as passive advice or virtual shadow simulation records.
