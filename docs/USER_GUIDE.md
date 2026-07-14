# RG_V3_AI User Guide

## 1. Intelligence Demo Scenario Platform
To run a complete, end-to-end analytical scenario trace:
1. Initialize the `DemoScenarioRunner`.
2. Load the scenario library:
   ```python
   from src.Application.Demo import load_scenario_library, DemoScenarioRunner
   runner = DemoScenarioRunner()
   scenarios = load_scenario_library()
   ```
3. Select a scenario (e.g. Trend Continuation, High Volatility).
4. Run the scenario and generate an audit-ready trace report:
   ```python
   res = runner.run_scenario(scenarios[0])
   # Generate report
   from src.Application.Demo import DemoReportGenerator
   generator = DemoReportGenerator()
   report = generator.generate_report(res)
   print(report.rendered_summary)
   ```

---

## 2. Running Historical Backtests
Configure backtest scenarios to run iterative historical loops:
```python
from src.Application.Backtesting import BacktestScenario, IntelligenceBacktestEngine
# Construct scenario
# Run backtest engine over chronological slices
```

---

## 3. Real-Time Shadow Mode Tracking
Track real-time market data in shadow mode:
```python
from src.Application.Shadow import ShadowModeEngine
# Start shadow session
# Execute periodic ticks on polling loops
# Track averages under read-only guidelines
```
