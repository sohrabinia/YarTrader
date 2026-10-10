# YarTrader Wave-Reversal Lifecycle

## Intended cycle
1. **Analyze:** ingest closed broker candles across H4/H1 context and M15/M5 setup with M1 timing. No forming candle may confirm a signal.
2. **Backtest:** run the multitimeframe base event study, wave-riding exits, reverse-entry events, chronological holdout and broker-specific spread/commission/slippage sensitivity. Research outputs are hypotheses until net expectancy is stable out of sample.
3. **Signal:** emit BUY/SELL/WAIT with source timestamps, base/structure evidence, stop, destination, gross and net reward/risk, expected-value inputs, and a reason code. A loss of edge in the current direction is not by itself a reverse signal.
4. **Demo:** if flat, pass all execution gates before opening. If a YarTrader-owned position exists, do not duplicate it. A reverse candidate requires M15/H1 structural confirmation, a closed M1 break, net R/R >= 1.2, positive expected-value proxy after cost allowance, a successful close, and broker-confirmed flat state before the reverse order is submitted.
5. **Shadow/live-readiness:** observe broker quotes and signal outcomes read-only; reconcile orders, positions, and fills; collect forward results. The current real-money execution gate remains hard-disabled.

## Code changes in this iteration
- `src/Execution/Services/session_execution_manager.py`: protective stop exits and explicitly confirmed wave/reversal exits bypass the legacy 120-second discretionary hold floor; unconfirmed discretionary exits remain blocked.
- `src/Execution/Services/demo_execution_engine.py`: close requests can carry an explicit exit reason and wave/reversal confirmation; normal closes still respect the legacy floor.
- `src/Execution/Services/autonomous_demo_trader.py`: an existing position is evaluated instead of causing an unconditional early skip. Foreign/manual positions and multiple-position states fail closed. An opposite direction is eligible only after higher-timeframe setup plus closed-M1 confirmation; the close must be confirmed flat before the reverse order. Reversal economics are logged with the order result.
- `src/Risk/Services/reversal_handoff.py`: economic-wave reversals require explicit opposite-structure confirmation, positive net expected value, and net R/R >= 1.2.

## Important remaining gates
- The current `wave_rider` historical simulator is still a single-leg research baseline; it does **not yet simulate full close-and-reverse trade campaigns**. Do not interpret its results as evidence for reversal profitability.
- The demo loop still returns `HOLDING` for a same-direction open position and does not yet apply a persistent, broker-verified ATR trailing-stop state machine to that position. Existing broker SL/TP remains protective; full intratrade wave management needs its own tests before being enabled.
- The demo reversal expected-value probability currently uses strategy confidence as a **proxy**, not a calibrated win probability. It is a conservative gating heuristic for forward-demo validation, not a validated expectancy model.
- The backtest's 0.05 ATR cost proxy is not a broker execution model. A production promotion gate must use observed Alpari spread, commission, slippage, rejected orders, and realistic intrabar stop ordering.
- Real-money trading remains disabled in `MetaTraderSafetyGate`. Do not remove that lock based on unit tests or demo results. Live activation requires independent approval, audited broker/account authorization, chronological out-of-sample evidence, demo forward performance, restart/reconciliation drills, and a separate safety review.

## Promotion order
`research -> chronological backtest -> cost sensitivity -> read-only signal/shadow -> demo forward test -> risk/reconciliation audit -> explicit live authorization review`.
Never promote automatically merely because one backtest split is profitable.