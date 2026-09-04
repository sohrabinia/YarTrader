"""
YarTrader Layer 3 — Gymnasium-Compatible Fractal Market Environment
===================================================================
Simulates sequential trading decisions driven by Layer 2 FractalMarketState.
Actions:
  0 = HOLD
  1 = ENTER_LONG
  2 = EXIT_LONG
  3 = ENTER_SHORT
  4 = EXIT_SHORT

Observation space: Normalized vector extracted strictly from FractalMarketState (no future data leakage).
Reward function: Net PnL - Spread/Commission/Slippage - Drawdown - Turnover - Unnecessary Reversal Penalty - Anti-Regime Penalty.
"""

import math
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from src.Research.Brain.multi_timeframe_state import FractalMarketState


class FractalMarketEnv:
    """
    Gymnasium-compatible trading environment for research and policy evaluation.
    """

    def __init__(
        self,
        states: List[FractalMarketState],
        price_series: List[float],
        initial_balance: float = 10000.0,
        spread_usd: float = 0.20,      # ~$2.00/oz gold spread
        commission_usd: float = 0.07,  # $7/lot ($0.07/oz)
        slippage_usd: float = 0.10     # $1.00/oz slippage
    ) -> None:
        if len(states) != len(price_series):
            raise ValueError("State count and price series count must match exactly.")

        self.states = states
        self.price_series = price_series
        self.initial_balance = initial_balance
        self.spread_usd = spread_usd
        self.commission_usd = commission_usd
        self.slippage_usd = slippage_usd

        # Action space size: 5 discrete actions
        self.action_space_n = 5
        # Observation feature vector length: 10 normalized features
        self.observation_shape = (10,)

        self.current_step = 0
        self.balance = initial_balance
        self.peak_balance = initial_balance
        self.position = 0  # 0 = FLAT, 1 = LONG, -1 = SHORT
        self.entry_price = 0.0
        self.holding_steps = 0
        self.trade_count = 0
        self.reversal_count = 0

    def reset(self) -> Tuple[np.ndarray, Dict[str, Any]]:
        self.current_step = 0
        self.balance = self.initial_balance
        self.peak_balance = self.initial_balance
        self.position = 0
        self.entry_price = 0.0
        self.holding_steps = 0
        self.trade_count = 0
        self.reversal_count = 0

        obs = self._get_observation(0)
        info = {"step": 0, "balance": self.balance, "position": self.position}
        return obs, info

    def _get_observation(self, step_idx: int) -> np.ndarray:
        """
        Extracts 10 normalized features strictly from FractalMarketState at step_idx.
        No future data access!
        """
        st = self.states[step_idx]

        # Normalized feature vector:
        # 0: Hurst H (0 to 1)
        # 1: Higuchi D (1 to 2 -> normalized to 0 to 1)
        # 2: Wavelet high-freq energy ratio (0 to 1)
        # 3: ATR normalized by current price
        # 4: Target consensus probability (0 to 1)
        # 5: Quality score (0 to 1)
        # 6: Regime encoding (CONTINUATION=1.0, PULLBACK=0.5, REVERSAL=-1.0, RANGE=0.0, NO_TRADE=-0.5)
        # 7: Current position state (-1, 0, 1)
        # 8: Normalized holding steps (holding_steps / 100)
        # 9: Drawdown from peak balance ratio
        curr_price = max(1.0, self.price_series[step_idx])

        reg_map = {"CONTINUATION": 1.0, "PULLBACK": 0.5, "REVERSAL": -1.0, "RANGE": 0.0, "NO_TRADE": -0.5}
        reg_val = reg_map.get(st.regime_state, 0.0)

        dd = (self.peak_balance - self.balance) / self.peak_balance if self.peak_balance > 0 else 0.0

        target_p = st.target_consensus.get("consensus_probability", 0.5) if isinstance(st.target_consensus, dict) else 0.5

        vec = np.array([
            float(st.hurst_h),
            float((st.fractal_dimension_d - 1.0)),  # 0.0 to 1.0
            float(st.wavelet_high_freq_ratio),
            float(st.atr / curr_price),
            float(target_p),
            float(st.quality_score),
            float(reg_val),
            float(self.position),
            float(min(1.0, self.holding_steps / 100.0)),
            float(dd)
        ], dtype=np.float32)

        return np.nan_to_num(vec)

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        """
        Executes one environment step.
        Actions: 0=HOLD, 1=ENTER_LONG, 2=EXIT_LONG, 3=ENTER_SHORT, 4=EXIT_SHORT
        """
        curr_p = self.price_series[self.current_step]
        next_p = self.price_series[self.current_step + 1] if self.current_step + 1 < len(self.price_series) else curr_p

        pnl = 0.0
        cost = 0.0
        penalty = 0.0

        st = self.states[self.current_step]
        regime = st.regime_state

        # Action execution logic
        if action == 1:  # ENTER_LONG
            if self.position == 0:
                self.position = 1
                self.entry_price = curr_p
                self.holding_steps = 0
                self.trade_count += 1
                cost = self.spread_usd + self.commission_usd + self.slippage_usd
                if regime in ["REVERSAL", "NO_TRADE"]:
                    penalty += 0.5  # Entering long against adverse regime
            elif self.position == -1:
                # Direct reversal without exiting first penalty
                penalty += 1.0
                self.reversal_count += 1

        elif action == 2:  # EXIT_LONG
            if self.position == 1:
                pnl = (curr_p - self.entry_price)
                cost = self.spread_usd + self.commission_usd + self.slippage_usd
                self.position = 0
                self.entry_price = 0.0
                self.holding_steps = 0
                # If exited during normal PULLBACK without strong reversal evidence -> penalize premature exit
                if regime == "PULLBACK":
                    penalty += 0.3

        elif action == 3:  # ENTER_SHORT
            if self.position == 0:
                self.position = -1
                self.entry_price = curr_p
                self.holding_steps = 0
                self.trade_count += 1
                cost = self.spread_usd + self.commission_usd + self.slippage_usd
                if regime in ["CONTINUATION", "PULLBACK"]:
                    # PENALTY FOR ENTERING SHORT DURING HTF CONTINUATION OR PULLBACK!
                    penalty += 2.0
            elif self.position == 1:
                # Direct reversal without exiting first penalty
                penalty += 1.0
                self.reversal_count += 1

        elif action == 4:  # EXIT_SHORT
            if self.position == -1:
                pnl = (self.entry_price - curr_p)
                cost = self.spread_usd + self.commission_usd + self.slippage_usd
                self.position = 0
                self.entry_price = 0.0
                self.holding_steps = 0

        elif action == 0:  # HOLD
            if self.position != 0:
                self.holding_steps += 1
                # Continuous mark-to-market PnL step delta
                if self.position == 1:
                    pnl = (next_p - curr_p)
                elif self.position == -1:
                    pnl = (curr_p - next_p)

        # Update balance
        net_step_return = pnl - cost
        self.balance += net_step_return
        if self.balance > self.peak_balance:
            self.peak_balance = self.balance

        # Drawdown penalty
        dd = (self.peak_balance - self.balance) / self.peak_balance if self.peak_balance > 0 else 0.0
        dd_penalty = dd * 2.0

        # Total multi-objective reward
        reward = float(net_step_return - penalty - dd_penalty)

        self.current_step += 1
        terminated = (self.current_step >= len(self.price_series) - 1) or (self.balance <= self.initial_balance * 0.5)
        truncated = False

        next_obs = self._get_observation(min(self.current_step, len(self.price_series) - 1))
        info = {
            "step": self.current_step,
            "balance": round(self.balance, 2),
            "position": self.position,
            "net_return": round(net_step_return, 4),
            "pnl": round(pnl, 4),
            "cost": round(cost, 4),
            "penalty": round(penalty, 4),
            "drawdown": round(dd, 4)
        }

        return next_obs, reward, terminated, truncated, info
