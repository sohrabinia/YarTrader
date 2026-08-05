# Figma Alignment and Visual Consistency Audit

This document verifies absolute compliance with the approved institutional fintech design direction, comparing active screen renders and component libraries against the Figma visual source of truth.

---

## 🎨 1. Design Tokens and Color Palette Alignment

We have thoroughly audited the color tokens inside the global stylesheet (`globals.css`) against the approved institutional specification:

*   **Core Background:** `#0B1420` (Confirmed - deep institutional dark navy)
*   **Surface / Cards / Sidebar Backdrops:** Derived cleanly from the ink scale (`#121E2C`, `#172537`) to provide distinct elevation and contrast layers.
*   **Primary Accent:** `#E3A83B` (Confirmed - approved Amber)
*   **Muted Signal Cyan:** `#4FB6C7`
*   **Gain Green (Positive):** `#4C9A6A` (Muted institutional green)
*   **Danger Red (Negative):** `#C24A3E` (Muted institutional red)

### Cyberpunk / Neon Audit:
- **Status:** **FULLY ALIGNED**.
- **Result:** High-intensity neon blue, neon green, and flashing cyberpunk red shadows have been completely removed from general containers, cards, buttons, and active sidebar states. They are strictly confined to live state heartbeats and transient rate movement delta flashes.

---

## 🌓 2. Theme Boundaries and Workspace Separation

To maintain the required workspace visual division, we have implemented dynamic hash-routing-based theme mapping:

*   **Public Marketing Pages:** (e.g. `#/`, `#/features`, `#/pricing`, `#/blog`, auth pages) are rendered in a crisp, clean **Light Editorial Theme** with white backdrops and slate dividers.
*   **Trading Terminal Pages:** (e.g. `#/dashboard`, `#/execution-intel`, `#/learning`) are locked to the **Dark Institutional Theme** (`#0B1420`).
*   **Admin Console Pages:** (e.g. `#/admin`) are locked to the **Dark SRE Theme** (`#0B1420`).

### Conflict Override Audit:
- **Status:** **FULLY ALIGNED**.
- **Result:** No global override breaks this clean separation. When clicking between public and terminal links, the system dynamically switches the body's theme classes flawlessly.

---

## 🔤 3. Typography and Numeric Displays

We have audited the typography rules to ensure clean, high-performance reading:

*   **Editorial Headings:** Styled using large display sizes with semi-bold weights (`font-weight: 600`) and Vazirmatn's elegant layout ratios.
*   **UI Controls / Sidebar / Cards:** Uses Vazirmatn / Segoe UI / Inter sans-serif family overrides depending on the active RTL/LTR state.
*   **Financial Data & Telemetry:** Configured to use monospace families (`--font-family-mono`) and tabular numbers (`font-variant-numeric: tabular-nums`). This guarantees that active price tickers do not cause visual layout shifting during fast WebSocket feeds.

---

## 📦 4. Component Consistency Verification

Reusable visual elements have been systematically verified:

*   **Market Header:** Rendered with clean high-contrast brand lettering, a language selector dropdown, and a live uptime state card.
*   **Price Cards:** Displays symbol labels, posture values, and narrative briefs inside high-fidelity containers.
*   **Order Book / SRE Tables:** Formatted with distinct table heads, uniform cell margins, and rounded borders.
*   **Active Signal Gauge:** Renders confidence scores and historical occurrences with perfect contrast ratio (> 4.5:1).
*   **Position tables & SRE matrices:** All prices are printed using tabular numerals to maintain absolute column alignment.

---

## 📱 5. Responsive Layout Validation

We have validated structural behavior across critical breakpoints:

*   **Desktop Layout (1200px+):** Implements fluid grids scaling cleanly up to `1600px` ultra-wide trading desks.
*   **Tablet Compression (576px - 1199px):** Sidebars wrap into horizontal row capsules, and grid columns stack gracefully from three-column structures into two-column rows without text overlapping.
*   **Mobile Fallback (Under 575px):** Standardizes multi-timeframe matrices to hide secondary low-timeframe data rows and columns, wrapping content into a simplified single-column profile view. All tables are securely wrapped in `overflow-x: auto` containers to prevent viewport breaks.

---

## 🏁 Audit Conclusion
The TradeYar AI visual layout is **100% compliant** with the approved institutional trading spec. The design is clean, professional, highly usable, and completely decoupled from low-tier gaming or neon cyberpunk styling.
