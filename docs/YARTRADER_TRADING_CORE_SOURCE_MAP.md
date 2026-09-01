# YARTRADER TRADING CORE SOURCE MAP
**Repository Source Map Mapping Trading Core Categories & Rules to Exact Code Locations**
**Classification: READ-ONLY FORENSIC SOURCE MAP**

---

## REPOSITORY SOURCE MAP

This document maps every trading category, component, function, and parameter to its exact relative file path, class/function name, line number, and structural authority.

| Category / Rule | File Path | Class / Function | Line Numbers | Description & Authority |
| --------------- | --------- | ---------------- | ------------ | ----------------------- |
| **Decision Engine Core** | `src/Decision/Intelligence/engine.py` | `DecisionIntelligenceEngine.evaluate_intelligence_context` | Lines 50–120 | Orchestrates intelligence context, evaluates signals, risk, and portfolio limits to produce final `DecisionState`. Final decision authority. |
| **Professional Signal Engine** | `src/Decision/Intelligence/professional_signal_engine.py` | `ProfessionalSignalEngine.generate_unified_signal` | Lines 120–220 | Synthesizes multi-timeframe context, strategy candidates, and pattern memory into a unified `ProfessionalSignal` (`BUY`/`SELL`/`WAIT`). |
| **Timeframe Selector** | `src/Decision/Intelligence/timeframe_selector.py` | `AutomaticTimeframeSelector.select_optimal_timeframe` | Lines 10–45 | Determines primary execution timeframe (**M5** canonical default). |
| **Professional Risk Engine** | `src/Risk/Services/professional_risk_engine.py` | `ProfessionalRiskEngine.evaluate_trade_risk` | Lines 210–290 | Enforces real RR >= 1.5, expected value > 0, max spread <= 5.0 pips, and win probability >= 50%. Hard risk veto authority. |
| **Position Sizing Engine** | `src/Risk/Services/professional_risk_engine.py` | `ProfessionalRiskEngine.evaluate_equity_risk_and_position_size` | Lines 155–205 | Calculates exact lot size based on equity, risk %, net SL distance, contract size, and $7/lot commission. |
| **Effective BE Calculation** | `src/Risk/Services/professional_risk_engine.py` | `ProfessionalRiskEngine.calculate_effective_risk_free_stop` | Lines 120–150 | Computes exact cost-adjusted Break-Even price accounting for spread, commission, and slippage. |
| **Campaign Lifecycle Manager** | `src/Risk/Services/campaign_manager.py` | `CampaignLifecycleManager.create_campaign` | Lines 20–100 | Creates initial trading campaign leg with **2.0% Equity Risk**. |
| **Add-On Eligibility Gate** | `src/Risk/Services/campaign_manager.py` | `CampaignLifecycleManager.attempt_add_on_leg` | Lines 105–180 | Enforces **1.0% Equity Risk** add-on gate requiring active parent campaign and all previous legs to be effective risk-free. |
| **Reversal Handoff Manager** | `src/Risk/Services/reversal_handoff.py` | `ReversalHandoffManager.evaluate_reversal_candidate` | Lines 20–140 | Evaluates post-close fast scalp/scalp non-blind reversal candidates. |
| **Strategy Orchestrator** | `src/Intelligence/Execution/strategy_orchestrator.py` | `StrategyOrchestrator.evaluate_all_strategies` | Lines 50–120 | Orchestrates evaluation across 6 strategies (`FAST_SCALP`, `SCALP`, `DAY_TRADING`, `JUMP`, `PRICE_ACTION_RTM`, `FRACTAL`). |
| **Fast Scalp Strategy** | `src/Intelligence/Execution/strategy_orchestrator.py` | `StrategyOrchestrator._evaluate_fast_scalp` | Lines 170–215 | M1/M5 EMA5/EMA13 setup; 1.5x SL TP multiplier; max spread 1.5 pips; min confidence 60%. |
| **Scalp Strategy** | `src/Intelligence/Execution/strategy_orchestrator.py` | `StrategyOrchestrator._evaluate_scalp` | Lines 220–265 | M5/M15 FVG/OB mitigation setup; 2.0x SL TP multiplier; max spread 2.5 pips; min confidence 65%. |
| **Day Trading Strategy** | `src/Intelligence/Execution/strategy_orchestrator.py` | `StrategyOrchestrator._evaluate_day_trading` | Lines 270–318 | M15/H1/H4 trend sweep setup; 2.5x SL TP multiplier; max spread 3.0 pips; min confidence 70%. |
| **Jump Strategy** | `src/Intelligence/Execution/strategy_orchestrator.py` | `StrategyOrchestrator._evaluate_jump` | Lines 320–372 | M1/M5 sudden volume spike setup; 2.5x SL TP multiplier; max spread 2.0 pips; min confidence 60%. |
| **Price Action RTM Strategy** | `src/Intelligence/Execution/strategy_orchestrator.py` | `StrategyOrchestrator._evaluate_price_action_rtm` | Lines 375–430 | M5/M15 QML/compression setup; 2.0x SL TP multiplier; max spread 2.5 pips; min confidence 68%. |
| **Fractal Pattern Strategy** | `src/Intelligence/Execution/strategy_orchestrator.py` | `StrategyOrchestrator._evaluate_fractal` | Lines 432–485 | Pattern memory match setup; projected pattern TP; max spread 2.0 pips; min confidence 70%. |
| **Portfolio Risk Intelligence** | `src/Intelligence/Execution/portfolio.py` | `PortfolioRiskIntelligenceEngine.calculate_portfolio_risk` | Lines 25–130 | Evaluates total heat (max 6.0%), strategy ceiling (max 3.0%), and single trade risk (max 0.5% in advisory planner). |
| **Execution Intelligence Planner**| `src/Intelligence/Execution/execution_planner.py` | `ExecutionIntelligencePlanner.generate_execution_plan` | Lines 15–70 | Synthesizes narrative, liquidity, zones, and alignment into advisory execution plans (`BUY`/`SELL`/`WAIT`/`AVOID`). |
| **Demo Execution Safety Gate** | `src/Execution/Safety/demo_execution_gate.py` | `DemoExecutionGate.verify_demo_execution_eligibility` | Lines 30–145 | Enforces `LIVE_TRADING_ENABLED = False`, demo_mode check, directional SL/TP checks, and position exclusivity. SRE hard stop. |
| **Demo Execution Engine** | `src/Execution/Services/demo_execution_engine.py` | `DemoExecutionEngine.execute_demo_decision` | Lines 40–145 | Receives verified decisions, logs execution evidence, and dispatches orders to broker adapter. |
| **Real MT5 Broker Adapter** | `src/Execution/Adapters/mt5_adapter.py` | `RealMT5BrokerAdapter.place_order` | Lines 150–220 | Handles direct MetaTrader 5 terminal IPC communication (`mt5.order_send`). Broker boundary. |
| **Market Session Engine** | `src/Execution/Services/market_session_engine.py` | `MarketSessionEngine.evaluate_market_session` | Lines 40–160 | Enforces session hours, 120-second minimum hold time, and 15-minute pre-close EOD flattening. |
| **Trading Style Selector** | `src/Research/Brain/trading_style.py` | `TradingStyleSelector.select_style` | Lines 50–75 | Maps timeframe and spread to trading style profiles (`FAST_SCALPING`, `SCALPING`, `INTRADAY`, `SWING`). |
| **Fractal Pattern Memory** | `src/Research/Brain/fractal_memory.py` | `FractalPatternMemory.record_pattern_outcome` | Lines 50–90 | Stores pattern outcomes, updates success rate (`wins / frequency`), and updates confidence weight. |
| **Market Memory System** | `src/Research/Brain/memory.py` | `MarketMemorySystem.save_patterns` / `load_patterns` | Lines 100–180 | Single canonical memory persistence authority managing 4 layers (Events, Experiences, Patterns, Concepts). |
| **Multi-Timeframe Context** | `src/Research/Brain/multi_timeframe_context.py` | `MultiTimeframeContextEngine.analyze_context` | Lines 30–110 | Analyzes market structure alignment across M1, M5, M15, H1, H4. |
| **Backtest & Learning Engine** | `src/Application/Backtesting/backtest_learning_engine.py` | `BacktestAndLearningEngine.run_backtest_with_learning` | Lines 120–200 | Zero look-ahead backtester evaluating post-trade learning feedback and win rates. |
| **Research Worker** | `app/workers/research_worker.py` | `ResearchWorker._run_research_cycle` | Lines 180–280 | Background polling loop executing research cycles, signal generation, and demo execution on live MT5 feeds. |

---

## CONCLUSION
All mapped file paths, class/function definitions, line numbers, and rule thresholds represent the exact, audited code state of YarTrader HEAD.
