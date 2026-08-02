# SPACING.md — Spacing and Grid Layout

TradeYar AI uses a mathematically sound, 8px-based spacing system. All structural components, gutters, margins, paddings, and heights must align to the base scale increments to create visual rhythm.

---

## 📐 Spacing Scale

The baseline spacing increment is **8px** (represented as `0.5rem` on standard HTML setups).

| Token Name | Rem Value | Pixel Value | Application |
| :--- | :--- | :--- | :--- |
| `--space-1` | `0.25rem` | 4px | Inline icon-to-text spacing, micro pills padding |
| `--space-2` | `0.5rem` | 8px | Tiny card padding, form label gap, list items |
| `--space-3` | `0.75rem`| 12px | Internal container gaps, medium pills padding |
| `--space-4` | `1rem` | 16px | Card content padding, general grid gutters |
| `--space-5` | `1.5rem` | 24px | Dashboard panel spacing, section separations |
| `--space-6` | `2rem` | 32px | Side drawer widths, header navigation padding |
| `--space-8` | `3rem` | 48px | Public landing page sections margin |
| `--space-10`| `4rem` | 64px | Outer margins on high-impact landing layouts |

---

## 🧱 Dashboard Grid Specifications

To support complex data representations (such as the 8-timeframe matrix x 30 active symbols registry), use a modular grid with flexible grid systems.

### 1. Unified Grid Layout
- **Sidebar Width:** Fixed at `240px` (collapsed: `64px` with tooltip text fallback).
- **Core Container:** Fluid grid max-width: `1600px` for optimal wide-screen analytical usage.
- **Main Gutters:** Fixed at `--space-4` (16px) on desktop, scaling down to `--space-3` (12px) on mobile breakpoints.

### 2. Timeframe Column Breakpoints
Since TradeYar AI supports exactly eight timeframes (**M1, M5, M15, H1, H4, D1, W1, MN1**), the grid structure must scale cleanly:

- **Desktop (>= 1200px):** Show all 8 columns in the timeframe matrix.
- **Tablet (768px - 1199px):** Show 4 critical timeframes (M5, H1, H4, D1) or enable horizontal scroll indicators with frozen symbol names.
- **Mobile (< 768px):** Hide the full matrix grid. Replace with a responsive "Single Symbol Profile View" where the user selects one symbol and views a vertical carousel list of timeframe states.

---

## 📱 CSS Responsive Grid Breakpoints

Use these standard breakpoint thresholds for media queries:

```css
/* Mobile Devices */
@media (max-width: 575px) { ... }

/* Mobile Landscape & Small Tablets */
@media (min-width: 576px) and (max-width: 767px) { ... }

/* Medium Tablets (Portrait) */
@media (min-width: 768px) and (max-width: 991px) { ... }

/* Large Laptops / Standard Desktops */
@media (min-width: 992px) and (max-width: 1199px) { ... }

/* Enterprise Ultra-Wide Desktops (Trading Desks) */
@media (min-width: 1200px) { ... }
```
Layout elements must remain perfectly aligned to these grids with zero content overlapping.
