# YarTrader Autonomous Demo Trading Final Verification Manual

**Version:** 1.2.0
**Authority:** Technical Manager Release Directive

---

## 1. System Overview

YarTrader Autonomous Demo Trading provides end-to-end autonomous research, market intelligence, decision formulation, pre-trade risk/confidence gating, fail-closed DEMO execution, position tracking, immutable trade journal logging, and post-trade evidence-based learning.

---

## 2. Fail-Closed Execution & Adapter Safety

1. **`order_check` Fail-Closed Protection:**
   Prior to `mt5.order_send()`, `RealMT5BrokerAdapter.send_order_to_broker()` calls `mt5.order_check()`.
   If `order_check()` returns a retcode other than `0` (DONE), `10009` (DONE), or `10013` (INVALID_STOPS / CHECK_OK), `send_order_to_broker()` returns a failed `OrderResponse` immediately without invoking `order_send()`.

2. **Deterministic Filling Mode Resolver:**
   Reads `sym_info.filling_mode` bitmask and selects supported filling mode (`FOK` = 0, `IOC` = 1, `RETURN` = 2). On assets such as `BITCOIN`, `FOK` is selected, avoiding filling mode rejections.

3. **Comment Sanitization:**
   Requests sanitize `Comment` strings to max 31 clean ASCII characters.

---

## 3. P&L Reconciliation & Journal Integrity

- P&L reconciliation (`reconcile_pnl`) compares MT5 deal metrics (`gross_profit`, `commission`, `swap`, `net_pnl`, `open_price`, `close_price`, `volume`) field-by-field against an existing YarTrader Trade Journal record (`TradeJournalRecord`).
- Synthetic journal records are never created. If no matching journal record exists, reconciliation returns `UNPROVEN / BLOCKED`.

---

## 4. Learning Protection Gates

- **Sample Size Gate (N >= 5):** When `N < 5`, candidate adaptations remain in `OBSERVE_ONLY` status without mutating decision parameters.
- **Safety Boundary Isolation:** Learning engine is hard-blocked from altering `LIVE_TRADING_ENABLED`, `DemoExecutionGate`, `MetaTraderSafetyGate`, or `AUTONOMOUS_DEMO_TRADING_ENABLED`.
