# YARTRADER TRADING CORE FORENSIC RULEBOOK
**Authoritative forensic rulebook documenting the active, legacy, and shadow trading behavior of YarTrader**
**Classification: READ-ONLY AUDIT REPORT**
**Repository Version / Commit: YarTrader v7.0 (HEAD: `5b7e817d44f43131a8ce68193a36bcbf2fdbd0fc`)**

---

## 1. TRADING DECISION PIPELINE

The YarTrader decision pipeline progresses sequentially from raw ticks/candles up to broker order dispatch. The complete chain with exact components, inputs, outputs, and decision authority is detailed below:

### Pipeline Stages
1. **Market Data Ingestion & Quality Control**
   - **File:** `src/Data/MarketData/Normalization/validator.py` (`MarketDataValidator`), `src/Data/MarketData/Normalization/quality_checker.py` (`DataQualityChecker`)
   - **Input:** Raw tick/bar feeds (OHLCV, Bid, Ask, Spread)
   - **Output:** Validated `MarketDataPoint` or `CandleData`
   - **Authority:** Data Normalization Boundary (Vetoes corrupt or gapped price data)
   - **Thresholds:** Max bid/ask spread > 5.0 pips triggers data warning/rejection.

2. **Research & Multi-Timeframe Structure Analysis**
   - **File:** `src/Research/Brain/multi_timeframe_context.py` (`MultiTimeframeContextEngine`), `src/Research/Brain/fractal_base_detection_engine.py` (`FractalBaseDetectionEngine`)
   - **Input:** Candle series across M1, M5, M15, H1, H4
   - **Output:** Market structure alignment (`BULLISH`, `BEARISH`, `NEUTRAL`), Order Blocks, FVGs (Fair Value Gaps), Swing Highs/Lows
   - **Authority:** Research Brain

3. **Pattern Memory & Historical Evidence Matching**
   - **File:** `src/Research/Brain/fractal_memory.py` (`FractalPatternMemory`), `src/Intelligence/Execution/similarity.py` (`StructureSimilarityEngine`)
   - **Input:** Current market vector (volatility, momentum, swing geometry)
   - **Output:** Pattern match record (`success_rate`, `confidence_weight`, `epistemic_success_rate`)
   - **Authority:** Memory Engine (Advisory to Strategy Orchestrator & Professional Signal Engine)

4. **Trading Style Selection**
   - **File:** `src/Research/Brain/trading_style.py` (`TradingStyleSelector`)
   - **Input:** Timeframe, current spread in pips
   - **Output:** Selected `TradingStyle` (`FAST_SCALPING`, `SCALPING`, `INTRADAY`, `SWING`), target RR, max allowed spread
   - **Authority:** Style Selector (Advisory / Constraint Provider)

5. **Strategy Candidate Generation (Strategy Orchestrator)**
   - **File:** `src/Intelligence/Execution/strategy_orchestrator.py` (`StrategyOrchestrator`)
   - **Input:** Candles dict, symbol, timeframe, spread_pip
   - **Output:** `StrategyCandidate` list across 6 strategies (`FAST_SCALP`, `SCALP`, `DAY_TRADING`, `JUMP`, `PRICE_ACTION_RTM`, `FRACTAL`)
   - **Authority:** Strategy Orchestrator (Evaluates candidate setups)

6. **Unified Professional Signal Generation**
   - **File:** `src/Decision/Intelligence/professional_signal_engine.py` (`ProfessionalSignalEngine`)
   - **Input:** Symbol, candles_m1, candles_m5, candles_h1, spread_pip, account_balance
   - **Output:** `ProfessionalSignal` containing direction (`BUY`, `SELL`, `WAIT`), entry, SL, TP, confidence, risk evaluation
   - **Authority:** Unified Signal Generator (Converts candidates to unified signal)

7. **Deterministic Risk Evaluation & Position Sizing**
   - **File:** `src/Risk/Services/professional_risk_engine.py` (`ProfessionalRiskEngine`), `src/Risk/Services/campaign_manager.py` (`CampaignLifecycleManager`)
   - **Input:** Direction, Entry, SL, TP, account equity, free margin, win_probability (default 0.55)
   - **Output:** `RiskEvaluationResult` & `PositionSizingResult` (Calculates lot size, checks real RR >= 1.5, expected value > $0.00, spread <= 5.0 pips)
   - **Authority:** Deterministic Risk Engine (HARD VETO AUTHORITY)

8. **Portfolio Risk Intelligence Boundary**
   - **File:** `src/Intelligence/Execution/portfolio.py` (`PortfolioRiskIntelligenceEngine`)
   - **Input:** Active trades, virtual balance, strategy exposure
   - **Output:** Portfolio Heat %, drawdown risk, approval flag
   - **Authority:** Portfolio Intelligence (HARD VETO: Max portfolio heat 6.0%, max single trade risk 0.5% in advisory planner / 2.0% in campaign manager)

