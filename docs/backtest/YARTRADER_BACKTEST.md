# YarTrader — Backtest Architecture & Specification

## 1. Overview
The Backtest subsystem in YarTrader provides a pure, deterministic historical simulation engine that evaluates canonical trading strategies (`SPIKE`, `RANGE`, `TREND`) over historical normalized market data.

Backtest is strictly a **HISTORICAL SIMULATION ENGINE**. It does not perform live trading, submit broker orders, or alter account balances or positions.

---

## 2. Core Architecture & Strategy Reuse

```text
Historical Market Data
        ↓
MarketDataService (Phase 6 Provider Abstraction)
        ↓
BacktestService
        ↓
BacktestEngine (Walk-Forward Simulation Loop)
   ┌────┼────┐
   ↓    ↓    ↓
 Spike Range Trend (Phase 7, 8, 9 Strategy Engines)
   └────┼────┘
        ↓
BacktestResult / BacktestSummary
        ↓
Protected REST API (GET /api/backtest)
```

### Strategy Reuse Principle
Backtest does NOT duplicate strategy mathematical algorithms. It instantiates and invokes existing strategy engines (`SpikeStrategyEngine`, `RangeStrategyEngine`, `TrendStrategyEngine`). This maintains a single source of truth for strategy logic across both single-timestamp evaluation and historical backtesting.

---

## 3. Walk-Forward Methodology & Look-Ahead Protection

To eliminate look-ahead bias, `BacktestEngine` implements a strict walk-forward evaluation loop:
1. Historical candles are sorted chronologically and timestamp-deduplicated.
2. For each historical index $i$ (where $i \ge \text{min\_history\_bars}$), the engine slices a historical candle window consisting strictly of candles $t \le T$ (where $T = \text{candles}[i-1]$).
3. The sliced window is passed to the selected strategy engine's `evaluate(...)` method.
4. The strategy returns a deterministic signal and metrics for timestamp $T$.
5. Appending arbitrary future candles $T+1, T+2, \dots$ does NOT alter evaluation results for timestamp $T$.

---

## 4. Result Model & Data Transfer Objects

### `BacktestConfig`
- `symbol`: Instrument symbol (e.g. `XAUUSD`)
- `interval`: Timeframe interval (e.g. `M15`)
- `strategy_type`: Enum (`SPIKE`, `RANGE`, `TREND`)
- `min_history_bars`: Initial cold-start window (default: 21)

### `BacktestSummary`
- `total_evaluations`: Total timestamp evaluations performed
- `valid_evaluations`: Evaluations producing valid strategy signals
- `insufficient_data_count`: Evaluations resulting in `INSUFFICIENT_DATA` cold-start signals
- `signal_counts`: Map of signal types to frequency counts

### `BacktestResult`
- `symbol`: Cleaned canonical symbol
- `interval`: Cleaned canonical interval
- `strategy_type`: Selected strategy
- `summary`: `BacktestSummary` DTO
- `evaluations`: Array of `BacktestEvaluation` objects
- `executed_at`: UTC execution timestamp

---

## 5. REST API Specification

### `GET /api/backtest`
- **Description:** Executes walk-forward backtest simulation for specified instrument, interval, and strategy.
- **Authentication:** Protected endpoint requiring valid session token parameter `token`.
- **Query Parameters:**
  - `symbol` (str, default: `"XAUUSD"`)
  - `interval` (str, default: `"M15"`)
  - `strategy` (str, default: `"TREND"`, options: `"SPIKE"`, `"RANGE"`, `"TREND"`)
  - `limit` (int, default: `100`, max: `1000`)
  - `min_history_bars` (int, default: `21`)
- **Response Format:**
  ```json
  {
    "status": "Success",
    "data": {
      "symbol": "XAUUSD",
      "interval": "M15",
      "strategy_type": "TREND",
      "summary": {
        "total_evaluations": 80,
        "signal_counts": {
          "TREND_UP": 42,
          "NO_SIGNAL": 38
        },
        "valid_evaluations": 80,
        "insufficient_data_count": 0
      },
      "config": {
        "symbol": "XAUUSD",
        "interval": "M15",
        "strategy_type": "TREND",
        "min_history_bars": 21
      },
      "evaluations": [ ... ],
      "executed_at": "2026-09-07T19:25:00+00:00"
    }
  }
  ```

---

## 6. Non-Goals & Boundaries

1. **Zero Order Execution:** Backtest does NOT interact with order execution systems, MetaTrader trading terminals, or live broker accounts.
2. **Zero Financial Mutation:** Backtest does NOT modify wallet balances, create ledger transactions, or process payments.
3. **No Duplicate Math:** Backtest reuses Phase 7, 8, and 9 strategy domain engines without re-implementing mathematical calculations.
