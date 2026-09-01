# YARTRADER TRADING CORE CONTRADICTION MATRIX
**Forensic Audit of Conflicting Rules, Parameters, and Thresholds across YarTrader Core Modules**
**Classification: READ-ONLY FORENSIC ANALYSIS**

---

## CONTRADICTION MATRIX

The following table documents every observed rule conflict in the YarTrader repository, identifying both sources, runtime paths, execution authority, and whether the contradiction materially affects trading decisions.

| ID | Category | Source A (Rule A) | Source B (Rule B) | Runtime Path | Winning Rule / Authority | Material Impact on Trading? |
| -- | -------- | ----------------- | ----------------- | ------------ | ------------------------ | --------------------------- |
| **C-01** | **Single Trade Risk %** | `src/Intelligence/Execution/portfolio.py:14`<br>`max_risk_per_trade_pct = 0.5%` | `src/Risk/Services/campaign_manager.py:50`<br>`risk_pct = 2.0%` | Campaign Creation & Execution via `ResearchWorker` | **2.0% Risk Wins** in campaign execution.<br>`PortfolioRiskIntelligenceEngine` (0.5%) is advisory in execution planner only. | **YES.** Actual position lot sizing uses 2.0% equity risk per trade, four times higher than the advisory planner's 0.5% ceiling. |
| **C-02** | **Default Risk Engine Risk %** | `src/Risk/Services/professional_risk_engine.py:220`<br>`risk_percentage = 1.0%` | `src/Risk/Services/campaign_manager.py:50`<br>`risk_pct = 2.0%` | Campaign Manager invoking Risk Engine Position Sizing | **2.0% Risk Wins** when called explicitly by Campaign Lifecycle Manager. Default 1.0% is used if un-specified. | **NO (Resolved at Runtime).** Explicit parameter passing in `CampaignLifecycleManager` overrides the function default. |
| **C-03** | **Minimum Risk/Reward (RR)** | `src/Intelligence/Execution/strategy_orchestrator.py:202`<br>`FAST_SCALP RR = 1.5` / `DAY_TRADING RR = 2.5` | `src/Risk/Services/professional_risk_engine.py:265`<br>Global `Real RR >= 1.5` Gate | Decision Pipeline Risk Check | **Global Real RR >= 1.5 Wins.** Strategy-specific TP target multipliers set the initial target (1.5x, 2.0x, 2.5x), but any signal meeting Net Real RR >= 1.5 passes the global risk gate. | **NO.** Strategy-specific multipliers naturally generate candidates with RR >= strategy target; risk engine enforces baseline >= 1.5. |
| **C-04** | **Trading Style Naming** | `src/Research/Brain/trading_style.py:4`<br>`TradingStyle.FAST_SCALPING` / `SCALPING` | `src/Intelligence/Execution/strategy_orchestrator.py:15`<br>`FAST_SCALP` / `SCALP` | Unified Signal Generation & Style Selection | **String Mapping in `professional_signal_engine.py`**. | **NO.** Map explicitly converts `FAST_SCALP` -> `FAST_SCALPING` before style query. |
| **C-05** | **Win Rate vs Win Probability** | `src/Application/Backtesting/backtest_learning_engine.py:181`<br>Calculated historical closed win rate | `src/Risk/Services/professional_risk_engine.py:220`<br>Hardcoded default `win_probability = 0.55` (55%) | Risk Engine Expected Value Calculation | **Hardcoded 0.55 Wins** in `evaluate_trade_risk()`. | **YES.** Expected Value calculation currently assumes a fixed 55% win rate regardless of actual historical strategy win rate, unless overridden by caller. |
| **C-06** | **Historical Pattern Success Rate vs Strategy Win Rate** | `src/Research/Brain/fractal_memory.py:76`<br>`pattern.success_rate = wins / frequency` | `src/Strategy/Evaluation/performance_analytics.py:53`<br>`strategy.win_rate = win_count / total_trades` | Memory Matching vs Analytics | **Separate Concepts.** Pattern success rate evaluates local geometric setup matches; strategy win rate evaluates total PnL execution outcomes. | **NO.** Both serve distinct architectural functions without runtime collision. |
| **C-07** | **Max Portfolio Heat** | `src/Intelligence/Execution/portfolio.py:10`<br>`max_heat_pct = 6.0%` | `src/Risk/Services/professional_risk_engine.py:12`<br>`max_portfolio_risk_pct = 6.0%` | Portfolio Risk Checking | **Identical Threshold (6.0%).** Both components enforce 6.0% max portfolio equity heat. | **NO.** Consistent across both advisory and execution boundaries. |
| **C-08** | **Maximum Spread Limit** | `src/Risk/Services/professional_risk_engine.py:270`<br>`max_spread_pip = 5.0 pips` (Global Hard Veto) | `src/Research/Brain/trading_style.py:19`<br>`FAST_SCALPING max_allowed_spread_pip = 1.5 pips` | Strategy Filtering vs Global Risk Evaluation | **Both Enforced.** Strategy Orchestrator filters candidates above style spread limits (1.5 pips for fast scalp); Risk Engine blocks anything above 5.0 pips. | **NO.** Hierarchical filter behavior (stricter filter applies first). |