9. **Decision Engine State Approval**
   - **File:** `src/Decision/Intelligence/engine.py` (`DecisionIntelligenceEngine`)
   - **Input:** `DecisionIntelligenceContext` (Signal, Risk, Portfolio)
   - **Output:** `DecisionIntelligenceReport` with final `DecisionState` (`APPROVED`, `NO_ACTION`, `REJECTED`, `REVIEW_REQUIRED`)
   - **Authority:** Decision Engine Core

10. **Demo / Runtime Execution Safety Gate**
    - **File:** `src/Execution/Safety/demo_execution_gate.py` (`DemoExecutionGate`)
    - **Input:** `OrderRequest` (symbol, order_type, entry_price, sl, tp, volume)
    - **Output:** Verification status (Checks demo_mode == True, `LIVE_TRADING_ENABLED == False`, SL/TP directional orientation, position exclusivity)
    - **Authority:** SRE Execution Gate (FINAL HARD STOP PRIOR TO MT5 IPC DISPATCH)

11. **MT5 Execution Boundary**
    - **File:** `src/Execution/Services/demo_execution_engine.py` (`DemoExecutionEngine`), `src/Execution/Adapters/mt5_adapter.py` (`RealMT5BrokerAdapter`)
    - **Input:** Verified `OrderRequest`
    - **Output:** `OrderResponse` (Ticket, status "Placed", "Failed", "REJECTED")
    - **Authority:** Broker IPC Boundary

---

## 2. STRATEGIES

YarTrader implements 6 distinct strategy evaluation engines inside `src/Intelligence/Execution/strategy_orchestrator.py` (`StrategyOrchestrator`).

| Strategy ID | Strategy Name | Active Status | Timeframes | Direction Logic | Entry Trigger | SL Logic | TP Logic | RR Requirement | Min Confidence | Spread Ceil |
| ----------- | ------------- | ------------- | ---------- | --------------- | ------------- | -------- | -------- | -------------- | -------------- | ----------- |
| `FAST_SCALP` | Fast Scalp | Active | M1, M5 | M1 Trend + Structure | EMA5/EMA13 crossover or M1 breakout | Recent Swing Low/High (Min 3 pips, Max 15 pips) | Fixed 1.5x SL Distance | 1.5 | 60.0% | 1.5 pips |
| `SCALP` | Scalp | Active | M5, M15 | M5 Market Structure Break | Fair Value Gap (FVG) / Order Block mitigation | Swing Low/High + 2 pip buffer | Fixed 2.0x SL Distance | 2.0 | 65.0% | 2.5 pips |
| `DAY_TRADING` | Day Trading | Active | M15, H1, H4 | Multi-timeframe trend (H1 + H4 alignment) | Liquidity Sweep + Displacement | Structure High/Low beyond sweep | Key HTF Liquidity Zone / 2.5x SL Distance | 2.5 | 70.0% | 3.0 pips |
| `JUMP` | Jump | Active | M1, M5 | Sudden Volatility Spike | Volume spike > 2.0x 20-bar avg + Directional Candle | Spike base / High-Low bounds | 2.5x SL Distance | 2.5 | 60.0% | 2.0 pips |
| `PRICE_ACTION_RTM` | Price Action RTM | Active | M5, M15, H1 | Read the Market (RTM) Compress & Quasimodo (QML) | QML Level retest / Compression breakout | Above/below QML apex + buffer | Next Unmitigated FVG / Supply-Demand Zone | 2.0 | 68.0% | 2.5 pips |
| `FRACTAL` | Fractal Pattern | Active | M5, M15, H1 | Historical Pattern Match | Pattern Similarity Score >= 70.0% | Structural Fractal High/Low | Projected Pattern Target | 2.0 | 70.0% | 2.0 pips |

---

## 3. ENTRY CONDITIONS

### BUY Candidates
- **FAST_SCALP:** Fast EMA (5) > Slow EMA (13) on M1/M5 AND price > Fast EMA AND spread <= 1.5 pips.
- **SCALP:** Bullish Market Structure Break (MSB) on M5 AND unmitigated Bullish FVG or Bullish Order Block detected AND price retesting FVG/OB AND spread <= 2.5 pips.
- **DAY_TRADING:** H1 trend == BULLISH AND H4 trend == BULLISH AND M15 liquidity sweep of previous session low completed with bullish displacement candle.
- **JUMP:** Current bar volume > 2.0 * average 20-bar volume AND bar close - bar open > 1.8 * ATR(14) in bullish direction.
- **PRICE_ACTION_RTM:** Bullish Quasimodo (QML) structure formed (Lower Low followed by Higher High) AND price retesting QML level during compression.
- **FRACTAL:** Top matching fractal pattern from `FractalPatternMemory` has `expected_direction == "BUY"` AND `similarity_score >= 70.0%`.

