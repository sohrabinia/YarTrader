# 00 - Project State & Repository Overview

## Core Repository Identity
* **Repository**: `sohrabinia/YarTrader`
* **Current Main SHA**: `2c2926c` (Merged PR #267 Google OIDC integration)
* **Domain**: `https://yartrader.com`
* **Architecture**: APES-FIN Clean Architecture Standard (Python 3.12 Backend, React Vite SPA Frontend)

## Canonical Product Scope
YarTrader is an Autonomous Financial Intelligence and Trading Engine strictly limited in execution scope:
* **Primary Asset**: `XAUUSD` Gold (Multi-asset extensible framework ready for EURUSD, GBPUSD, USDJPY, commodities, indices, crypto).
* **Execution Boundary**: Backtest & Native MT5 DEMO Execution strictly (`LIVE_TRADING_ENABLED = False` hard-locked).
* **Trading Logic**: Market-following probabilistic brain (M1+ OHLCV baseline) without artificial fixed SL/TP or R/R contracts ($3 SL / $5 TP eliminated).
* **Execution Rules**: 120-second minimum position holding period, End-Of-Day (EOD) position flattening (`OPEN_POSITIONS = 0`).
* **Risk Budget**: 2.0% max account equity trade-risk hard ceiling enforced by `ProfessionalRiskEngine`.
