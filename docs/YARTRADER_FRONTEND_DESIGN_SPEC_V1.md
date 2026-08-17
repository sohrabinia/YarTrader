# YARTRADER FRONTEND DESIGN SPECIFICATION V1.0

**Classification:** Institutional Financial Intelligence & Trading Terminal
**Design Authority:** YarTrader Product Experience Engineering
**Implementation Package:** `trader-terminal`

---

## 1. VISUAL PHILOSOPHY & ART DIRECTION

YarTrader is an institutional AI financial intelligence platform. The user interface reflects a calm, technical, high-density, dark-mode terminal environment designed for quantitative analysts and traders.

### Design Principles:
1. **Calm Precision:** Elimination of unnecessary neon gradients, decorative blurs, and gamified animations.
2. **High Information Density:** Dense data tables and visual gauges optimized for 1440px+ displays without horizontal scrolling.
3. **Execution Safety Transparency:** Unambiguous visual indicators distinguishing DEMO, SHADOW, and HARD-BLOCKED LIVE execution states.
4. **Bi-directional Typography:** Full native RTL layout support for Persian and Arabic alongside LTR for English and Turkish.

---

## 2. COLOR TOKEN SPECIFICATION

```json
{
  "color": {
    "background": {
      "dark": "#0B1420",
      "surface": "#121E2C",
      "card": "#18283B",
      "hover": "#1F324A"
    },
    "border": {
      "default": "#243850",
      "gold": "rgba(227, 168, 59, 0.4)",
      "green": "rgba(76, 154, 106, 0.4)",
      "red": "rgba(194, 74, 62, 0.4)"
    },
    "brand": {
      "gold": "#E3A83B",
      "gold_hover": "#F0B84D",
      "buy": "#4C9A6A",
      "sell": "#C24A3E",
      "intel": "#4FB6C7"
    },
    "text": {
      "main": "#F1F5F9",
      "muted": "#94A3B8",
      "dim": "#64748B"
    }
  }
}
```

---

## 3. TYPOGRAPHY & LAYOUT GRID

- **Primary Font:** `Vazirmatn` (Persian/Arabic) + `Inter` (Latin)
- **Technical Monospace:** `Fira Code` (Prices, Tickets, P&L, Timestamps)
- **Container Breakpoints:** `640px` (sm), `768px` (md), `1024px` (lg), `1280px` (xl), `1536px` (2xl)