### SELL Candidates
- **FAST_SCALP:** Fast EMA (5) < Slow EMA (13) on M1/M5 AND price < Fast EMA AND spread <= 1.5 pips.
- **SCALP:** Bearish Market Structure Break (MSB) on M5 AND unmitigated Bearish FVG or Bearish Order Block detected AND price retesting FVG/OB AND spread <= 2.5 pips.
- **DAY_TRADING:** H1 trend == BEARISH AND H4 trend == BEARISH AND M15 liquidity sweep of previous session high completed with bearish displacement candle.
- **JUMP:** Current bar volume > 2.0 * average 20-bar volume AND bar open - bar close > 1.8 * ATR(14) in bearish direction.
- **PRICE_ACTION_RTM:** Bearish Quasimodo (QML) structure formed (Higher High followed by Lower Low) AND price retesting QML level during compression.
- **FRACTAL:** Top matching fractal pattern from `FractalPatternMemory` has `expected_direction == "SELL"` AND `similarity_score >= 70.0%`.

---

## 4. ENTRY PRICE

- **Source:** Live Ask price for BUY orders, Live Bid price for SELL orders from `RealMT5BrokerAdapter.get_market_data()` (`src/Execution/Adapters/mt5_adapter.py`).
- **Rounding:** Rounded to 4 decimal places for XAUUSD / standard pairs (`round(price, 4)` in `strategy_orchestrator.py` and `professional_signal_engine.py`).
- **Spread Adjustment:** Applied at risk evaluation boundary where net cost distance = `(spread_pip + estimated_slippage_pip) * pip_size`.
- **Order Mode:** Market execution in Demo/Live runtime (`ORDER_TYPE_BUY` / `ORDER_TYPE_SELL` via `mt5.order_send`).

---

## 5. STOP LOSS

- **Formula:**
  - BUY SL: `entry_price - sl_distance`
  - SELL SL: `entry_price + sl_distance`
- **Reference Source:**
  - `FAST_SCALP`: Recent swing low/high within last 10 bars on M1/M5, with minimum distance of 3.0 pips and maximum distance of 15.0 pips (`src/Intelligence/Execution/strategy_orchestrator.py:195-200`).
  - `SCALP`: Order Block low / FVG low - 2.0 pips buffer (`strategy_orchestrator.py:240-245`).
  - `DAY_TRADING`: HTF swing anchor point (`strategy_orchestrator.py:295`).
- **Min/Max Constraints:** Min SL distance = 3 pips ($0.30 on XAUUSD), Max SL distance = 50 pips ($5.00 on XAUUSD).
- **Validation Gate:** `DemoExecutionGate` (`src/Execution/Safety/demo_execution_gate.py:113-122`) enforces that BUY SL MUST be strictly below entry price and SELL SL MUST be strictly above entry price.

---

## 6. TAKE PROFIT

- **Formula & Target Sources:**
  - `FAST_SCALP`: `entry_price + (sl_distance * 1.5)` for BUY, `entry_price - (sl_distance * 1.5)` for SELL (`strategy_orchestrator.py:202`). Fixed 1.5x multiplier.
  - `SCALP`: `entry_price + (sl_distance * 2.0)` for BUY, `entry_price - (sl_distance * 2.0)` for SELL (`strategy_orchestrator.py:248`). Fixed 2.0x multiplier.
  - `DAY_TRADING` / `JUMP`: `entry_price + (sl_distance * 2.5)` for BUY, `entry_price - (sl_distance * 2.5)` for SELL (`strategy_orchestrator.py:345`). Fixed 2.5x multiplier.
- **Validation Gate:** `DemoExecutionGate` (`src/Execution/Safety/demo_execution_gate.py:117-122`) enforces that BUY TP MUST be strictly above entry price and SELL TP MUST be strictly below entry price.

---

## 7. RISK / POSITION RISK

- **Initial Single Trade Risk:**
  - `CampaignLifecycleManager` (`src/Risk/Services/campaign_manager.py:50`): **Strict 2.0% Equity Risk** per initial campaign leg.
  - `PortfolioRiskIntelligenceEngine` (`src/Intelligence/Execution/portfolio.py:14`): **0.5% Equity Risk** per trade ceiling (Advisory execution planner limit).
  - `ProfessionalRiskEngine.evaluate_trade_risk` (`src/Risk/Services/professional_risk_engine.py:240`): Default parameter `risk_percentage = 1.0%`.
  - `ResearchWorker` (`app/workers/research_worker.py:263`): Passes `risk_pct = 2.0%` to risk evaluation.
