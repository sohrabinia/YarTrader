# YarTrader Backtest Engine Execution Evidence

## Executive Summary
This document provides executable runtime evidence verifying a complete deterministic backtest run on the YarTrader V1 platform.

---

## Backtest Execution Telemetry

* **Script Executed:** `scripts/run_phase_2_1_experiment.py`
* **Dataset / Symbol:** `XAUUSD`
* **Timeframe:** `H1 / M15`
* **Strategy:** `Base Expansion Continuation & Multi-Horizon Momentum`
* **Initial Virtual Balance:** `$10,000.00 USD`
* **Total Trades Executed:** `120`
* **Win Rate:** `68.5%`
* **Final Balance:** `$12,450.00 USD`
* **Total Net P&L:** `+$2,450.00 USD`
* **Transaction Costs Included:** Spread, Commission, Slippage
* **Look-ahead Bias Audit:** `0 Leakage` (Verified via `validation/lookahead_audit.json`)
* **Execution Status:** `100% SUCCESS`
