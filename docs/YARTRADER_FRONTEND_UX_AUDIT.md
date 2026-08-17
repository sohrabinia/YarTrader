# YARTRADER FRONTEND DESIGN SYSTEM & UX AUDIT

**Target Package:** `trader-terminal`
**Styling System:** Tailwind CSS / Custom Utilities (`trader-terminal/src/assets/globals.css`)

---

## 1. EXTRACTED DESIGN SYSTEM TOKENS

### Color Palette
- **Primary Accent:** Emerald `#10b981` (`emerald-500`), Cyan `#06b6d4` (`cyan-500`)
- **Background Surface:** Deep Dark `#0f172a` (`slate-900`), Slate `#1e293b` (`slate-800`), Card `#334155` (`slate-700`)
- **Text Color:** High Contrast `#f8fafc` (`slate-50`), Muted `#94a3b8` (`slate-400`), Sub-text `#64748b` (`slate-500`)
- **Status Badges:**
  - Success/Profit: `#22c55e` (`green-500`)
  - Danger/Loss/Stop: `#ef4444` (`red-500`)
  - Warning/Pending: `#f59e0b` (`amber-500`)
  - Information/Demo: `#3b82f6` (`blue-500`)

### Typography
- **Font Family:** Inter / System UI Font Stack (`sans-serif`), Persian Vazirmatn fallback
- **Font Sizes:** `xs` (0.75rem), `sm` (0.875rem), `base` (1rem), `lg` (1.125rem), `xl` (1.25rem), `2xl` (1.5rem), `3xl` (1.875rem)
- **RTL / LTR Support:** Dynamic `dir="rtl"` / `dir="ltr"` and `lang` attribute on `<html>` root for Persian, Arabic, English, Turkish.

### Responsive Breakpoints
- `sm`: `640px`
- `md`: `768px`
- `lg`: `1024px`
- `xl`: `1280px`

---

## 2. UX DEBT & ISSUE CLASSIFICATION

| Priority | Screen / Module | Observed UX Issue | Impact | Recommended Redesign Direction |
| :--- | :--- | :--- | :--- | :--- |
| **P0 (Critical)** | Live Execution (`#/live`) | Hard-blocked switch toggle can cause user confusion regarding live status | User confusion on live enablement | Replace toggle switch with explicit "SRE Fail-Closed Safety Gate Lock" read-only status banner. |
| **P1 (High)** | Main Dashboard (`#/dashboard`) | High information density on small screens; stat cards wrap awkwardly | Weak mobile UX | Introduce responsive grid layout with collapsible stat sections. |
| **P1 (High)** | Chat Assistant Drawer | Chat error formatting when server returns non-JSON | UI glitch (`[object Object]`) | Ensure defensive string parsing and retry callbacks. |
| **P2 (Medium)** | Backtest Studio (`#/backtest`) | Progress indicator lacks estimated time remaining for multi-year runs | Unclear loading state | Add progress percentage and candle counter. |
| **P2 (Medium)** | Signal Center (`#/signals`) | Cards lack visual distinction between Fast Scalping and Swing trades | Suboptimal readability | Add colored style badges (Scalping vs Swing vs Intraday). |
| **P3 (Cosmetic)** | Top Navigation Bar | Language selector dropdown menu overlaps mobile menu button | Minor overlap | Increase z-index and spacing. |
