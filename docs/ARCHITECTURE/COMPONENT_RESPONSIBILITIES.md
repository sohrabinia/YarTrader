# Component Responsibilities

- **`MetaTrader5Provider`**: Standard mock rates ingestion.
- **`FeaturePipeline`**: Computes rolling volatility, range expansions, and percentage returns.
- **`ResearchEngine`**: Matches technical patterns and qualitative sentiment insights.
- **`StrategyEvaluator`**: Scores concept stability and risk alignment.
- **`RiskAnalyzer`**: Audits single-asset exposure limits.
- **`DecisionEngine`**: Evaluates multi-factor context, resolves conflict, and maps evidence trails.
- **`StructuredLogger`**: Outputs single-line standardized JSON records.
- **`ProductionHealthChecker`**: Executes comprehensive diagnostics across all subsystems.
- **`ShadowModeEngine`**: Coordinates live, read-only shadow tracking sessions.
