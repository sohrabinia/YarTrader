# UX rules: realtime-behavior.md

This document defines the expected UX interactions when live-streaming market prices and AI reasoning flows.

---

## 1. Interactive Pulsing Visuals
- The `SystemStatus` indicator must use a soft pulsing radial glow matching its theme state.
- Real-time pricing cells in `MarketCard` must trigger flash highlights upon update (Green for price increase, Red for price decrease, lasting 300ms max).

## 2. Freeze and Desaturation on Disconnection
- Upon receiving a connection drop or heartbeat failure:
  - Immediately freeze all price fields at their last known values.
  - Overlay a semi-transparent blur or 60% opacity reduction.
  - Display a top-floating banner: `"Reconnecting to live feed... Prices frozen."` with a rotating spinner.
