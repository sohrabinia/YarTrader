"""
YarTrader Layer 3 — PPO Policy Agent (NumPy Vectorized)
======================================================
Proximal Policy Optimization (PPO) agent with Actor-Critic architecture.
Computes clipped surrogate policy loss, Value function MSE loss, GAE advantage estimation,
and returns advisory decision proposals for trade entry, management, and exit.
"""

import math
import numpy as np
from typing import Dict, Any, List, Tuple, Optional


class PPOAgent:
    """
    NumPy vectorized Actor-Critic PPO agent for research policy optimization.
    """

    def __init__(
        self,
        obs_dim: int = 10,
        action_dim: int = 5,
        hidden_dim: int = 64,
        lr: float = 0.001,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
        clip_ratio: float = 0.2,
        seed: int = 42
    ) -> None:
        self.obs_dim = obs_dim
        self.action_dim = action_dim
        self.hidden_dim = hidden_dim
        self.lr = lr
        self.gamma = gamma
        self.gae_lambda = gae_lambda
        self.clip_ratio = clip_ratio

        np.random.seed(seed)

        # Actor Weights (Policy)
        self.W1_actor = np.random.randn(obs_dim, hidden_dim) * np.sqrt(2.0 / obs_dim)
        self.b1_actor = np.zeros(hidden_dim)
        self.W2_actor = np.random.randn(hidden_dim, action_dim) * np.sqrt(2.0 / hidden_dim)
        self.b2_actor = np.zeros(action_dim)

        # Critic Weights (Value function)
        self.W1_critic = np.random.randn(obs_dim, hidden_dim) * np.sqrt(2.0 / obs_dim)
        self.b1_critic = np.zeros(hidden_dim)
        self.W2_critic = np.random.randn(hidden_dim, 1) * np.sqrt(2.0 / hidden_dim)
        self.b2_critic = np.zeros(1)

    def _softmax(self, x: np.ndarray) -> np.ndarray:
        exp_x = np.exp(x - np.max(x, axis=-1, keepdims=True))
        return exp_x / np.sum(exp_x, axis=-1, keepdims=True)

    def _relu(self, x: np.ndarray) -> np.ndarray:
        return np.maximum(0.0, x)

    def forward_actor(self, obs: np.ndarray) -> np.ndarray:
        """Computes action probabilities via softmax."""
        h1 = self._relu(np.dot(obs, self.W1_actor) + self.b1_actor)
        logits = np.dot(h1, self.W2_actor) + self.b2_actor
        return self._softmax(logits)

    def forward_critic(self, obs: np.ndarray) -> float:
        """Computes state value V(s)."""
        h1 = self._relu(np.dot(obs, self.W1_critic) + self.b1_critic)
        v = np.dot(h1, self.W2_critic) + self.b2_critic
        return float(np.squeeze(v))

    def select_action(self, obs: np.ndarray, deterministic: bool = False) -> Tuple[int, float, float]:
        """
        Selects an action given observation obs.
        Returns: (action, log_prob, state_value)
        """
        probs = self.forward_actor(obs)
        val = self.forward_critic(obs)

        if deterministic:
            action = int(np.argmax(probs))
        else:
            probs_clean = np.clip(probs, 1e-8, 1.0)
            probs_clean /= np.sum(probs_clean)
            action = int(np.random.choice(self.action_dim, p=probs_clean))

        log_prob = float(np.log(probs[action] + 1e-8))
        return action, log_prob, val

    def compute_gae(
        self,
        rewards: List[float],
        values: List[float],
        dones: List[bool],
        next_val: float
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculates Generalized Advantage Estimation (GAE).
        """
        T = len(rewards)
        advantages = np.zeros(T, dtype=np.float32)
        returns = np.zeros(T, dtype=np.float32)

        last_gae = 0.0
        vals = values + [next_val]

        for t in reversed(range(T)):
            non_terminal = 1.0 - float(dones[t])
            delta = rewards[t] + self.gamma * vals[t + 1] * non_terminal - vals[t]
            last_gae = delta + self.gamma * self.gae_lambda * non_terminal * last_gae
            advantages[t] = last_gae
            returns[t] = advantages[t] + vals[t]

        return advantages, returns

    def train_step(
        self,
        obs_batch: np.ndarray,
        actions_batch: np.ndarray,
        old_log_probs: np.ndarray,
        returns_batch: np.ndarray,
        advantages_batch: np.ndarray,
        epochs: int = 4
    ) -> Dict[str, float]:
        """
        Performs PPO policy and value network update using clipped surrogate loss.
        """
        adv_mean = np.mean(advantages_batch)
        adv_std = np.std(advantages_batch) + 1e-8
        norm_adv = (advantages_batch - adv_mean) / adv_std

        total_policy_loss = 0.0
        total_value_loss = 0.0

        N = len(obs_batch)
        if N == 0:
            return {"policy_loss": 0.0, "value_loss": 0.0}

        for _ in range(epochs):
            for i in range(N):
                o = obs_batch[i]
                a = actions_batch[i]
                old_log_p = old_log_probs[i]
                ret = returns_batch[i]
                adv = norm_adv[i]

                # Forward actor
                h1_a = self._relu(np.dot(o, self.W1_actor) + self.b1_actor)
                probs = self._softmax(np.dot(h1_a, self.W2_actor) + self.b2_actor)
                p_a = probs[a]
                new_log_p = np.log(p_a + 1e-8)

                # Clipped surrogate objective
                ratio = np.exp(new_log_p - old_log_p)
                surr1 = ratio * adv
                surr2 = np.clip(ratio, 1.0 - self.clip_ratio, 1.0 + self.clip_ratio) * adv
                policy_loss = -min(surr1, surr2)

                # Forward critic
                h1_c = self._relu(np.dot(o, self.W1_critic) + self.b1_critic)
                val = float(np.squeeze(np.dot(h1_c, self.W2_critic) + self.b2_critic))
                val_loss = 0.5 * (val - ret)**2

                # Simple SGD gradient update step for actor
                grad_logits = probs.copy()
                grad_logits[a] -= 1.0
                grad_logits *= (-adv)  # Policy gradient direction

                d_W2_a = np.outer(h1_a, grad_logits)
                d_b2_a = grad_logits
                dh1_a = np.dot(self.W2_actor, grad_logits) * (h1_a > 0)
                d_W1_a = np.outer(o, dh1_a)
                d_b1_a = dh1_a

                self.W2_actor -= self.lr * d_W2_a
                self.b2_actor -= self.lr * d_b2_a
                self.W1_actor -= self.lr * d_W1_a
                self.b1_actor -= self.lr * d_b1_a

                # SGD gradient update for critic
                val_err = val - ret
                d_W2_c = np.outer(h1_c, val_err)
                d_b2_c = np.array([val_err])
                dh1_c = np.dot(self.W2_critic, np.array([val_err])) * (h1_c > 0)
                d_W1_c = np.outer(o, dh1_c)
                d_b1_c = dh1_c

                self.W2_critic -= self.lr * d_W2_c
                self.b2_critic -= self.lr * d_b2_c
                self.W1_critic -= self.lr * d_W1_c
                self.b1_critic -= self.lr * d_b1_c

                total_policy_loss += float(policy_loss)
                total_value_loss += float(val_loss)

        return {
            "policy_loss": round(total_policy_loss / (N * epochs), 6),
            "value_loss": round(total_value_loss / (N * epochs), 6)
        }

    def generate_decision_proposal(self, obs: np.ndarray) -> Dict[str, Any]:
        """
        Inference method returning an advisory decision proposal (Advisory/Research level).
        """
        action, log_prob, val = self.select_action(obs, deterministic=True)
        probs = self.forward_actor(obs)
        conf = float(probs[action])

        action_names = {
            0: "HOLD",
            1: "ENTER_LONG",
            2: "EXIT_LONG",
            3: "ENTER_SHORT",
            4: "EXIT_SHORT"
        }

        return {
            "proposal_action": action_names.get(action, "HOLD"),
            "action_code": action,
            "confidence": round(conf, 4),
            "state_value": round(val, 4),
            "action_probabilities": {action_names[i]: round(float(probs[i]), 4) for i in range(5)},
            "advisory_note": "PPO Research Decision Proposal. Sole execution authority belongs to Risk Engine and Safety Gates."
        }