- **Add-On Risk:**
  - `CampaignLifecycleManager` (`campaign_manager.py:165`): **Strict 1.0% Equity Risk** per add-on leg.
- **Portfolio Heat Limit:** Max 6.0% total portfolio risk across active positions (`portfolio.py:10` & `professional_risk_engine.py:12`).
- **Max Strategy Exposure Ceiling:** 3.0% equity exposure ceiling per single strategy (`portfolio.py:15`).
- **Equity Source:** Real-time Account Equity queried from MT5 Terminal via `RealMT5BrokerAdapter.get_account_info()` (`src/Execution/Adapters/mt5_adapter.py`).

---

## 8. RISK / REWARD (RR)

- **Formula:**
  - Gross RR: `raw_tp_distance / raw_sl_distance`
  - Real Net RR: `net_tp_distance / net_sl_distance` where `net_tp_distance = max(0.0, raw_tp_distance - cost_distance)` and `net_sl_distance = raw_sl_distance + cost_distance` (`src/Risk/Services/professional_risk_engine.py:245-255`).
- **Minimum RR Gates:**
  - `ProfessionalRiskEngine` (`professional_risk_engine.py:265`): **Real RR >= 1.5** (HARD VETO). Trades with Real RR < 1.5 are rejected with reason `"Real RR (<1.5) < 1.5 minimum threshold."`.
  - Strategy Level:
    - `FAST_SCALP`: RR = 1.5 (`strategy_orchestrator.py:202`)
    - `SCALP`: RR = 2.0 (`strategy_orchestrator.py:248`)
    - `DAY_TRADING`: RR = 2.5 (`strategy_orchestrator.py:345`)
    - `TradingStyleSelector` (`src/Research/Brain/trading_style.py:20-44`): Defines `min_rr` profiles (FAST_SCALPING: 1.5, SCALPING: 1.5, INTRADAY: 2.0, SWING: 2.5).

### Summary Table

| Component | RR Rule | Threshold | Enforced? | Authority |
| --------- | ------- | --------: | --------- | --------- |
| `ProfessionalRiskEngine` | Net Real RR Gate | 1.5 | YES (Hard Veto) | Risk Engine Boundary |
| `StrategyOrchestrator` (`FAST_SCALP`) | Target TP Multiplier | 1.5 | YES | Strategy Candidate Engine |
| `StrategyOrchestrator` (`SCALP`) | Target TP Multiplier | 2.0 | YES | Strategy Candidate Engine |
| `StrategyOrchestrator` (`DAY_TRADING`) | Target TP Multiplier | 2.5 | YES | Strategy Candidate Engine |
| `TradingStyleSelector` | Profile Advisory RR | 1.5 - 2.5 | NO (Advisory) | Brain Style Selector |

---

## 9. CONFIDENCE

- **Calculation:** Derived from multi-timeframe alignment, order block clarity, volume confirmation, and pattern memory similarity score.
- **Minimum Thresholds:**
  - `FAST_SCALP`: Min 60.0% (`strategy_orchestrator.py:210`)
  - `SCALP`: Min 65.0% (`strategy_orchestrator.py:255`)
  - `DAY_TRADING`: Min 70.0% (`strategy_orchestrator.py:314`)
  - `ProfessionalSignalEngine`: Min signal confidence 60.0% (`professional_signal_engine.py:180`).
- **Historical Pattern Weighting:**
  - `FractalPatternMemory` (`src/Research/Brain/fractal_memory.py:78`): `confidence_weight = 0.4 + (success_rate * 0.5)`.

---

## 10. WIN RATE

YarTrader calculates 7 distinct types of win rate across different modules:

1. **Backtesting / Learning Engine Win Rate:**
   - `src/Application/Backtesting/backtest_learning_engine.py:181`
   - Formula: `(wins / total_closed * 100.0)` where breakeven trades are included in total_closed.
2. **Backtesting Simulation Win Rate:**
   - `src/Application/Backtesting/engine.py:272`
   - Formula: `(winning_trades / total_trades * 100.0)`.
3. **Shadow Trading Win Rate:**
   - `src/ShadowTrading/Engine/PredictiveShadowEngine.py:636`
   - Formula: `((prev_wins + current_win_val) / total_with_current * 100.0)`.
4. **Historical Pattern Success Rate:**
   - `src/Research/Brain/fractal_memory.py:76`
   - Formula: `record.wins / record.frequency`.
5. **Epistemic Knowledge Success Rate:**
   - `src/Research/Brain/query.py:53`
   - Formula: `(successful_experiments / total_experiments * 100.0)`.
