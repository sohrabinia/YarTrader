# SYSTEM_STATUS_UI.md — System Status UI

This document details the layout design and interaction patterns for the real-time SRE status panels in the SRE Admin Control Console (`/admin`).

---

## 🟢 Status Badges & Neon Telemetry Cards

To make operational issues visible at a single glance, the top of the SRE Admin console features four pulsating neon cards mapping the core components:

```
┌────────────────────────┐  ┌────────────────────────┐  ┌────────────────────────┐
│   MT5 BRKR STATUS      │  │   ACTIVE RESEARCH LOP  │  │   SHADOW TRADE WORKER  │
├────────────────────────┤  ├────────────────────────┤  ├────────────────────────┤
│  🟢 Connected          │  │  🟢 ACTIVE (IDLE)      │  │  🟢 RUNNING            │
│  Ping: 12ms            │  │  Symbols: 18/30        │  │  Positions: 4 Open     │
│  Server: IC_Markets    │  │  Last Sync: 10s ago    │  │  Last Tick: 1s ago     │
└────────────────────────┘  └────────────────────────┘  └────────────────────────┘
```

### Card Styling and States:

- **1. MT5 Connectivity Card**
  - **Healthy:** Green pulsating badge `🟢 Connected`. Displays broker server, account ID, and ping latency in milliseconds.
  - **Critical:** Flashing red border `🔴 Disconnected`. Displays the specific error code (e.g., MT5 Error 503) and triggers a system recovery notification card.

- **2. Research Loop Card**
  - **Healthy:** Green badge `🟢 Active`. Shows currently active symbol count out of the dynamic limit ceiling (e.g. `18/30 Active Symbols`), lookback candle health, and last updated time.
  - **Degraded:** Yellow badge `🟡 High Latency`. Triggers when rates fetch takes longer than double the baseline threshold.

- **3. Shadow Worker State Card**
  - **Healthy:** Green badge `🟢 Running`. Shows number of open virtual position contracts and last update tick.
  - **Failed:** Red flashing banner `🔴 Failed`. Indicates the background worker encountered a crash or uncaught thread exception. Triggers recovery state.

---

## ⚡ Real-Time Transition Animations

When a background process shifts its state (e.g., a background worker crashes or the MT5 connection drops):
1. **Dynamic CSS Shifting:** The respective card must dynamically shift its layout class from `.border-success` to `.border-critical` within a `150ms` CSS transition transition speed.
2. **Alert Triggering:** Slide-in a critical SRE notification toast on the top-right corner containing actionable diagnostic codes.
