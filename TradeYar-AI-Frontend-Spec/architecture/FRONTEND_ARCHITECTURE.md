# FRONTEND_ARCHITECTURE.md — Frontend Architecture

This document describes the core architecture of the TradeYar AI Client Platform.

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

## 🛠️ Technology Stack & Performance Philosophy

1. **SPA Platform:** React 18+ / Next.js (App Router or Pages Router configured for Static Export) or Vue 3 (Pinia-based).
2. **Realtime Update Engine:** Built-in WebSocket client with deterministic JSON payload mapping and automated backoff reconnect policies.
3. **Data Fetching:** Axios or Fetch API wrapper with global request/response interceptors to manage token renewals and error toasts.
4. **Localization:** Multi-lingual JSON localization catalogs loaded dynamically from `/locales/` directory. DOM is manipulated dynamically without causing page flashes or broken text alignments.
5. **Chart Engine:** Lightweight Charts (TradingView) or Highcharts Stock for rendering raw price-action sequences and reaction zones. **No traditional indicators (EMA, RSI, MACD) may be drawn.** Only structural boundaries and raw candle ticks are permitted.
