# YarTrader DEMO restart plan

## Scope and safety
- Never enable LIVE trading. Keep the MT5 DEMO-only safety gate and existing 8% daily loss ceiling.
- Daily drawdown uses YarTrader-owned MT5 deal/position PnL only (magic 143056 or YarTrader comment), divided by current wallet equity. Balance/credit/deposit/withdrawal operations and manual trades are not PnL.
- Recompute wallet risk basis from min(current balance, current equity) before each order. Per-trade risk target and hard ceiling are 1.0%, shared across enabled symbols and execution modes; round lots down to broker volume step and refuse the order if broker minimum lot exceeds budget. No fixed 0.01-lot cap.
- Reset only generated trading/learning/backtest artifacts and old kill-switch state. Preserve source, configs, secrets, account/auth/business data, and security/audit records.

## Execution sequence
1. Patch risk accounting and all final DEMO execution gates.
2. Compile and run focused safety, risk, market-session, and isolation tests.
3. Stop YarTrader and historical backtest/session workers before cleanup.
4. Purge allowlisted old generated trading/learning data and risk state; preserve non-trading app state and security audit logs. If NTFS corruption prevents deleting the artifact store, quarantine it and retry after filesystem repair.
5. Restart service; verify health, DEMO mode, LIVE disabled, new risk state and worker cycle logs.
6. Report whether an order actually executed; never force an order just to make the trade counter non-zero.

## One-time reset tool
Run python scripts/reset_demo_trading_state.py --apply only while service/workers are stopped.