6. **Strategy Evaluation Analytics Win Rate:**
   - `src/Strategy/Evaluation/performance_analytics.py:53`
   - Formula: `(win_count / total_trades * 100.0)`.
7. **Advisory Decision Signal Win Probability Assumption:**
   - `src/Risk/Services/professional_risk_engine.py:220`
   - Default constant: `win_probability = 0.55` (55.0%). Used to evaluate Expected Value `(0.55 * Potential Reward) - (0.45 * Target Risk)`.

---

## 11. HISTORICAL PATTERN / MEMORY

- **Layer Architecture:** `MarketMemorySystem` (`src/Research/Brain/memory.py`) maintains 4 memory layers:
  1. Events Layer (`event_logs`)
  2. Experiences Layer (`experiences.json`)
  3. Patterns Layer (`patterns_memory.json`)
  4. Concepts Layer (`concepts.json`)
- **Fractal Pattern Matching:** `FractalPatternMemory` (`src/Research/Brain/fractal_memory.py`) matches live bar vectors against stored pattern nodes.
- **Influence on Decision:**
  - Modifies signal confidence in `ProfessionalSignalEngine` (`professional_signal_engine.py:212`).
  - Does NOT directly alter position sizing or bypass risk gates.
  - Can veto trade generation in `FRACTAL` strategy if pattern similarity < 70.0%.

---

## 12. TRADING STYLE

- **Defined Profiles in `src/Research/Brain/trading_style.py` (`TradingStyleSelector`):**
  - `FAST_SCALPING`: Timeframes M1, M5 | Max Spread: 1.5 pips | Min RR: 1.5
  - `SCALPING`: Timeframes M5, M15 | Max Spread: 2.5 pips | Min RR: 1.5
  - `INTRADAY`: Timeframes M15, H1, H4 | Max Spread: 3.0 pips | Min RR: 2.0
  - `SWING`: Timeframes H4, D1, W1 | Max Spread: 4.0 pips | Min RR: 2.5
- **Naming Difference:**
  - Enum uses `FAST_SCALPING` and `SCALPING`.
  - Strategy Orchestrator strategy IDs use `FAST_SCALP` and `SCALP`.
  - Resolved via string mapping in `ProfessionalSignalEngine`.

---

## 13. TIMEFRAMES

- **Primary Execution Timeframe:** **M5** is the canonical primary execution timeframe for real-time signal evaluation (`src/Decision/Intelligence/timeframe_selector.py:15` & `app/workers/research_worker.py:220`).
- **Supported Timeframes:** M1, M5, M15, H1, H4, D1, W1 (`src/Core/timeframes.py`).
- **Multi-Timeframe Hierarchy:**
  - Structure Anchor: H1 / H4
  - Setup Confirmation: M15
  - Entry Execution Microstructure: M5 / M1

---

## 14. MARKET CONDITIONS / REGIME

- **Trend Filter:** Measured via EMA5 / EMA13 / EMA50 alignment and Swing High/Low progression (`MultiTimeframeContextEngine`).
- **Spread Gate:**
  - Hard Veto: Current spread > 5.0 pips rejects trade immediately (`ProfessionalRiskEngine.evaluate_trade_risk`).
  - Strategy Level: FAST_SCALP rejects spread > 1.5 pips; SCALP rejects spread > 2.5 pips.
- **Volatility Filter:** Measured via ATR(14) in `JumpStrategy`. ATR spike < 1.8x average rejects JUMP trades.

---

## 15. REJECTION CONDITIONS

Taxonomy of all potential rejection reasons in YarTrader:

1. `DemoExecutionGate Violation: Live trading is strictly disabled in code safety gates (LIVE_TRADING_ENABLED = False).` (Hard Safety)
2. `DemoExecutionGate Violation: Demo mode must be explicitly enabled.` (Hard Safety)
3. `DemoExecutionGate Violation: Position Exclusivity Violation. Active BUY position exists for XAUUSD.` (Position Exclusivity Guard)
4. `DemoExecutionGate Violation: Buy order SL must be below entry price.` (Directional Safety)
5. `DemoExecutionGate Violation: Buy order TP must be above entry price.` (Directional Safety)
6. `Real RR (<1.5) < 1.5 minimum threshold.` (Risk Gate)
7. `Win probability (<50.0%) < 50.0% threshold.` (Risk Gate)
8. `Expected Value (<=$0.00) <= 0.` (Risk Gate)
9. `Spread (>5.0 pips) exceeds maximum safe threshold (5.0 pips).` (Risk Gate)
10. `Insufficient free margin. Required: $X, Available: $Y.` (Margin Gate)
11. `Portfolio Heat exceeds system budget (6.0%).` (Portfolio Gate)
12. `Combined strategy exposure exceeds max ceiling (3.0%).` (Portfolio Gate)
13. `Market is closed (10018 MARKET_CLOSED).` (Broker Session Gate)
14. `Minimum hold time not satisfied (< 120 seconds).` (Session Gate)

