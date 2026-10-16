# Multi-timeframe Base Behavior Monitor

## What is integrated

`DecisionEngine` now owns a `MultitimeframeBaseBehaviorMonitor`. Every call to
`generate_professional_signal(..., candles_by_tf=...)` attempts a Base-observation
snapshot from that same timeframe feed and stores it in
`DecisionEngine.last_base_behavior_report`. Call
`analyze_multitimeframe_base_behavior(candles_by_tf, now=...)` directly when the
caller needs the report immediately.

The snapshot reports, per timeframe, the number of closed bars and detected/recent
bases; recent base zones; a causally confirmed nested parent/child link when one
exists; and a reaction ledger for each base. Each lower timeframe is measured
separately so one move touching the same zone on M1 and M5 is not conflated into
one ordinal. Each visit reports touch time/price, penetration fraction, duration,
observed favorable/adverse excursion in ATR units, and a structural wave snapshot (post-departure, riding-wave, retesting, or invalidated).

## Input contract

- Supply a mapping such as `{"H1": [...], "M15": [...], "M5": [...], "M1": [...]} `.
- Values may be `MarketDataPoint` instances or OHLC mappings with a timestamp.
- Candles must be closed. The monitor additionally excludes bars whose nominal
  close timestamp is after `now`.
- The monitor inspects a bounded recent tail per timeframe; use the offline
  research scripts for long-history model training and walk-forward validation.

## Safety and current limits

This is a live observation and measurement layer, not a claim that the complete
wave-riding strategy is ready. The decision section remains `WAIT` and entry,
exit, and reversal proposals remain empty until a causal model with sufficient
broker-costed out-of-sample expectancy is available. It never places, modifies,
or cancels broker orders and does not override the existing professional signal.

The current reaction count is a bar-based visit count. Intrabar ordering, tick-level
touch sequencing, broker-specific spread/commission/slippage, persistent reaction
memory across restarts, portfolio constraints, and a validated wave-state machine
still require further work. A monitor report must not be interpreted as a trade
instruction.


## Durable reaction memory update

The monitor now persists observed reaction episodes to `runtime_logs/base_behavior_monitor_state.json` by default. State writes use a temporary file followed by an atomic replace, and visits are upserted by timeframe plus visit start timestamp so repeated snapshots do not create duplicate visits. If a still-visible episode develops more bars, its stored metrics are updated in place. The report includes persistence status, stored-base count, and stored-reaction count.

Pass `state_path=None` to disable persistence for isolated tests. Persistence errors are reported in the snapshot and do not turn the observer into a trading decision-maker. The state file is runtime data and must not be committed to source control.
