# YarTrader Final Claim Ledger

| Production Claim | Primary Source File | Primary Function / Gate | Regression Test File | Test Result | Audited Commit SHA | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **2.0% Risk Ceiling** | `src/Risk/Services/professional_risk_engine.py` | `evaluate_equity_risk_and_position_size` | `test_professional_risk_engine_bounds.py` | PASS | `d4e49c174b23db2edd6f78578b76cf9ba1a03fcd` | PASS |
| **MT4 Zero Order Authority** | `src/Execution/Adapters/mt4_adapter.py` | `send_order_to_broker` | `test_mt4_mt5_dual_pipeline.py` | PASS | `d4e49c174b23db2edd6f78578b76cf9ba1a03fcd` | PASS |
| **MT5 DEMO Boundary** | `src/Execution/Safety/demo_execution_gate.py` | `verify_demo_execution_eligibility` | `test_demo_execution_gate.py` | PASS | `d4e49c174b23db2edd6f78578b76cf9ba1a03fcd` | PASS |
| **8.0% Daily Loss Kill Switch** | `src/Risk/Services/daily_loss_kill_switch.py` | `evaluate_daily_loss` | `test_daily_loss_kill_switch.py` | PASS | `d4e49c174b23db2edd6f78578b76cf9ba1a03fcd` | PASS |
| **Range Regime Engine** | `src/Research/Brain/range_regime_engine.py` | `evaluate_regime` | `test_range_regime_engine.py` | PASS | `d4e49c174b23db2edd6f78578b76cf9ba1a03fcd` | PASS |
| **Data Anti-Contamination** | `src/Application/Services/web_dashboard.py` | `resolve_candles_for_context` | `test_web_dashboard.py` | PASS | `d4e49c174b23db2edd6f78578b76cf9ba1a03fcd` | PASS |
| **PPO Advisory Authority** | `src/RL/ppo_agent.py` | `get_action` | `test_hybrid_fractal_rl_pipeline.py` | PASS | `d4e49c174b23db2edd6f78578b76cf9ba1a03fcd` | PASS |
