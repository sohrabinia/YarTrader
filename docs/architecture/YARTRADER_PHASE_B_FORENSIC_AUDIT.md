# YARTRADER PHASE B FORENSIC AUDIT REPORT

**Document Version:** `YARTRADER_PHASE_B_AUDIT_V1.0`
**Master Roadmap Version:** `YARTRADER_MASTER_ROADMAP_V1`
**Date:** 2026-08-27
**Auditor:** Lead Technical Orchestrator (Jules)

---

## 1. EXECUTIVE SUMMARY

This forensic audit evaluates the existing YarTrader risk management, position sizing, campaign tracking, and execution safety mechanisms against the requirements of **Phase B (Risk, Position Sizing, Campaign & Pyramiding)** defined in `YARTRADER_MASTER_ROADMAP_V1`.

---

## 2. SECTION 86 FORENSIC AUDIT (20 MANDATORY QUESTIONS)

### Q1: Where is the authoritative Risk Engine?
- **Location:** `src/Risk/Services/professional_risk_engine.py` (`ProfessionalRiskEngine`).
- **Integrations:** Integrated in `src/Risk/Services/prop_challenge_engine.py`, `src/Decision/Intelligence/professional_signal_engine.py`, and `src/Execution/Safety/demo_execution_gate.py`.
- **Classification:** `PASS` (Authoritative component identified).

### Q2: What is its current contract?
- **Signature:** `ProfessionalRiskEngine.evaluate_trade_risk(symbol, direction, entry_price, stop_loss, take_profit, account_balance=10000.0, risk_percentage=1.0, spread_pip=1.0, commission_per_lot=7.0, estimated_slippage_pip=0.5, win_probability=0.55) -> RiskEvaluationResult`
- **Output:** `RiskEvaluationResult` containing `is_valid`, `direction`, `entry_price`, `stop_loss`, `take_profit`, `risk_amount_usd`, `potential_reward_usd`, `spread_cost_pip`, `commission_usd`, `slippage_pip`, `gross_rr`, `real_rr`, `win_probability`, `expected_value`, `rejection_reason`.
- **Rules:** Enforces `win_probability >= 0.50`, `real_rr >= 1.5`, `expected_value > 0`, and `spread_pip <= 5.0`.
- **Classification:** `PARTIAL` (Solid foundation, but lacks 2% Equity calculation, 1% Add-On gating, and Effective BE contracts).

### Q3: Where is position sizing implemented?
- **Location:** `ProfessionalRiskEngine` calculates `target_risk_usd = account_balance * (risk_percentage / 100.0)`. Lot size calculation is distributed across `src/Execution/` wrappers.
- **Classification:** `PARTIAL` (Calculates USD risk, but position size is not unified with Equity and broker contract specs).

### Q4: How is account risk currently calculated?
- **Current Logic:** `target_risk_usd = account_balance * (risk_percentage / 100.0)`.
- **Gap:** Uses account balance rather than **account equity** and does not account for existing open position margin/risk exposure dynamically.
- **Classification:** `PARTIAL`.

### Q5: How is stop distance represented?
- **Current Logic:** `raw_sl_distance = abs(entry_price - stop_loss)`. Cost distance `cost_distance = (spread_pip + estimated_slippage_pip) * pip_size` is added to produce `net_sl_distance`.
- **Classification:** `PASS`.

### Q6: How are spread and commission handled?
- **Current Logic:** Spread (`spread_pip`) and estimated slippage (`estimated_slippage_pip`) reduce TP distance and expand SL distance. Commission is tracked in USD per lot.
- **Classification:** `PASS`.

### Q7: How is slippage represented?
- **Current Logic:** Represented in pips as `estimated_slippage_pip` (default 0.5 pips) and added directly to transaction friction in `evaluate_trade_risk()`.
- **Classification:** `PASS`.

### Q8: How is effective break-even calculated?
- **Current Logic:** No formal `calculate_effective_be()` helper accounting for spread, commission, slippage, and safety buffer.
- **Classification:** `MISSING`.

