# PAGE_MAP.md — Page Directory and Screen Specifications

This document catalogs every page/screen in the TradeYar AI platform, detailing visual components, access levels, and specific layout guidelines.

---

## 🗺️ Page Mapping Directory

```
├── Public Marketing Website (Guest Users)
│   ├── /                         # Landing Page
│   ├── /features                 # Algorithmic capabilities
│   ├── /pricing                  # Subscription and payments
│   ├── /blog                     # Article catalog
│   └── /blog/:article_id         # Article reader page
│
├── Customer Trader Terminal (Authenticated Members)
│   ├── /dashboard                # Unified Market Ticker & Multi-Timeframe Matrix
│   ├── /dashboard/research       # Feature extraction & QC analytics
│   ├── /dashboard/strategy       # Strategy confidence & backtester
│   ├── /dashboard/risk           # Exposure meters & policy checklist
│   ├── /dashboard/execution      # Advisory logs & shadow trades
│   └── /dashboard/learning       # Cognitive loop & memory progress
│
└── SRE Admin Console (SRE Operators & Admins)
    ├── /admin                    # Main system health & telemetries
    ├── /admin/workers            # Worker lifecycle & live log stream
    └── /admin/limits             # Active symbols matrix limits manager
```

---

## 📺 Detailed Screen Layout Specs

### 1. Unified Trader Terminal (`/dashboard`)
The central landing panel of the trading environment.

- **Structure:**
  - **Left Sidebar:** Collapsible navigation list + active symbol quick-selector dropdown list.
  - **Top Navigation:** Dynamic language select, active user profile pill, real-time WebSocket connection state indicator.
  - **Main View Matrix:** Multi-Timeframe Grid showing the 8 primary frames (M1, M5, M15, H1, H4, D1, W1, MN1) for the active symbol. Clicking a row reveals:
    - Current Tick (High/Low/Close)
    - Trend state (Bullish/Bearish/Flat, color-coded)
    - Intelligence score (0-100 meter)
    - Risk status (OK/Warning/Violation)
    - Decision state (No action / Advisory Buy / Advisory Sell)
  - **Right Floating Panel:** Collapsible English/Persian AI support chatbot widget.

---

### 2. SRE Admin Dashboard (`/admin`)
Used strictly for infrastructure management and operational safety monitoring.

- **Structure:**
  - **System Status Bar:** Displays global API responsiveness, active MT5 connection state, database parse integrity, and active incident alarms.
  - **Central Diagnostic Grid:**
    - **Worker Cards:** Uptime metrics, worker thread state, memory size, and restart hooks for `ResearchWorker`, `IntelligenceWorker`, and `ShadowWorker`.
    - **Resource Panels:** Interactive SVG graph charting server CPU/RAM usage.
    - **Limits Manager:** Field configurations to alter active assets ceiling and YAML configurations.
  - **Bottom Timeline Panel:** Rotating live structured logs fetched from `security.log` and SRE stream.