---

## 16. MINIMUM HOLD

- **Threshold:** **120 seconds (2.0 minutes)** (`src/Execution/Services/market_session_engine.py:145` & `src/Execution/Services/session_execution_manager.py:88`).
- **Rule:** Positions opened less than 120 seconds ago cannot be closed by normal automated exit logic, EXCEPT during emergency stop-loss hit or forced EOD session flatten.

---

## 17. EOD / SESSION MANAGEMENT

- **Session Engine:** `MarketSessionEngine` (`src/Execution/Services/market_session_engine.py`)
- **Daily Pre-Close Flatten:**
  - Cutoff Time: 15 minutes before broker market close (e.g. 23:45 UTC).
  - Rule: All active positions are forcefully closed (`flatten_all_at_eod()`), and pending orders are cancelled to avoid weekend swap and gap risk.

---

## 18. BREAK-EVEN / RISK-FREE (EFFECTIVE BE)

- **Formula:** Defined in `ProfessionalRiskEngine.calculate_effective_risk_free_stop` (`src/Risk/Services/professional_risk_engine.py:120-150`):
  - `net_cost_pip = spread_pip + estimated_slippage_pip + commission_in_pips`
  - `BUY Effective BE = entry_price + (net_cost_pip * pip_size)`
  - `SELL Effective BE = entry_price - (net_cost_pip * pip_size)`
- **Definition of "Risk-Free":** A trade is legally "Effective Risk-Free" ONLY when its Stop Loss is moved to or beyond the Effective BE price, guaranteeing that even after spread, commission ($7/lot), and slippage (0.5 pips), the trade cannot result in a net financial loss.

---

## 19. ADD-ON / PYRAMIDING

- **Rules (`src/Risk/Services/campaign_manager.py:106-180`):**
  1. Parent Trade Campaign status MUST be `ACTIVE`.
  2. ALL active previous legs MUST be verified as Effective Risk-Free (`is_effective_risk_free == True`).
  3. A fresh, independent M5 trade setup MUST be confirmed by Strategy Orchestrator.
  4. Add-on position size is strictly capped at **1.0% Equity Risk** (compared to 2.0% for initial leg).
  5. Maximum active legs per campaign: 3 legs.

---

## 20. POSITION SIZING

- **Exact Formula (`src/Risk/Services/professional_risk_engine.py:180-210`):**
  $$\text{Risk Budget USD} = \text{Account Equity} \times \left(\frac{\text{Risk \%}}{100}\right)$$
  $$\text{Net SL Distance} = \text{Raw SL Distance} + \left((\text{Spread Pips} + \text{Slippage Pips}) \times \text{Pip Size}\right)$$
  $$\text{Risk Per Lot USD} = (\text{Net SL Distance} \times \text{Contract Size}) + \text{Commission Per Lot}$$
  $$\text{Calculated Lots} = \frac{\text{Risk Budget USD}}{\text{Risk Per Lot USD}}$$
  $$\text{Volume Lots} = \text{round}(\max(0.01, \text{Calculated Lots}), 2)$$

- **Symbolic Worked Example (XAUUSD):**
  - Account Equity: $10,000.00
  - Risk %: 2.0% ($200.00 Risk Budget)
  - Entry Price: $2,000.00 | Stop Loss: $1,995.00 (Raw SL Distance = $5.00)
  - Spread: 1.0 pip ($0.10) | Slippage: 0.5 pips ($0.05) | Contract Size: 100 oz | Commission: $7.00/lot
  - Net SL Distance = $5.00 + $0.15 = $5.15
  - Risk Per Lot = ($5.15 * 100) + $7.00 = $522.00
  - Calculated Lots = $200.00 / $522.00 = 0.3831 lots
  - Final Rounded Lot Size = **0.38 Lots**

---

## 21. EXECUTION BOUNDARY

- **Final Decision Object:** `DecisionIntelligenceReport` / `OrderRequest`
- **Safety Gate:** `DemoExecutionGate.verify_demo_execution_eligibility()`
- **Safety Hard Locks:** `LIVE_TRADING_ENABLED = False` hard-coded in `DemoExecutionGate` (`src/Execution/Safety/demo_execution_gate.py:55`).
- **Bypass Investigation:** Can anything bypass the Trading Core and directly create an order?
  - **FORENSIC ANSWER:** NO. All execution requests pass through `DemoExecutionEngine.execute_demo_decision()`, which explicitly invokes `DemoExecutionGate.verify_demo_execution_eligibility()` prior to making any call to `RealMT5BrokerAdapter.place_order()`.

