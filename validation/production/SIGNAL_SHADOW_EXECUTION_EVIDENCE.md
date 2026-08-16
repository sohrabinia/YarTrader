# YarTrader Shadow / Signal Trading Execution Evidence

## Executive Summary
This document provides executable runtime evidence verifying signal-only shadow trading operations on YarTrader V1.

---

## Signal Execution Telemetry

* **Engine:** `PredictiveShadowEngine`
* **Signal ID Generated:** `sig-66aa3b`
* **Linked Virtual Trade ID:** `strade-66aa3b`
* **Symbol / Direction:** `EURUSD` / `LONG`
* **Signal Status:** `ACTIVE`
* **Hypothetical Position Tracking:** Floating P&L, MFE, and MAE tracked in `SymbolTimeContext`
* **Broker Execution Status:** `NO EXECUTABLE BROKER ORDERS SENT`
* **Persistence:** Saved in `runtime_logs/signal_history.json` and served via `/api/user/signals`
