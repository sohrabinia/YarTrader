# COLORS.md — Color Palette Specification

This document defines the visual color palette and diagnostic system signaling standards. TradeYar AI uses a Bloomberg/TradingView-style dark theme with intense neon telemetry accent colors.

---

## 🎨 Color Spectrum

### 1. Base Layer Colors (Backgrounds and Surfaces)
These dark-scale colors represent the backdrop of all dashboards, panels, and modal flows.

| Token | CSS Variable | Hex Code | Visual Swatch | Role |
| :--- | :--- | :--- | :--- | :--- |
| Base BG | `--color-bg-base` | `#0a0e17` | ⬛ | Core layout background |
| Surface BG | `--color-bg-surface` | `#101622` | ⬛ | Sidebars, headers, content sections |
| Card BG | `--color-bg-card` | `#162032` | ⬛ | Telemetry dashboards, analytics, lists |
| Border Subtle | `--color-border-subtle` | `#1e2a3e` | ➖ | Inner card dividers and gridlines |

---

### 2. Branding Accents and Primary Actions
Accents used for primary action buttons, clickable tabs, interactive widgets, and brand recognition.

| Token | CSS Variable | Hex Code | Visual Swatch | Role |
| :--- | :--- | :--- | :--- | :--- |
| Primary Neon | `--color-primary` | `#00e5ff` | 🟦 | Primary actions, links, neon highlights |
| Primary Hover | `--color-primary-hover`| `#33ebff` | 🟦 | Hover state for buttons and tabs |
| Primary Dim | `--color-primary-dim` | `rgba(0, 229, 255, 0.15)` | 🟦 | Highlight backgrounds, secondary pills |

---

### 3. Diagnostic & State Mapping
Accurate representations of status and health across SRE monitoring and system parameters.

| State | Hex Code | CSS Variable | Associated Meaning / Signal |
| :--- | :--- | :--- | :--- |
| **Healthy / Active** | `#00e676` | `--color-success` | Active workers running normally, connection healthy, no limits reached |
| **Degraded / Warning** | `#ffd600` | `--color-warning` | High latency, service recovery active, system limits nearing 90% |
| **Critical / Incident** | `#ff1744` | `--color-critical` | MetaTrader5 connection lost, database files missing, worker crashed |

---

### 4. Financial Signaling (Trading Indicators)
Used exclusively to highlight passive advisory trading signals and shadow execution stats.

| Signal | Hex Code | CSS Variable | Applied Components |
| :--- | :--- | :--- | :--- |
| **Buy / Bullish** | `#00e676` | `--color-buy` | BUY signals, virtual LONG entry price, positive P&L metrics |
| **Sell / Bearish** | `#ff1744` | `--color-sell` | SELL signals, virtual SHORT entry price, negative P&L metrics |
| **Neutral / Flat** | `#90a4ae` | `--color-neutral` | Out-of-market state, flat positions, pending orders |

---

## ⚡ Accessibility and Readability Rules
1. **Pristine Dark Contrast:** All text must meet a minimum contrast ratio of `4.5:1` against their respective backgrounds. Use white or bright gray (`#f5f7fa`) for body copy over dark surfaces.
2. **Colorblind Fallback:** Indicators must never rely on color alone. Always combine color-coded states with an text label (e.g., `BUY` or `SELL`) or a status icon.
3. **No Light Mode:** This is a professional dark-themed fintech environment. There is no alternative light mode theme.