---

## DETAILED FORENSIC EXPLANATION OF KEY CONTRADICTIONS

### 1. Contradiction C-01: Single Trade Risk % (0.5% vs 2.0%)
- **Source A:** `src/Intelligence/Execution/portfolio.py` defines `max_risk_per_trade_pct = 0.5%`. This class (`PortfolioRiskIntelligenceEngine`) acts as an advisory planner for portfolio risk calculation and flags trades risking > 0.5% as violations.
- **Source B:** `src/Risk/Services/campaign_manager.py` explicitly executes initial campaign entries with `risk_pct = 2.0%` (`sizing = self.risk_engine.evaluate_equity_risk_and_position_size(..., risk_pct=2.0)`).
- **Runtime Resolution:** When trades are executed via `CampaignLifecycleManager`, position sizing is calculated using **2.0% equity risk**. If the trade is subsequently analyzed by `PortfolioRiskIntelligenceEngine`, it triggers a violation warning (`"Single trade risk exceeds max limit of 0.5% equity"`), but execution has already occurred under campaign rules.

### 2. Contradiction C-03: Minimum Risk/Reward (1.5 vs 2.0 vs 2.5)
- **Source A:** `src/Intelligence/Execution/strategy_orchestrator.py` defines fixed RR multipliers per strategy (`FAST_SCALP` = 1.5, `SCALP` = 2.0, `DAY_TRADING` = 2.5, `JUMP` = 2.5, `PRICE_ACTION_RTM` = 2.0, `FRACTAL` = 2.0).
- **Source B:** `src/Risk/Services/professional_risk_engine.py` enforces a single global minimum gate: `if real_rr < 1.5: rejection_reasons.append(...)`.
- **Runtime Resolution:** The strategy orchestrator sets target TP based on its strategy-specific multiplier, which creates candidate trades meeting that specific RR ratio. When passed to `ProfessionalRiskEngine`, the engine calculates net real RR (accounting for spread, commission, and slippage). If net real RR is >= 1.5, the trade passes the risk engine, regardless of whether the original strategy had a 2.0 or 2.5 target.

### 3. Contradiction C-05: Win Rate Parameterization in Risk Engine
- **Source A:** `src/Application/Backtesting/backtest_learning_engine.py` dynamically calculates win rates from actual closed trades (`win_rate = wins / total_closed * 100`).
- **Source B:** `src/Risk/Services/professional_risk_engine.py:220` sets a hardcoded default keyword argument `win_probability: float = 0.55`.
- **Runtime Resolution:** When `evaluate_trade_risk()` is called without passing a dynamically computed `win_probability` from historical memory, the risk engine calculates Expected Value using `0.55 * Potential Reward - 0.45 * Target Risk`.

---

## CONCLUSION
No source code changes or fixes are permitted under this audit directive. The above contradictions represent the exact current state of the YarTrader repository.
