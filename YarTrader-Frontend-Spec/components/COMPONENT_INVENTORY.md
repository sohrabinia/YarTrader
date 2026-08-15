# COMPONENT_INVENTORY.md — Component Inventory

This document lists the catalog of visual components required to build the TradeYar AI user interface across all three shell layers.

---

## 📦 Component Library

### 1. General Interface Components
Used across public, terminal, and SRE shell layers.

- **`LanguageSelector`**
  - **Description:** Dropdown header widget allowing quick toggle of active platform language (EN, FA, TR, AR).
  - **Interaction:** Modifies global HTML `lang` attribute and DOM text elements without page refresh (dynamic DOM localized updates, avoiding static or inverted translations).
- **`SecureAuthForm`**
  - **Description:** Form handling email login, secure password hashing registration, password recovery, and Apple & Google OAuth.
  - **Validation:** Minimum 8 characters, checks active login limits inside `runtime_logs/auth.json`.

---

### 2. Customer Trader Terminal Components (`/dashboard/*`)
High-fidelity elements optimized for analytical monitoring.

- **`SymbolSelector`**
  - **Description:** Autocomplete list displaying active trading symbols (governed by `SymbolRegistry` with a max limit ceiling of 30 symbols).
  - **Telemetry:** Shows real-time spreads and last updated timestamp.
- **`MultiTimeframeGrid`**
  - **Description:** A matrix-style table displaying the selected symbol across the 8 standard timeframes: **M1, M5, M15, H1, H4, D1, W1, MN1**.
  - **Columns:** Timeframe, Current Price, Trend State (Bullish/Bearish/Flat), Intelligence Score (0 to 100), Risk Status, Decision State.
- **`VirtualPositionManager`**
  - **Description:** Real-time visual panel of open and closed virtual positions synced from the Shadow Trading Engine.
  - **Fields:** Symbol, Timeframe, Direction (LONG/SHORT), Entry Price, SL/TP levels, Current P&L (color-coded, pulsating), Exit Reason.
- **`AssistantChatbot`**
  - **Description:** Collapsible floating chat widget allowing bilingual English/Persian interaction.
  - **Telemetry:** Counts daily usage against subscription tiers (USER: 10, PRO: 100, PREMIUM: 500, ADMIN: unlimited).

---

### 3. Demo Trading Dashboard Components (`/dashboard/demo`)
Specific elements optimized for simulated execution validation under learning risk environments.

- **`DemoAccountOverview`**
  - **Description:** Multi-unit header rendering key account performance metrics.
  - **Fields:**
    - Initial Balance: initialized at exactly **1194 USD**
    - Current Equity (simulated in real-time)
    - Margin Used, Free Margin
    - Daily Risk Used % (Learning risk limit **10%** vs Production risk limit **2%**)
    - Risk Alert status (Green = OK, Flashing Orange = warning when nearing daily limits)
- **`DemoPositionsTable`**
  - **Description:** Grid showing active positions established on the MT5 Demo Broker.
  - **Columns:** Symbol, Timeframe, Direction (BUY/SELL), Volume, Entry Price, Current Price, SL/TP, Current P&L (pulsating), Risk %, Actions (manual exit trigger).
- **`DemoTradeHistory`**
  - **Description:** List of closed simulated demo trades.
  - **Details:** Includes the parsed bilingually-detailed **AI Decision Explanation** (explaining the detected pattern, strategy name, timeframe, entry confidence, risk score, and decision chain) alongside the structured **Learning Feedback** lesson learned.

---

### 4. SRE Admin Console Components (`/admin/*`)
Highly utilitarian, status-aware diagnostic cards.

- **`SreTelemetryCard`**
  - **Description:** Panel showing dynamic system stats. Includes a pulsating neon indicator mapping background process loops.
  - **States:**
    - `Active / Healthy` (Pulsating green glow)
    - `Degraded / High Latency` (Static yellow border)
    - `Critical / Offline` (Flashing red shadow)
- **`WorkerLifecycleTracker`**
  - **Description:** Panel listing active background service workers (`ResearchWorker`, `IntelligenceWorker`, `ShadowWorker`, and `DemoTradingWorker`). Shows uptime, last tick timestamp, and current state (STARTING, RUNNING, IDLE, RECOVERING, FAILED, STOPPED).
  - **Actions:** Safe service manual start/stop hook button.
- **`EmergencyStopButton`**
  - **Description:** High-contrast, glowing button that triggers immediate virtual risk shutdown via `POST /api/risk/emergency_stop`.
  - **Protection:** Includes a double-step authorization dialog box.