### Q9: Does campaign/leg already exist?
- **Current Logic:** Positions are tracked as isolated tickets/orders. No `TradeCampaign` or `CampaignLeg` multi-leg campaign container.
- **Classification:** `MISSING`.

### Q10: Does pyramiding already exist?
- **Current Logic:** Multi-position placement exists in demo runners, but lacks structured leg-based pyramiding with risk bounds.
- **Classification:** `MISSING`.

### Q11: Does add-on already exist?
- **Current Logic:** No formal 1% add-on risk gating mechanism linked to risk-free status of previous legs.
- **Classification:** `MISSING`.

### Q12: How is margin calculated?
- **Current Logic:** Broker adapters evaluate leverage and margin requirements during order check.
- **Classification:** `PARTIAL`.

### Q13: How is free margin used?
- **Current Logic:** Evaluated retroactively at order execution time rather than upfront in the risk sequence.
- **Classification:** `PARTIAL`.

### Q14: How is portfolio exposure calculated?
- **Current Logic:** Single-asset max exposure checks exist in `src/Risk/evaluators.py`. Portfolio correlation risk checks are not unified with trade entry gates.
- **Classification:** `PARTIAL`.

### Q15: What happens after restart?
- **Current Logic:** MT5 position reconciliation queries open positions via `mt5.positions_get()`, but multi-leg campaign state is not persisted.
- **Classification:** `PARTIAL`.

### Q16: What prevents duplicate orders?
- **Current Logic:** Ticket checks and order comment normalization (`YarOpen` / `YarClose`) in `mt5_adapter.py` and `demo_execution_gate.py`.
- **Classification:** `PASS`.

### Q17: What prevents add-on before risk-free?
- **Current Logic:** No current check prevents opening additional positions when Leg 1 is still at risk.
- **Classification:** `MISSING`.

### Q18: What happens at EOD?
- **Current Logic:** Session cutoff enforcement flattens open positions (`OPEN_POSITIONS = 0`) at session close.
- **Classification:** `PASS`.

### Q19: Which existing tests already prove these properties?
- **Tests:** `tests/test_risk.py`, `tests/YarTrader.Tests/Execution/test_real_mt5_adapter.py`, `tests/YarTrader.Tests/Services/test_prop_challenge_api.py`, `tests/runtime/test_service_host.py`.
- **Classification:** `PASS`.

### Q20: Which properties are missing?
- **Summary of Missing/Partial Requirements:**
  1. Authoritative 2% Initial Risk calculated on Account Equity.
  2. Authoritative 1% Add-On Risk Gate strictly requiring `PREVIOUS_LEG_EFFECTIVE_RISK_FREE == True`.
  3. Effective Risk-Free calculation accounting for spread, commission, slippage, and safety buffer.
  4. Structured `TradeCampaign` and `CampaignLeg` data models and lifecycle manager.
  5. Node / Base Settlement Rule closing campaigns at structural target nodes.
  6. Mandatory Free Margin sequence: Risk Budget -> Stop Distance -> Position Size -> Margin Check -> Free Margin Check -> Portfolio Exposure -> Execution.
  7. Correlation-aware portfolio risk aggregation.

---

## 3. PHASE B CLASSIFICATION MATRIX

| Property | Status |
|---|---|
| Authoritative Risk Engine Base | `PASS` |
| 2% Equity Initial Risk Calculation | `PARTIAL` |
| 1% Add-On Risk Gating | `MISSING` |
| Effective Risk-Free Calculation | `MISSING` |
| Trade Campaign & Leg Data Model | `MISSING` |
| Node / Base Settlement Rule | `MISSING` |
| Free Margin Sequence | `PARTIAL` |
| Portfolio Correlation Control | `PARTIAL` |
| Restart Reconciliation | `PARTIAL` |
| EOD Flatten Safety Invariant | `PASS` |
