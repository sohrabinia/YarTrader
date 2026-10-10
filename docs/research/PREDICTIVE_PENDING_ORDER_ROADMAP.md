# Predictive market analysis and pending-order roadmap

## Target behavior
YarTrader should form a multi-timeframe scenario before price reaches the entry: detect the base and its departure, map retest/continuation and opposing-wave alternatives, estimate destination and invalidation, and propose a conditional order only while the scenario remains valid. A pending order is a hypothesis with explicit expiry and cancellation rules, not a prediction that must be defended.

## New research component
`src/Decision/Intelligence/pending_order_planner.py` is a pure, broker-independent proposal planner.
- `RETEST` can propose BUY_LIMIT / SELL_LIMIT only when the intended entry is still on the correct side of the quote.
- `BREAKOUT` can propose BUY_STOP / SELL_STOP only when the trigger has not already been crossed or become too close.
- Every proposal requires direction, zone, invalidation, target, ATR, confidence, fresh quote, and expiry; spread and estimated slippage/commission reduce net reward/risk.
- The plan carries explicit cancellation conditions: invalidated zone, confirmed opposing structure, excessive spread, expiry, or failed revalidation.
- `should_cancel` only computes a policy decision; it does not cancel broker orders.

## Safety boundary
The planner deliberately does not call MT5 and cannot place orders. This is intentional. Before connecting it to demo execution, build a broker-pending-order manager with durable order IDs, idempotent placement, amend/cancel reconciliation, restart recovery, broker minimum-distance/freeze-level checks, stale-quote rejection, one-position/one-order invariants, account risk caps, and audit logs. A plan must be revalidated immediately before placement and every time it is modified.

## Required research before enabling pending orders
1. Use only information available at the decision timestamp; all setup/context candles must be closed.
2. Replay historical M1 data with higher-timeframe context and nested base zones, simulating the actual order trigger, expiration, cancellation, gap/slippage, and intrabar stop/target ordering.
3. Compare market-at-confirmation versus limit-on-retest versus stop-on-breakout, separately by direction, setup type, volatility regime, session, and timeframe.
4. Use chronological walk-forward and untouched holdout periods. Deduct observed Alpari spread, commission, slippage and missed fills; report expectancy, profit factor, drawdown, trade count, fill rate, adverse selection, and cancellation rates.
5. Run shadow signals, then demo forward orders with reconciliation and restart tests. Promote only after stable out-of-sample and forward-demo results.

## Current status
The planner is implemented as a proposal-only component and has unit tests. It is not yet wired into the live/demo execution loop and has not been evaluated on historical data. Real-money execution remains disabled; no claim of predictive edge or profitability is made.

## Hierarchical parent/child behavior engine (implementation update)

Added src/Decision/Intelligence/hierarchical_base_behavior_engine.py and exposed it through DecisionEngine.generate_hierarchical_base_plan(...).

The engine:
- requires a confirmed lower-timeframe M15/M5 child base and a time/price-contained higher-timeframe parent;
- checks parent/child departure direction alignment;
- uses only prior outcome labels whose explicit label_end_time is before the learning cutoff;
- groups historical transition outcomes by child timeframe, child Base type, parent timeframe and alignment;
- fails closed when the sample is small, the observed continuation rate is weak, no destination Base is known, or the conditional-order geometry/cost gate fails;
- returns an order proposal only; it never submits, modifies, or cancels an MT5 order.

The transition labeler now adds label_end_time, parent_timeframe, and parent_aligned fields. label_end_time is deliberately conservative: the full forward labeling horizon must have closed before the example is eligible for learning.

Important limits:
- This is an initial, rule-based learning/decision bridge, not a calibrated ML model.
- Current learning labels are transition proxies (continuation/next-base vs reversal/failed close-back), not a complete broker-costed net-R distribution. No profitability claim is made.
- The legacy generate_professional_signal path has not been replaced or silently overridden. The new method is an explicit Base-based decision path until historical validation and demo-forward evidence justify making it canonical.
- No live/demo order execution is connected. Execution remains disabled.


## Base-primary decision path and M1 timing gate

AutonomousDemoTrader.run_once() now uses hierarchical Base analysis as its primary decision path by default (YARTRADER_BASE_BEHAVIOR_PRIMARY can explicitly disable this path for controlled comparison). It fetches closed H4/H1/M15/M5/M1 bars, detects confirmed Base departures, loads the research model artifact for analysis, and records the parent/child/M1 decision to the audit log.

The primary path is intentionally **proposal-only**. It returns WAIT or PROPOSAL_ONLY and prevents the legacy market-order strategy from bypassing the Base research gate. It does not place, amend, or cancel pending orders. If a position is already open, the path does not automatically close/reverse it; the existing broker SL/TP remain in place while live Base-based exit management is still unimplemented.

Parent context now has two explicit relations:
- NESTED: child Base is contained in the parent Base's time/price structure.
- TRANSITION_CONTEXT: a later child Base is in the corridor of a previously confirmed higher-timeframe Base.

The live decision also requires a fresh direction-aligned M1 Base departure after the M15/M5 setup, while price remains beyond the child zone. The walk-forward research runner is being aligned to the same sequence: parent/child setup -> M1 confirmation -> pending limit retest -> structural stop -> known destination Base or a disclosed 3R fallback -> wave-style exit. Historical results remain research-only; the model artifact is never a broker authorization.


## Latest M1-confirmed walk-forward run (research-only)

The current full multi-timeframe scan used 600,000 M1 bars, with sampled Base detection on all timeframes. It found 4,200 M15 and 7,665 M5 child events with aligned parent context, but only 106 M15 and 71 M5 setups had the required M1 trigger. After retest-fill and geometry checks, 47 independent event outcomes remained (28 M15, 19 M5).

The outcome proxy showed 68.09% positive net-R outcomes, mean net_R proxy +0.1543R, and profit-factor proxy 1.8207 at a round-trip cost sensitivity of 0.05 ATR. These are not broker-costed or portfolio-constrained results and overlap is possible. More importantly, **zero walk-forward decisions passed the minimum-sample gate** and zero learned groups met all gates; the largest exact group had only five outcomes. Therefore this is insufficient evidence for activation and the generated model stays marked RESEARCH_ONLY_NOT_ACTIVATED.

The report and research model are written to:
- runtime_logs/mt5_gold_history_full/hierarchical_base_pending_walkforward.json
- runtime_logs/mt5_gold_history_full/hierarchical_base_behavior_model_research.json
