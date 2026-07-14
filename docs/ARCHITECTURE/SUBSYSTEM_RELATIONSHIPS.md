# Subsystem Relationships

Subsystems communicate cleanly via structured, immutable DTO contracts:
- Raw Ingest `MarketDataPoint` lists are adapted into `MarketFeatureSet` collections.
- `MarketFeatureSet` properties are evaluated into descriptive `ResearchResult` outcomes.
- `ResearchResult` details form `StrategyCandidate` scoring profiles.
- Score targets are validated against volatility-scaled `RiskProfile` caps.
- Final layers synthesize these details into unified `DecisionIntelligenceReport` packages.
