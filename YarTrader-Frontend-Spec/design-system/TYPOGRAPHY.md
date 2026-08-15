# TYPOGRAPHY.md — Typography Specification

Typography in TradeYar AI supports quad-lingual alignment (English, Persian, Turkish, Arabic) while ensuring maximum visual clarity for dense numerical dashboards, symbol tickers, and live analytical trails.

---

## 🔤 Font Families

### 1. Persian and Arabic Interface Font
- **Primary Font:** `Vazirmatn` (specifically the modern, highly legible `Vazirmatn-font-face` hosted from a stable CDN or bundled locally).
- **Import Method:**
```html
<link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css" rel="stylesheet" type="text/css" />
```
- **Usage Policy:** Applies to all text elements (labels, headers, descriptions) when the language is set to Persian (`fa`) or Arabic (`ar`).

### 2. English and Turkish Interface Font
- **Primary Font:** `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif`.
- **Usage Policy:** Clean, geometric sans-serif styling optimized for fast reading in English (`en`) and Turkish (`tr`).

### 3. Monospace Code / Numeric Font
- **Primary Font:** `Fira Code, SFMono-Regular, Consolas, Monaco, monospace`.
- **Usage Policy:** Strictly applied to:
  - Raw candle price ticks (OHLCV)
  - Time stamps and dates
  - System performance telemetry numbers
  - Shadow Position P&L statistics

---

## 📏 Typography Hierarchy

| Style Role | Font Size | Font Weight | Line Height | Application |
| :--- | :--- | :--- | :--- | :--- |
| **H1 (Hero Heading)** | `2.25rem` (36px) | `700` (Bold) | `1.2` | Landing page title, onboarding headers |
| **H2 (Dashboard Title)**| `1.5rem` (24px) | `600` (Semi-bold) | `1.3` | Active panel titles, primary shell sections |
| **H3 (Card Heading)** | `1.125rem` (18px) | `600` (Semi-bold) | `1.4` | Component card titles, system module blocks |
| **Body (Standard)** | `0.875rem` (14px) | `400` (Regular) | `1.5` | System telemetry tables, assist chatbot |
| **Body (Small)** | `0.75rem` (12px) | `400` (Regular) | `1.4` | SRE logs, secondary timestamps, small labels |

---

## 📊 Numeric and Financial Display Standards

In a high-fidelity trading platform, numbers are the most vital data. Follow these strict rules when formatting numerical components:

1. **Monospace Pricing:** Always use tabular numerals (`font-variant-numeric: tabular-nums` or Mono fonts) for prices and metrics to prevent layouts from shifting during live WebSocket price ticks.
2. **Precision Standards:**
   - **XAUUSD / Precious Metals:** Round to exactly 2 decimal places (e.g., `2315.45`).
   - **Forex Majors (EURUSD):** Round to exactly 5 decimal places (e.g., `1.08245`).
   - **Crypto Assets (BTCUSD):** Round to 1 decimal place or zero decimals depending on asset price size (e.g., `68420.5`).
3. **Color-Coded Trend Pricing:**
   - Bullish delta numbers or positive percentages must prepend a plus sign and use `--color-buy` text coloring (e.g., `+1.45%`).
   - Bearish delta numbers or negative percentages must prepend a minus sign and use `--color-sell` text coloring (e.g., `-0.82%`).
   - Flat prices must remain in neutral white or light gray.
