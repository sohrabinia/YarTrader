# YARTRADER ENVIRONMENT SEPARATION MATRIX

This matrix defines the verified capability limits, inputs, and isolation rules active across YarTrader's four operational domains.

---

## 1. ENVIRONMENTAL MATRIX

| Capability | Backtest | Demo | Paper/Live Simulation (Shadow) | Real Live |
| :--- | :---: | :---: | :---: | :---: |
| **Historical Data** | **YES** | **NO** | **NO** | **NO** |
| **Real-time Market Ticks** | **NO** | **YES** (Simulated Stream) | **YES** | **YES** |
| **Virtual Execution** | **YES** | **YES** | **YES** | **NO** |
| **Real Broker Execution** | **NO** | **NO** | **NO** | **ONLY** if explicitly authorized |
| **Independent Ledger** | **YES** (`backtest_history.json`) | **YES** (`paper_account.json`) | **YES** (`shadow_trades.json`) | **YES** (`ledger.json`) |
| **Independent Report** | **YES** | **YES** | **YES** | **YES** |
| **Learning Feedback** | Controlled | Controlled | Controlled | Controlled |
| **Real Money Risk** | **NO** | **NO** | **NO** | **ONLY** if explicitly authorized |

---

## 2. SEPARATION COMPLIANCE STATE
* **Zero Result Contamination:** Backtesting history records are stored in `runtime_logs/backtest_history.json`, while VirtualAccount paper trading is persisted to `runtime_logs/paper_account.json`. Neither interacts with the actual double-entry financial ledger (`runtime_logs/ledger.json`) nor changes historical data or parameters retroactively.
* **Deterministic Replay Guarantee:** Replaying backtests over identical datetime windows generates identical decision confidence and supervisor reports, confirming absolute determinism and zero cached-state lookahead leaks.
