# Dependency Flow

Dependencies are strictly top-down, unidirectional, and guided by the Dependency Inversion Principle (DIP):
```
Data Ingest Adapters (Low Level)
        ▼
Technical Feature Pipeline (Indicators)
        ▼
Descriptive Research Engine (Observations & Patterns)
        ▼
Multi-Factor Strategy Evaluator (Scoring)
        ▼
Portfolio Risk Verification (Bounds & Exposure)
        ▼
Decision Intelligence Core (High Level Synthesis)
```

High-level decision modules never depend on volatile MT5 or CCXT database adapters.