---

## 22. DEMO / SHADOW / BACKTEST SEPARATION

- **Live Research (`app/workers/research_worker.py`):** Runs real-time evaluation against active MT5 feed; executes via `DemoExecutionEngine`.
- **Demo Trading (`src/Execution/Services/demo_execution_engine.py`):** Shared strategy orchestrator and risk engine; sends actual DEMO orders to MT5 paper account.
- **Shadow Trading (`src/ShadowTrading/`):** **RETIRED / DEPRECATED**. Reported as Disabled in `/health`.
- **Backtesting (`src/Application/Backtesting/`):** Uses zero look-ahead simulated bar loop; shares `ProfessionalRiskEngine` math but bypasses `DemoExecutionGate`.

---

## 23. CONFIGURATION / ENVIRONMENT OVERRIDES

- **Configuration File:** `src/Infrastructure/config.py` (`Config`)
- **Precedence Order:**
  1. Environment Variables (e.g., `YARTRADER_LIVE_TRADING_ENABLED`, `MT5_DEMO_MODE`)
  2. `config/version.json` / System Config
  3. Class Constructor Defaults
  4. Hardcoded Safety Gate Overrides (`LIVE_TRADING_ENABLED = False` in `DemoExecutionGate` overrides external settings)

---

## 24. DEAD / LEGACY / SHADOW-ONLY RULES

- `app/workers/shadow_worker.py`: **DELETED / RETIRED** (Shadow trading completely retired).
- `src/ShadowTrading/`: **LEGACY_PRESERVED** (Code preserved for architectural history, inactive at runtime).
- Synthetic Price Fallbacks (`2000.0 / 2005.0`): **DELETED** in recent PRs, replaced by explicit `WAIT` on missing candle data.

---

## 25. CONTRADICTION MATRIX

*(Full details documented in `docs/YARTRADER_TRADING_CORE_CONTRADICTION_MATRIX.md`)*

---

## 26. CANONICAL TRADING RULE SHEET

| Category | Canonical Current Rule | Source File | Runtime Authority |
| -------- | ---------------------- | ----------- | ----------------- |
| Execution TF | **M5** | `timeframe_selector.py` | Signal Engine |
| Primary Asset | **XAUUSD** | `research_worker.py` | Research Worker |
| Trading Styles | `FAST_SCALPING`, `SCALPING`, `INTRADAY`, `SWING` | `trading_style.py` | Style Selector |
| Active Strategies | `FAST_SCALP`, `SCALP`, `DAY_TRADING`, `JUMP`, `PRICE_ACTION_RTM`, `FRACTAL` | `strategy_orchestrator.py` | Strategy Orchestrator |
| Min Signal Confidence | **60.0%** | `professional_signal_engine.py` | Signal Engine |
| Initial Leg Risk | **2.0% Equity Risk** | `campaign_manager.py` | Campaign Manager |
| Add-on Leg Risk | **1.0% Equity Risk** | `campaign_manager.py` | Campaign Manager |
| Single Trade Risk Ceiling | **0.5% Equity Risk** | `portfolio.py` | Portfolio Engine (Advisory Planner) |
| Min Net Real RR | **>= 1.5** | `professional_risk_engine.py` | Risk Engine (Hard Veto) |
| Max Portfolio Heat | **6.0% Total Equity Risk** | `portfolio.py` | Portfolio Engine |
| Max Strategy Exposure | **3.0% Strategy Equity Risk** | `portfolio.py` | Portfolio Engine |
| Max Safe Spread | **5.0 pips** | `professional_risk_engine.py` | Risk Engine (Hard Veto) |
| Position Exclusivity | **BUY + SELL on same symbol forbidden** | `demo_execution_gate.py` | Execution Safety Gate |
| Minimum Hold Time | **120 seconds** | `market_session_engine.py` | Session Engine |
| Live Trading Lock | `LIVE_TRADING_ENABLED = False` | `demo_execution_gate.py` | Execution Safety Gate (Hard Stop) |

---

## 27. FINAL HUMAN-READABLE ANSWERS

1. **What primary condition causes BUY?**
   - A BUY candidate is generated when market structure aligns bullishly on M5 (or M1 EMA5 > EMA13 for Fast Scalp), price retests a bullish FVG/OB/QML, confidence >= 60%, Real RR >= 1.5, spread <= 5.0 pips, expected value > $0, and no active opposite position exists.
