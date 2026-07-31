# TRADEYAR Agent Intelligence Model

This document outlines the theoretical and operational intelligence models governing agents within the **TRADEYAR Collaborative Intelligence Layer**.

---

## 1. Agent Cognitive Framework

Each agent operates as a bounded-rationality actor, processing local information, participating in shared protocols, and evaluating its own output.

```
  +-------------------------------------------------+
  |                Agent Local Scope                |
  |                                                 |
  |  +---------------+             +-------------+  |
  |  |  Capabilities |             | Memory/State|  |
  |  +-------+-------+             +------+------+  |
  |          |                            |         |
  |          v                            v         |
  |  +-------------------------------------------+  |
  |  |           Local Processing Loop           |  |
  |  +--------------------+----------------------+  |
  |                       |                         |
  |                       v                         |
  |  +-------------------------------------------+  |
  |  |            Agent Self-Evaluation          |  |
  |  +--------------------+----------------------+  |
  +-----------------------|-------------------------+
                          | (IntelligenceMessage)
                          v
  +-------------------------------------------------+
  |           Collaborative Synthesis               |
  |                                                 |
  |  +-------------------------------------------+  |
  |  |        Knowledge Sharing Protocol         |  |
  |  +--------------------+----------------------+  |
  |                       |                         |
  |                       v                         |
  |  +-------------------------------------------+  |
  |  |          Negotiation Framework            |  |
  |  +--------------------+----------------------+  |
  |                       |                         |
  |                       v                         |
  |  +-------------------------------------------+  |
  |  |       Collective Intelligence Eval        |  |
  |  +--------------------+----------------------+  |
  +-----------------------|-------------------------+
                          v
               Decision Intelligence Core
```

---

## 2. Dynamic Priority Formulation

The priority of an agent $A_i$ at time $t$ is formulated dynamically based on market regimes and unsatisfied collaborative goals:

$$P(A_i, t) = P_{\text{default}}(A_i) + \Delta_{\text{regime}}(M_t) + \sum_{g \in G} w_g \cdot \mathbb{I}(g \text{ is unmet})$$

Where:
*   $P_{\text{default}}(A_i)$ is the baseline priority (defaults to $0.5$).
*   $\Delta_{\text{regime}}(M_t)$ is the market condition shift (e.g., $+0.4$ for the Risk Agent under high volatility).
*   $w_g \cdot \mathbb{I}(g \text{ is unmet})$ is the goal weight multiplier for unmet goals targeting agent $A_i$'s domain.

---

## 3. Weighted Compromise Negotiation

Divergent portfolio weight suggestions are reconciled through a weighted priority-confidence compromise:

$$W_{\text{compromise}}(Asset) = \frac{\sum_{j} W_{j}(Asset) \cdot P(A_j) \cdot C_j}{\sum_{j} P(A_j) \cdot C_j}$$

Where:
*   $W_j(Asset)$ is the weight proposed by agent $j$ for the target asset.
*   $P(A_j)$ is the dynamic priority score of agent $j$.
*   $C_j$ is the local confidence level reported by agent $j$.

---

## 4. Bounded Execution Scope (Safety Boundary)

Under APES-FIN standards, agents are mathematically barred from generating BUY/SELL directions or order triggers. Outputs are translated into non-trading context properties consumed exclusively by the **Decision Intelligence Core** under passive analysis states (`Approved`, `Rejected`, `ReviewRequired`, `NoAction`).
