# Multi-Timeframe Base & Transition Research

## Purpose
Research/backtest component for YarTrader. Detects base departures across MN1/W1/D1/H4/H1/M15/M5/M1, maps lower-timeframe bases contained in parent bases, records trend/volatility context known at the exit, and labels the route from the exited base toward the next known base.

## Run
From the repository root:

    C:\Users\Administrator\AppData\Local\Programs\Python\Python314\python.exe scripts\research\backtest_multitimeframe_base_transitions.py

The JSON report is written to:
runtime_logs\mt5_gold_history_full\multitimeframe_base_transition_study.json

The default run scans the latest 600,000 M1 bars to limit memory use. For more history, use zero for the cap (high memory use):

    C:\Users\Administrator\AppData\Local\Programs\Python\Python314\python.exe scripts\research\backtest_multitimeframe_base_transitions.py --m1-max-bars 0 --scan-m1 30

Lower scan-step values examine more bars and take longer.

## Current operational definitions
- Base: 2–6 bars, width no greater than 1.5 ATR, mean candle body no greater than 0.55 ATR.
- Incoming leg: four-bar close displacement of at least 0.8 ATR.
- Departure: a confirmed close outside the base, at least 0.15 ATR beyond its edge and at least 1.0 ATR from its midpoint; confirmation occurs within 1–3 bars.
- Types: RBR, DBD, DBR, RBD.
- Nested child context: child base interval is inside the parent base interval, its midpoint is inside the parent zone, and its departure was confirmed no later than the parent departure. Later-confirmed child structures are excluded from the parent's feature snapshot.
- Timestamps: MT5 CSV times are bar-open timestamps. A departure becomes known at the confirmation candle's close (bar open + timeframe duration), not at its open.
- Market context: each event records trend and ATR/rolling-median volatility across timeframes, using only candles whose close time is no later than the event confirmation.
- Next base: nearest price zone in the departure direction among zones whose departure was confirmed strictly before the current exit; the whole target zone must be ahead of the exit price. Same-time events are not treated as prior-known targets.
- Transition labels: continuation barrier, reversal barrier, origin-base retest, failed-exit closeback, touch of the next known base, and a compact pause/consolidation candidate in the next 24 bars. The system also records whether that new corridor pause later departs in the original exit direction or the opposite direction. Simultaneous first hits are marked ambiguous, except retest + closeback on the same bar is classified as failed exit.

## Baseline trade simulation
The report includes two fixed-rule baselines and one intraday wave-riding research baseline, none of them production strategies:
- fixed_2R: enter at the next candle open after a confirmed departure, stop beyond the far side of the base plus 0.1 ATR, target 2R, maximum hold 24 bars.
- next_base: same entry/stop logic, but target the nearest already-known base zone in the departure direction; events without a valid forward target are not eligible.
- wave_rider (M15/M5/M1 only): no fixed profit target; initial stop is behind the base. At +1R the stop is protected at breakeven, at +1.5R a 2.5 ATR chandelier-style trail is activated, and two closes back inside the origin base can exit only when the trade remains profitable. For finite research windows, evaluation caps are 48 M15 bars, 96 M5 bars, and 240 M1 bars; these caps are accounting boundaries, not proposed live time-based exits.
- If stop and target are both touched in one OHLC candle, the stop is assumed first (conservative).
- Cost-adjusted metrics subtract 0.05 ATR per completed trade as a rough round-trip cost proxy. This is not actual broker spread/commission/slippage. Net R proxy and profit-factor proxy are sensitivity diagnostics, not proof of profitability.

## Leakage and limitations
Detection features and offline outcome labels are separated. The feature cutoff time records the latest time allowed for event features. Forward outcomes must not be fed back into live inference or model features. The script is research-only and does not send orders.

The scan is sampled, so some events can be missed. M1 is limited to its most recent 600,000 bars by default; older parent structures will not have complete M1 child context. OHLC bars cannot resolve the intrabar order when multiple barriers are touched in one candle. This is a baseline event and trade simulation, not a fully broker-costed backtest: spread, commissions, slippage, entry execution, stop/target management, and position sizing still need validation against actual broker data before profitability can be assessed.

## Interpretation
Compare outcomes by timeframe, base type, long/short direction, nested child alignment/opposition, destination-zone distance, and closed D1/H4/H1 trend/volatility regimes. The baseline trade simulation also reports a rough first-70% / last-30% chronological split; treat the last 30% as a preliminary holdout, not a final independent validation. Do not interpret transition percentages or ATR-cost proxies as proof of a profitable edge. Fix candidate hypotheses before a strict chronological holdout test and re-test with actual broker costs.
