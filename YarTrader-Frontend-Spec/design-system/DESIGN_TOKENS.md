# DESIGN_TOKENS.md — Design Tokens Master

Design tokens are the visual atoms of our design system. These tokens represent the single source of truth for all styling, branding, and layouts across the TradeYar AI platform.

These tokens are structured to enable consistent engineering by human developers and Frontend AI Coding Agents.

---

## 🚀 CSS Variables Integration

Implement these tokens inside your global stylesheets (e.g., `globals.css` or `theme.scss`) as custom properties:

```css
:root {
  /* Colors */
  --color-bg-base: #0a0e17;
  --color-bg-surface: #101622;
  --color-bg-card: #162032;
  --color-border-subtle: #1e2a3e;

  --color-primary: #00e5ff;
  --color-primary-hover: #33ebff;
  --color-primary-dim: rgba(0, 229, 255, 0.15);

  --color-success: #00e676;
  --color-warning: #ffd600;
  --color-critical: #ff1744;

  --color-buy: #00e676;
  --color-sell: #ff1744;
  --color-neutral: #90a4ae;

  /* Typography */
  --font-family-sans: "Vazirmatn", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-family-mono: "Fira Code", "Courier New", Courier, monospace;

  /* Spacing (Base-8 System) */
  --space-1: 0.25rem; /* 4px */
  --space-2: 0.5rem;  /* 8px */
  --space-3: 0.75rem; /* 12px */
  --space-4: 1rem;    /* 16px */
  --space-5: 1.5rem;  /* 24px */
  --space-6: 2rem;    /* 32px */
  --space-8: 3rem;    /* 48px */
  --space-10: 4rem;   /* 64px */

  /* Shadows & Neon Glows */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.5);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.6), 0 2px 4px -1px rgba(0, 0, 0, 0.5);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.7), 0 4px 6px -2px rgba(0, 0, 0, 0.6);
  --shadow-neon-primary: 0 0 12px rgba(0, 229, 255, 0.4);
  --shadow-neon-success: 0 0 12px rgba(0, 230, 118, 0.4);
  --shadow-neon-critical: 0 0 12px rgba(255, 23, 68, 0.4);

  /* Animation Speeds */
  --transition-fast: 150ms ease-in-out;
  --transition-normal: 250ms ease-in-out;
  --transition-slow: 400ms ease-in-out;
}
```

---

## 🎯 Implementation Policies

1. **Bilingual Stylesheet Rules:**
   - For RTL text direction (Persian and Arabic), set `direction: rtl;` and enforce the Vazirmatn font-face override on the body.
   - For LTR text direction (English and Turkish), set `direction: ltr;` and use standard sans-serif system fonts or Vazirmatn's Latin glyphs.
2. **Pulsating Status Signals:**
   - Neon glow tokens must support interactive keyframe animations representing the real-time activity of background service loops and telemetry heartbeats.
3. **Responsive Grid Controls:**
   - Multi-timeframe matrices must dynamically compress or hide low-resolution columns (like W1 and MN1) on mobile breakpoints to ensure maximum usability.
