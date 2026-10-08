        except ImportError:
            mt5_lib_ok = False

        results["mt5"] = {
            "name": "MetaTrader 5 Link",
            "status": "PASSED" if (is_windows and mt5_lib_ok) else "SIMULATED_FALLBACK",
            "details": "MT5 Terminal Connection Active" if (is_windows and mt5_lib_ok) else "Synthetic Fallback Mode Active (Non-Windows platform)"
        }
        self.log(f"MT5 Verification: {results['mt5']['details']}")

        return results

    def run_automated_tests(self) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Part 6: Complete Automatic Test Discovery & Deterministic Partitioned Execution"""
        self.log("Starting automatic test discovery and deterministic partitioned execution...")
        start_time = time.perf_counter()

        # Non-overlapping partition mapping covering 100% of the repository test suite
        PARTITIONS = [
            ("Gate 1 Suite", ["tests/YarTrader.Tests/Gate1/"]),
            ("Gate 2 Suite", ["tests/YarTrader.Tests/Gate2/"]),
            ("Forensic Safety Suite", ["tests/YarTrader.Tests/Forensic/"]),
            ("Risk Subsystem", ["tests/YarTrader.Tests/Risk/"]),
            ("Agents & Growth Subsystem", [
                "tests/YarTrader.Tests/Agents/", "tests/YarTrader.Tests/Growth/",
                "tests/YarTrader.Tests/Collaboration/", "tests/YarTrader.Tests/Supervisor/"
            ]),
            ("Dashboard Subsystem", ["tests/YarTrader.Tests/Dashboard/"]),
            ("Data & Timeframes & Providers & Monitoring", [
                "tests/YarTrader.Tests/Data/", "tests/YarTrader.Tests/Timeframes/",
                "tests/YarTrader.Tests/Providers/", "tests/YarTrader.Tests/Monitoring/",
                "tests/YarTrader.Tests/Universe/"
            ]),
            ("Execution Subsystem", ["tests/YarTrader.Tests/Execution/"]),
            ("Learning Subsystem", ["tests/YarTrader.Tests/Learning/"]),
            ("Backtesting Subsystem", ["tests/YarTrader.Tests/Backtesting/"]),
            ("Audit & SDDL & Compliance", ["tests/YarTrader.Tests/Audit/", "tests/YarTrader.Tests/SDDL/", "tests/YarTrader.Tests/Compliance/"]),
            ("Pipeline Subsystem", ["tests/YarTrader.Tests/Pipeline/"]),
            ("Brain Subsystem", [
                "tests/YarTrader.Tests/Brain/", "tests/YarTrader.Tests/Decision/",
                "tests/YarTrader.Tests/Explainability/"
            ]),
            ("Integration & Services & Shadow", [
                "tests/YarTrader.Tests/Integration/", "tests/YarTrader.Tests/Services/",
                "tests/YarTrader.Tests/Shadow/", "tests/YarTrader.Tests/Communication/",
                "tests/YarTrader.Tests/Context/", "tests/YarTrader.Tests/Conversation/",
                "tests/YarTrader.Tests/Demo/"
            ]),
            ("Architecture & Intelligence & Knowledge & Orchestration & Research", ["tests/YarTrader.Tests/Architecture/", "tests/YarTrader.Tests/Intelligence/", "tests/YarTrader.Tests/Knowledge/", "tests/YarTrader.Tests/Orchestration/", "tests/YarTrader.Tests/Research/"]),
            ("General Runtime Core Tests A", [
                "tests/runtime/test_api_startup.py",
                "tests/runtime/test_config_loading.py",
                "tests/runtime/test_health_endpoint.py",
                "tests/runtime/test_health_status.py"
            ]),
            ("General Runtime Core Tests B", [
                "tests/runtime/test_logging.py",
                "tests/runtime/test_mt5_mock_connection.py",
                "tests/runtime/test_research_health_metrics.py",
                "tests/runtime/test_safety_gate_fail_closed.py"
            ]),
            ("General Runtime Services Tests", [
                "tests/runtime/test_service_host.py",
                "tests/runtime/test_sre_operational.py",
                "tests/runtime/test_worker_lifecycle.py"
            ]),
            ("General Runtime Validation Tests", [
                "tests/runtime/test_validate_release_partitioning.py",
                "tests/YarTrader.Tests/Runtime/",
                "tests/YarTrader.Tests/Validation/"
            ]),
            ("General Deployment & Infrastructure Tests", [
                "tests/YarTrader.Tests/Deployment/",
                "tests/YarTrader.Tests/Infrastructure/",
                "tests/YarTrader.Tests/Memory/"
            ]),
            ("General Core & Intelligence Tests A", [
                "tests/test_core.py", "tests/test_data_intelligence.py", "tests/test_decision.py",
                "tests/test_decision_intelligence.py", "tests/test_feature_extraction.py",
                "tests/test_full_intelligence_validation.py", "tests/test_historical_data_adapter.py",
                "tests/test_integration_and_production.py", "tests/test_learning.py",
                "tests/test_learning_optimization.py", "tests/test_mt5_production_session2_bridge.py"
            ]),
            ("General Core & Intelligence Tests B", [
                "tests/test_pipeline_integration.py", "tests/test_platform_integration.py",
                "tests/test_research_engine.py", "tests/test_research_intelligence.py",
                "tests/test_research_worker_symbol_availability.py", "tests/test_risk.py",
                "tests/test_simulation_scenarios.py", "tests/test_strategy_evaluation.py",
                "tests/test_strategy_intelligence.py"
            ])
        ]

        # Validate the partition map itself before selecting a partition.  This is
        # deliberately fail-closed: a stale/ambiguous map must never silently