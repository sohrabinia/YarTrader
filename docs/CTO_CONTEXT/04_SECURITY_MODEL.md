# 04 - Security Model & Fail-Closed Guardrails

## Core Guardrail Invariants
1. **Hard-Locked Demo Execution**:
   - `LIVE_TRADING_ENABLED = False` is hard-locked across `DemoExecutionGate`, `MetaTraderSafetyGate`, and `RealMT5BrokerAdapter`.
   - Real MT5/MT4 accounts (`is_real == True` or `trade_mode == 0`) trigger immediate rejection and raise `ValidationException`.

2. **Daily 8% Loss Protection Kill-Switch**:
   - Implemented in `src/Risk/Services/daily_loss_kill_switch.py`.
   - Captures an immutable account equity baseline once per trading session at `01:35 Iran local time` (`Asia/Tehran` / UTC+3:30).
   - If cumulative daily loss exceeds 8.00% relative to the active session baseline, entry permissions are immediately revoked (`allowed = False`).
   - Uninitialized or invalid account equity fails closed.

3. **Account Equity Fail-Closed Policy**:
   - `ResearchWorker` position sizing and execution dispatch require explicit, non-zero, non-NaN broker account equity (`acc_info.get('equity')`).
   - If account equity is missing or non-positive, execution fails closed with `sizing_call_count = 0` and zero default $10,000 equity fallbacks.

4. **Exact Risk Volume & Broker Metadata Validation**:
   - `RealMT5BrokerAdapter` validates requested order volume against broker symbol limits (`volume_min`, `volume_max`, `volume_step`).
   - Silent volume clamping or rounding is eliminated; non-compliant volumes trigger `ValidationException`.
   - Disconnected broker queries return explicit `None` (`UNKNOWN`) position states rather than flat `[]`.
