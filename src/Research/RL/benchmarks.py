"""
YarTrader Layer 3 — Baseline Comparison & Research Benchmark Runner
===================================================================
Compares Hybrid PPO Policy performance against:
1. Buy & Hold Baseline
2. Simple Trend-Following Baseline
3. Fractal-Only Baseline
4. Math-Feature-Only Baseline
5. Hybrid PPO Policy

Evaluates net return, Sharpe, Sortino, max drawdown, win rate, profit factor, expectancy, turnover, average trade.
"""

import math
import numpy as np
from typing import Dict, Any, List
from src.Research.Brain.multi_timeframe_state import FractalMarketState
from src.Research.RL.environment import FractalMarketEnv
from src.Research.RL.ppo_agent import PPOAgent


class BenchmarkRunner:
    """
    Executes chronological baseline evaluations and compares Hybrid PPO against traditional models.
    """

    @staticmethod
    def _calculate_metrics(returns: List[float], initial_balance: float = 10000.0) -> Dict[str, Any]:
        """Calculates performance analytics for a return series."""
        if not returns:
            return {
                "net_return_pct": 0.0,
                "sharpe_ratio": 0.0,
                "sortino_ratio": 0.0,
                "max_drawdown_pct": 0.0,
                "win_rate_pct": 0.0,
                "profit_factor": 0.0,
                "expectancy_usd": 0.0,
                "trade_count": 0
            }

        arr = np.array(returns, dtype=np.float64)
        total_pnl = float(np.sum(arr))
        net_ret_pct = round((total_pnl / initial_balance) * 100.0, 2)

        wins = arr[arr > 0]
        losses = arr[arr < 0]

        win_rate = round((len(wins) / len(arr)) * 100.0, 2) if len(arr) > 0 else 0.0
        gross_profit = float(np.sum(wins)) if len(wins) > 0 else 0.0
        gross_loss = float(np.abs(np.sum(losses))) if len(losses) > 0 else 0.0

        pf = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)
        expectancy = round(total_pnl / len(arr), 2) if len(arr) > 0 else 0.0

        mean_ret = np.mean(arr)
        std_ret = np.std(arr) + 1e-8
        sharpe = round(float((mean_ret / std_ret) * math.sqrt(252)), 2)

        downside_std = np.std(losses) + 1e-8 if len(losses) > 0 else std_ret
        sortino = round(float((mean_ret / downside_std) * math.sqrt(252)), 2)

        # Drawdown calculation
        cum = np.cumsum(arr) + initial_balance
        peaks = np.maximum.accumulate(cum)
        dds = (peaks - cum) / peaks
        max_dd = round(float(np.max(dds)) * 100.0, 2) if len(dds) > 0 else 0.0

        return {
            "net_return_pct": net_ret_pct,
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "max_drawdown_pct": max_dd,
            "win_rate_pct": win_rate,
            "profit_factor": pf,
            "expectancy_usd": expectancy,
            "trade_count": len(arr)
        }

    def run_all_benchmarks(
        self,
        states: List[FractalMarketState],
        price_series: List[float]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Runs and compares 5 models on identical price and state series.
        """
        env = FractalMarketEnv(states, price_series)

        # 1. Buy & Hold
        bh_returns = [price_series[i] - price_series[i-1] for i in range(1, len(price_series))]
        bh_metrics = self._calculate_metrics(bh_returns)

        # 2. Simple Trend Following (SMA crossover proxy using Hurst H)
        tf_returns = []
        for i in range(1, len(states)):
            h = states[i-1].hurst_h
            ret = price_series[i] - price_series[i-1]
            if h > 0.55:
                tf_returns.append(ret)
            elif h < 0.45:
                tf_returns.append(-ret)
        tf_metrics = self._calculate_metrics(tf_returns)

        # 3. Fractal-Only Baseline
        fractal_returns = []
        for i in range(1, len(states)):
            reg = states[i-1].regime_state
            ret = price_series[i] - price_series[i-1]
            if reg == "CONTINUATION":
                fractal_returns.append(ret)
            elif reg == "REVERSAL":
                fractal_returns.append(-ret)
        fractal_metrics = self._calculate_metrics(fractal_returns)

        # 4. Math-Feature-Only Baseline
        math_returns = []
        for i in range(1, len(states)):
            st = states[i-1]
            ret = price_series[i] - price_series[i-1]
            if st.hurst_h > 0.55 and st.fractal_dimension_d < 1.4:
                math_returns.append(ret)
            elif st.hurst_h < 0.45 and st.fractal_dimension_d > 1.6:
                math_returns.append(-ret)
        math_metrics = self._calculate_metrics(math_returns)

        # 5. Hybrid PPO
        ppo_agent = PPOAgent()
        obs, _ = env.reset()
        ppo_returns = []
        done = False
        while not done:
            action, _, _ = ppo_agent.select_action(obs, deterministic=True)
            next_obs, reward, terminated, truncated, info = env.step(action)
            if info.get("pnl", 0) != 0:
                ppo_returns.append(info["net_return"])
            obs = next_obs
            done = terminated or truncated

        ppo_metrics = self._calculate_metrics(ppo_returns)

        return {
            "buy_and_hold": bh_metrics,
            "simple_trend_following": tf_metrics,
            "fractal_only_baseline": fractal_metrics,
            "math_feature_only_baseline": math_metrics,
            "hybrid_ppo_policy": ppo_metrics
        }
