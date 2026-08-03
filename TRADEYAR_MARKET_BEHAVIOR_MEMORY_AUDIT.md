# TRADEYAR_MARKET_BEHAVIOR_MEMORY_AUDIT.md

## Market Behavior Memory Verification Audit

### 1. Trace of Symbol: XAUUSD
This section traces the actual life cycle of a raw tick sequence on symbol `XAUUSD` through the platform’s cognitive processing pipeline:

```
[Raw Tick Stream] (e.g. from MT5DataProvider)
       ↓
[CustomTimeEngine] (Groups raw ticks into CustomTimeframeStructure, e.g., 1, 4, 16, 64 tick blocks)
       ↓
[BaseNodeDetector] (Identifies compression ranges as Bases, and high-velocity reversals as Nodes)
       ↓
[PredictiveShadowEngine] (Saves discovered Bases, Nodes, and triggers virtual ShadowTrades)
       ↓
[Outcome Learning] (Closed trades update pattern outcomes and learn confidence shifts on XAUUSD)
```

### 2. Verified Storage Schemas & Fields
The storage layer utilizes clean JSON-based file persistence under `runtime_logs/` with the following fully populated fields:

#### Base Structure Persistence (`runtime_logs/base_memory.json`)
- **`base_id`**: String ID, e.g., `Base-4f2a1b9e`
- **`symbol`**: String (e.g., `XAUUSD`)
- **`creation_time`**: ISO-8601 string representation of timestamp
- **`high`**: High price boundary of the compression area (float)
- **`low`**: Low price boundary of the compression area (float)
- **`duration`**: Total duration of compression in seconds (float)
- **`tick_count`**: Total ticks contained in the compression range (int)
- **`tests`**: Number of touches/tests of the high or low boundaries (int)
- **`expansion_direction`**: Direction of expansion breakout (`UP`, `DOWN`, `NONE`)
- **`historical_result`**: Outcome (`WIN`, `LOSS`, `PENDING`)
- **`success_rate`**: Overall success rating of base pattern (float)

#### Node Structure Persistence (`runtime_logs/node_memory.json`)
- **`node_id`**: String ID, e.g., `Node-b9d2f4a1`
- **`price_level`**: Price reaction value (float)
- **`creation_context`**: Text description, e.g., `"Velocity spike reaction"`
- **`movement_phase`**: Reversal or continuation phase
- **`reaction_strength`**: Mathematical change magnitude (float)
- **`outcome`**: Target hit status (`SUCCESS`, `FAILURE`, `PENDING`)

#### Outcome Memory Persistence (`runtime_logs/pattern_outcomes.json` and `runtime_logs/learning_history.json`)
- **`pattern`**: String, e.g., `"Base Expansion Continuation"`
- **`result`**: End state (`TARGET_HIT`, `STOP_HIT`)
- **`mae`**: Max Adverse Excursion (floating points P&L)
- **`mfe`**: Max Favorable Excursion (floating points P&L)
- **`confidence_shift`**: Multiplier change, e.g., `+0.05` for target hit, `-0.05` for stop hit.

### 3. Verification & Accuracy Score
- **Tick Sequence Memory**: Active tick buffers up to 5,000 ticks per symbol are maintained in `SymbolTimeContext` memory buffers.
- **Base Intelligence**: Completed and verified via AST inspects and persistent storage writes.
- **Node Memory**: Completed and verified.
- **Outcome Memory**: Real outcomes are fully recorded at runtime to `pattern_outcomes.json`. No hardcoded placeholder statistics are used.
