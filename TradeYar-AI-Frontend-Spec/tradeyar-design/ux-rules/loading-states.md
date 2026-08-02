# UX rules: loading-states.md

This document defines standard loading layouts to handle asynchronous data fetching cleanly.

---

## 1. Skeleton Loading States
- Always prefer skeleton layouts instead of generic spinner blocks for predictable dashboards.
- Skeletons must mimic the final card layouts with custom pulsate animation constraints.

## 2. Progressive Telemetry Rendering
- Render the core dashboard framework structure immediately.
- Incrementally fill in panels (first pricing, then signals, then explanation metadata) as they resolve.