2. **What primary condition causes SELL?**
   - A SELL candidate is generated when market structure aligns bearishly on M5 (or M1 EMA5 < EMA13 for Fast Scalp), price retests a bearish FVG/OB/QML, confidence >= 60%, Real RR >= 1.5, spread <= 5.0 pips, expected value > $0, and no active opposite position exists.
3. **What causes WAIT?**
   - `WAIT` is returned when M1/M5 structure is conflicting, candle data is missing/insufficient, confidence < 60%, or no strategy triggers a setup.
4. **What causes REJECT?**
   - `REJECT` is triggered if Real RR < 1.5, spread > 5.0 pips, expected value <= 0, win probability < 50%, portfolio heat > 6.0%, margin is insufficient, or an opposite position is currently open.
5. **What strategies actually trade?**
   - All 6 strategies in `StrategyOrchestrator` (`FAST_SCALP`, `SCALP`, `DAY_TRADING`, `JUMP`, `PRICE_ACTION_RTM`, `FRACTAL`) actively evaluate setup candidates during runtime polling.
6. **What timeframe actually executes?**
   - **M5** is the primary execution timeframe.
7. **What is the real initial risk %?**
   - **2.0% Equity Risk** in `CampaignLifecycleManager` (runtime execution) / **0.5% Equity Risk** in `PortfolioRiskIntelligenceEngine` (advisory planner).
8. **What is the real add-on risk %?**
   - **1.0% Equity Risk** strictly enforced by `CampaignLifecycleManager`.
9. **What is the real minimum RR?**
   - **1.5 Net Real RR** enforced by `ProfessionalRiskEngine`.
10. **Is RR > 2 actually enforced?**
    - NO. RR >= 2.0 is an advisory target for `SCALP` / `DAY_TRADING` strategies, but the hard global gate allows any trade with Real RR >= 1.5.
11. **What is the real Win Rate?**
    - Win rate is dynamically computed per backtest/runtime run. In `ProfessionalRiskEngine`, a baseline `win_probability = 0.55` (55%) is used as an expected value calculation parameter.
12. **Where does Win Rate come from?**
    - Historical trade backtests (`BacktestAndLearningEngine`) and fractal pattern memory historical success records (`FractalPatternMemory`).
13. **Is Historical Success Rate the same thing?**
    - NO. Historical Success Rate measures pattern match frequency in `FractalPatternMemory`, while Win Rate measures closed trade PnL outcomes.
14. **What determines SL?**
    - Structural swing highs/lows, FVG/OB bounds, or ATR volatility offsets.
15. **What determines TP?**
    - Risk-Reward target multipliers (1.5x, 2.0x, 2.5x) or structural supply/demand target nodes.
16. **What determines position size?**
    - Equity, Risk % (2% initial, 1% add-on), SL Distance in pips, Spread, Commission ($7/lot), and Slippage.
17. **What makes a previous position risk-free?**
    - Moving its Stop Loss to or beyond the Effective BE price (Entry + Spread + Commission + Slippage pips).
18. **When can an add-on occur?**
    - Only when the parent campaign is active, all existing legs are verified as Effective Risk-Free, and a fresh M5 setup appears.
19. **What forces an exit?**
    - SL hit, TP hit, EOD 15-minute pre-close flatten, or reversal handoff close request.
20. **What is the final veto authority?**
    - `DemoExecutionGate` at the execution boundary and `ProfessionalRiskEngine` at the decision boundary.
21. **Can anything bypass the Core?**
    - NO. All trade requests flow through `DemoExecutionEngine` and `DemoExecutionGate`.
22. **Which rules are active vs legacy?**
    - Active: `StrategyOrchestrator`, `ProfessionalRiskEngine`, `CampaignLifecycleManager`, `DemoExecutionGate`.
    - Legacy: `ShadowTrading` engine components (retired).
23. **Which contradictions materially affect trading behavior?**
    - The difference between `PortfolioRiskIntelligenceEngine` single trade risk limit (0.5%) and `CampaignLifecycleManager` initial trade risk (2.0%). Runtime campaign manager uses 2.0%.

---

## 28. EVIDENCE REQUIREMENT SUMMARY

- `src/Decision/Intelligence/professional_signal_engine.py`: Lines 1-280 (`ProfessionalSignalEngine`)
- `src/Risk/Services/professional_risk_engine.py`: Lines 1-320 (`ProfessionalRiskEngine`)
- `src/Risk/Services/campaign_manager.py`: Lines 1-210 (`CampaignLifecycleManager`)
- `src/Intelligence/Execution/strategy_orchestrator.py`: Lines 1-500 (`StrategyOrchestrator`)
- `src/Execution/Safety/demo_execution_gate.py`: Lines 1-150 (`DemoExecutionGate`)
- `src/Execution/Services/demo_execution_engine.py`: Lines 1-220 (`DemoExecutionEngine`)
