# LOADING_STATES.md — Loading States

This document defines the skeleton screens, spinners, and transition loading states to ensure perceived performance remains fluid.

---

## 💀 Skeleton Screen Specifications

For asynchronous panels (like the Multi-Timeframe Matrix or SRE Audit Trail), never use raw white screens or blocking spinner overlays. Instead, render static grey animated skeleton elements resembling the loaded cards.

### 1. Multi-Timeframe Grid Skeleton
- **Grid Layout:** 8 columns x 10 rows.
- **Visuals:** Static rectangles representing symbol tickers, with a pulsing background gradient shift:

```css
@keyframes skeleton-pulse {
  0% {
    background-color: #162032;
  }
  50% {
    background-color: #1f2d47;
  }
  100% {
    background-color: #162032;
  }
}

.skeleton-cell {
  height: 20px;
  border-radius: 4px;
  animation: skeleton-pulse 1.5s ease-in-out infinite;
}
```

---

## 🔄 Dynamic Content Loading Spinners

For fast-loading inline elements (such as submitting an AI Support Chat message or running a simulated backtest), use inline micro spinners.

### 1. Chatbot Typing Indicator
When waiting for `/api/chat/assistant` to respond, display the typing indicator:

```
┌─────────────────────────────────┐
│ Assistant                       │
├─────────────────────────────────┤
│ • • •                           │  <-- Pulsating dots animation
└─────────────────────────────────┘
```

- **Visuals:** Three small circular dots (`#00e5ff`) animating sequentially up and down.

### 2. Backtest Processing Ring
When running `POST /api/backtest/run`, overlay the backtest configuration panel with a semi-transparent screen featuring a central spinning progress ring.

- **Details:** Linear spinning border with a speed of `0.8s` per full revolution.
- **Progress Counter:** Display the percentage progress (e.g. `Backtesting Gold Matrix: 45%` calculated from real backtesting engine chunks).
- **Graceful Cancellation:** Include a secondary button that allows canceling the task and restoring the previous panel.
