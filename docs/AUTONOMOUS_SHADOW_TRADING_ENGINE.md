# Autonomous Shadow Trading Intelligence Engine Specification
## TradeYar AI v3.2

This document provides the architectural blueprint and specifications for the **Autonomous Shadow Trading Intelligence Engine** implemented inside TradeYar AI v3.2. This system isolates internal multi-layer cognitive pattern-learning processes from clean, user-visible signal interfaces.

---

## 1. System Overview & Mission

The core mission of the Autonomous Shadow Trading Engine is to create an internal, fully simulated non-trading sandbox. By consuming live, read-only MT5 ticks, the engine constructs its own mathematical representation of time, maps structural behaviors without subjective indicators, registers predictive virtual trades, evaluates performance outcomes via an independent judge, and exposes carefully sanitized signals to users.

---

## 2. Core Architecture & Data Flow

```
                MT5 READ ONLY TICKS
                         |
                         v
                Reality Layer
                         |
                         v
              Custom Time Engine
                         |
                         v
          Market Behavior Intelligence
                         |
                         v
              Base / Node Detection
                         |
                         v
             Pattern Recognition Engine
                         |
                         v
          Predictive Decision Engine
                         |
                         v
          Autonomous Shadow Trader
                         |
             +-----------+------------+
             |                        |
             v                        v
       ADMIN INTELLIGENCE       USER SIGNAL SYSTEM
             |
             v
       Judge + Memory Learning
```

### 2.1 Custom Timeframe Engine
- Aggregates raw tick streams into custom timeframe structures (e.g., 1, 4, 16, 64, 256, 1024 tick bars).
- Completely decoupled from standard MT5/Broker timeframes (such as M1, M5, H1, etc.).
- Stores `frame_id`, `tick_count`, `duration`, `price_range`, and `movement_behavior` descriptors.

### 2.2 Market Behavior Intelligence
- Employs strict price-action logic: velocity, acceleration, net displacement, compression, expansion, reaction, and historical similarity.
- **Forbidden Methods**: Any and all classical technical indicators (RSI, EMA, SMA, Bollinger Bands, Stochastic, MACD, etc.).

### 2.3 Base & Node Detection
- **Base (Compression Area)**: Stores Base ID, Symbol, creation time, high, low, duration, tick count, boundary touch tests, expansion direction, and success rates.
- **Node (Reaction Point)**: Stores Node ID, Price level, creation context, movement phase, reaction strength, and outcome.

---

## 3. Separation of Admin and User Layers

To preserve proprietary cognitive strategies, prevent unauthorized bypass, and keep a clear UX boundaries, the system establishes a hard separation between the Admin Panel and the User Panel.

| Boundary Factor | Admin Intelligence Platform | User Application Platform |
| :--- | :--- | :--- |
| **Purpose** | Internal AI supervision, research, debugging, training, and performance evaluation. | External, high-fidelity trade signal presentation. |
| **Response Models** | Returns complete mathematical states, raw events, confidence calculations, and excursions. | Returns only clean, actionable signal fields. |
| **Forbidden Fields** | None. | Internal weights, raw ticks, judge formulas, MAE/MFE, patterns, and base/node IDs. |
| **APIs** | `/api/admin/shadow-trades`, `/api/admin/memory`, `/api/admin/judge`, `/api/admin/patterns` | `/api/user/signals`, `/api/user/history`, `/api/user/active` |

### 3.1 Signal Translation Constraint
The User API signals are derived **strictly** from an active internal `ShadowTrade` instance. If the Shadow Trading Engine does not formulate or trigger a virtual trade, **no user signal is generated**.

---

## 4. Shadow Trade Lifecycle

A predictive shadow order moves through the following immutable states:

```
    [CREATED]
       |
       v (Price triggers Entry Level)
    [RUNNING]
       |
       +---> (Price hits Target) ----> [TARGET_HIT]
       |
       +---> (Price hits Stop) ------> [STOP_HIT]
       |
       +---> (Time exceeds limits) --> [TIMEOUT]
       |
       +---> (Order invalidated) ----> [INVALIDATED]
```

- **CREATED**: Predictive virtual order registered *before* the price reaches the entry price.
- **RUNNING**: Price has arrived at the entry level; live P/L, MAE, and MFE calculation begins.
- **TARGET_HIT / STOP_HIT**: Order successfully concluded; triggers memory learning loops.

---

## 5. Memory Learning & Judge System

Upon position closure (`TARGET_HIT` or `STOP_HIT`), the independent **Judge Brain** performs a retrospective evaluation of:
1. **Pattern Quality**: Accuracy of the predictive hypothesis structure.
2. **Base/Node Accuracy**: Precision of the entry triggers.
3. **Entry Timing**: Lag or execution efficiency.
4. **Target Quality & Risk Boundary**: Reward-to-risk ratio realism.

### 5.1 Experience Promotion Pipeline
The evaluations update three distinct layers of cognitive memory systems:
- **Experience Memory**: Retains situation signatures, outcomes, and contextual lesson feedbacks.
- **Pattern Memory**: Tracks pattern occurrence, continuation, and reversal success rates.
- **Concept Memory**: Promotes high-performing patterns into solidified concepts.

---

## 6. Secure Database Architecture & Persistence

To maintain learning progression without regression during upgrades, the engine writes persistent data to dedicated JSON files under `runtime_logs/`:
- `shadow_trades.json`: Complete virtual position history.
- `base_memory.json` / `node_memory.json`: Structural zones.
- `pattern_outcomes.json`: Hit rates for specific patterns.
- `learning_history.json`: Backpropagation and confidence calibration logs.
- `signal_history.json`: Sanitized user signal records.

**Retention Rule**: Data is strictly cumulative; learning records are never deleted.
