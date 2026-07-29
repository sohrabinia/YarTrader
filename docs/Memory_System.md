# Memory System Architecture

## 1. Overview
The Memory System of TradeYar AI consists of four separate, decoupled storage partitions, each serving a unique cognitive learning purpose.

---

## 2. The Four Memory Layers

### Event Memory
- **Purpose**: Immutable historical registry of raw observations.
- **Contents**: Observation IDs, Timestamps, Symbol, raw price sequence structure, and reaction points.

### Pattern Memory
- **Purpose**: Stores recurring, generalized structures.
- **Contents**: Pattern signatures, matched frequencies, sample count, and validation statuses. No predictions are stored here.

### Experience Memory
- **Purpose**: Tracks simulated decisions and actual future outcomes.
- **Contents**: Decisions made (BUY, SELL, WAIT), virtual entry/stops/targets, and performance results.

### Concept Memory
- **Purpose**: Stores verified principles that survived out-of-sample scientific validation.
- **Contents**: Generalized market behaviors with associated evidence-based confidence levels.
