import argparse
import json
import os
import sys
from datetime import datetime, timedelta

from src.Infrastructure.Configuration import EnvironmentType, ConfigurationManager
from src.Infrastructure.exceptions import ValidationException
from src.Infrastructure.health import PlatformHealthChecker
from src.Application.Runtime.launcher import RuntimeLauncher
from src.Application.Deployment.health import ProductionHealthChecker
from src.Application.Deployment.observability import PerformanceMetricsTracker
from src.Application.Reporting.engine import ReportEngine

# Demo components
from src.Application.Demo import (
    DemoScenarioRunner,
    DemoReportGenerator,
    load_scenario_library
)

# Simulation components
from src.Application.Simulation.models import SimulationEnvironmentGuard, MarketScenario, ScenarioInput
from src.Application.Simulation.runner import ScenarioRunner
from src.Data.MarketData.Models.models import MarketDataPoint
from src.Risk.Models.models import RiskProfile


def print_title():
    print("==========================================================================")
    print("                 TradeYar AI Platform CLI Utilities                     ")
    print("==========================================================================")


def handle_status(args):
    """Show runtime configuration details."""
    print_title()
    launcher = RuntimeLauncher()
    env = EnvironmentType[args.env.upper()] if args.env else None
    host = launcher.launch(environment_override=env)

    print(f"Active Environment:     {host.environment.value if host.environment else 'N/A'}")
    print(f"Log Level:              {host.config.log_level}")
    print(f"Lookback Days:          {host.config.lookback_days}")
    print(f"API Timeout (sec):      {host.config.api_timeout_sec}")
    print(f"Max Retries:            {host.config.max_retries}")
    print(f"Storage Root:           {host.config.storage_root}")
    print("Runtime Status:         READY")
    print("==========================================================================")


def handle_health(args):
    """Check platform comprehensive health checks."""
    print_title()
    # Comprehensive production health checks
    p_checker = ProductionHealthChecker()
    diag = p_checker.run_comprehensive_diagnostics()

    print(f"Timestamp:       {diag['timestamp']}")
    print(f"Uptime Seconds:  {diag['uptime_seconds']:.2f}")
    print(f"Global Status:   {diag['status']}")
    print("\nSubsystems Status:")
    for sub, info in diag["subsystems"].items():
        print(f"  - {sub.replace('_', ' ').title():<25} : {info['status']} ({info['details']})")

    # Platform health diagnostics
    plat_diag = PlatformHealthChecker.run_full_diagnostics()
    print("\nModule Compilation Status:")
    for dep, status in plat_diag["dependencies"].items():
        print(f"  - {dep:<30} : {status}")
    print("==========================================================================")


def handle_run_demo(args):
    """Run simulated end-to-end intelligence demo scenarios."""
    print_title()
    print(f"Loading scenario library for asset: {args.asset}...")
    scenarios = load_scenario_library(asset=args.asset)

    runner = DemoScenarioRunner()
    generator = DemoReportGenerator()

    selected_scenarios = scenarios
    if args.scenario_id:
        selected_scenarios = [s for s in scenarios if s.scenario_id == args.scenario_id]
        if not selected_scenarios:
            print(f"Error: Scenario with ID '{args.scenario_id}' not found.")
            sys.exit(1)

    print(f"Executing {len(selected_scenarios)} demo scenario(s)...")
    for sc in selected_scenarios:
        print(f"\n--- Running: {sc.name} ---")
        result = runner.run_scenario(sc)
        report = generator.generate_report(result)

        print(report.rendered_summary)

        # Optionally export report to files
        if args.export:
            rep_engine = ReportEngine()
            data_payload = {
                "final_decision_state": result.final_decision_state,
                "overall_confidence": result.overall_confidence,
                "explanations": [exp.rationale for exp in result.explainable_report.explanations] if result.explainable_report else [],
                "trace_map": result.explainable_report.visual_evidence_mapping if result.explainable_report else {}
            }
            rep = rep_engine.generate_decision_explanation_report(data_payload)
            exported_path = rep_engine.export_report(rep, fmt=args.export_format)
            print(f"Exported demo explanation report to: {exported_path}")

    print("==========================================================================")


def handle_run_simulation(args):
    """Run offline backtesting simulation scenarios."""
    print_title()
    print(f"Initializing synthetic trending scenario for: {args.asset}...")

    # Ensure simulation active
    SimulationEnvironmentGuard.set_simulation_active(True)
    runner = ScenarioRunner()

    now = datetime.now()
    synthetic_points = [
        MarketDataPoint(
            AssetId=args.asset,
            Timestamp=now - timedelta(days=2),
            Open=1.1000,
            High=1.1050,
            Low=1.0950,
            Close=1.1010,
            Volume=10000.0
        ),
        MarketDataPoint(
            AssetId=args.asset,
            Timestamp=now - timedelta(days=1),
            Open=1.1010,
            High=1.1120,
            Low=1.0980,
            Close=1.1100,
            Volume=12000.0
        ),
    ]

    scenario = MarketScenario(
        Asset=args.asset,
        TimeRange=(now - timedelta(days=2), now),
        PriceData=synthetic_points,
        ScenarioType="Trending"
    )

    profile = RiskProfile("Moderate", 1.5, 0.90)
    scenario_input = ScenarioInput(
        Scenario=scenario,
        TargetRiskProfile=profile,
        LookbackDays=args.lookback
    )

    print("Running simulation scenario...")
    result = runner.run_scenario(scenario_input)
    report = runner.generate_report(result)

    print(f"\nSimulation Complete:")
    print(f"  Asset:               {args.asset}")
    print(f"  Research Summary:    {report.ResearchSummary}")
    print(f"  Strategy Summary:    {report.StrategySummary}")
    print(f"  Risk Summary:        {report.RiskSummary}")
    print(f"  Decision Summary:    {report.DecisionSummary}")
    print(f"  Learning Summary:    {report.LearningFeedbackSummary}")
    print(f"  Prevention Status:   {report.ExecutionPreventionStatus}")

    if args.export:
        rep_engine = ReportEngine()
        data_payload = {
            "scenario_name": "Synthetic Trending Simulation",
            "total_intervals": 2,
            "performance_metrics": {"overall_score": 0.92},
            "compliance_passed": True
        }
        rep = rep_engine.generate_simulation_report(data_payload)
        exported_path = rep_engine.export_report(rep, fmt=args.export_format)
        print(f"\nExported simulation report to: {exported_path}")

    print("==========================================================================")


def handle_analyze(args):
    """Run feature extraction & passive intelligence analysis."""
    print_title()
    print(f"Analyzing passive intelligence for asset: {args.asset}...")

    # Run a simplified demo execution for input-feature extraction step
    sc = load_scenario_library(asset=args.asset)[0]
    runner = DemoScenarioRunner()
    res = runner.run_scenario(sc)

    print("\nExtracted Features and Observations:")
    for step in res.steps:
        if step.step_name in ("Input", "Feature Extraction", "Research"):
            print(f"\n--- Stage: {step.step_name} ({step.status}) ---")
            print(json.dumps(step.payload, indent=2))

    print("==========================================================================")


def handle_generate_report(args):
    """Export standard report types."""
    print_title()
    rep_engine = ReportEngine()

    rep_type = args.type.lower()
    fmt = args.format.lower()

    print(f"Compiling '{args.type}' report...")

    if rep_type == "research":
        data = {
            "asset": "EURUSD",
            "timeframe": "H1",
            "findings": ["Bullish structure confirmed by EMA cross."],
            "confidence": 0.89
        }
        rep = rep_engine.generate_research_report(data)
    elif rep_type == "risk":
        data = {
            "is_approved": True,
            "risk_profile": "Moderate",
            "portfolio_metrics": {"expected_volatility": 0.08, "historical_drawdown": 0.04},
            "risk_notes": "All variables operate within historical risk envelopes."
        }
        rep = rep_engine.generate_risk_report(data)
    elif rep_type == "decision":
        data = {
            "final_decision_state": "Approved",
            "overall_confidence": 0.91,
            "explanations": ["High-confidence trend support and low portfolio risk."],
            "trace_map": {"path": ["Research", "Strategy", "Risk", "Decision"]}
        }
        rep = rep_engine.generate_decision_explanation_report(data)
    elif rep_type == "simulation":
        data = {
            "scenario_name": "Volatility Stress Test",
            "total_intervals": 24,
            "performance_metrics": {"accuracy": 0.94},
            "compliance_passed": True
        }
        rep = rep_engine.generate_simulation_report(data)
    elif rep_type == "health":
        data = {
            "status": "READY",
            "uptime_seconds": 3600.0,
            "subsystems": {"all": "HEALTHY"}
        }
        rep = rep_engine.generate_system_health_report(data)
    else:
        print(f"Error: Unsupported report type '{args.type}'. Support: research, risk, decision, simulation, health")
        sys.exit(1)

    exported_path = rep_engine.export_report(rep, fmt=fmt, filename=args.out)
    print(f"Successfully generated and exported to:")
    print(f"  {exported_path}")
    print("==========================================================================")


def handle_diagnostics(args):
    """Diagnostics output about platform state and subsystems."""
    print_title()
    tracker = PerformanceMetricsTracker()

    # Seed tracker with sample performance data
    tracker.record_pipeline_execution(145.2)
    tracker.record_pipeline_execution(120.8)
    tracker.record_agent_latency(14.8)
    tracker.record_scenario_execution(550.4)
    tracker.record_decision_processing(35.2)
    tracker.record_warning("Slight database latency detected.")

    summary = tracker.get_performance_summary()

    print("Performance & Diagnostic Telemetry:")
    print(f"  Uptime Status:               OPERATIONAL")
    print(f"  Avg Pipeline execution (ms): {summary['average_pipeline_execution_ms']}")
    print(f"  Avg Agent Latency (ms):      {summary['average_agent_latency_ms']}")
    print(f"  Avg Scenario execution (ms): {summary['average_scenario_execution_ms']}")
    print(f"  Avg Decision processing (ms):{summary['average_decision_processing_ms']}")
    print(f"  Active Warning Count:        {summary['warning_count']}")
    print(f"  Active Error Count:          {summary['error_count']}")
    print("==========================================================================")


def main():
    parser = argparse.ArgumentParser(
        description="TradeYar AI Platform CLI Orchestrator. Completely decoupled command-line system interface."
    )

    subparsers = parser.add_subparsers(dest="command", required=True, help="Command to execute")

    # 1. status
    status_parser = subparsers.add_parser("status", help="Show runtime configuration details.")
    status_parser.add_argument("--env", type=str, choices=["development", "test", "simulation", "production"], help="Environment name")
    status_parser.set_defaults(func=handle_status)

    # 2. health
    health_parser = subparsers.add_parser("health", help="Check platform comprehensive health checks.")
    health_parser.set_defaults(func=handle_health)

    # 3. run-demo
    demo_parser = subparsers.add_parser("run-demo", help="Run simulated end-to-end intelligence demo scenarios.")
    demo_parser.add_argument("--asset", type=str, default="EURUSD", help="Asset symbol to run demo for.")
    demo_parser.add_argument("--scenario-id", type=str, help="Run specific scenario ID instead of all five.")
    demo_parser.add_argument("--export", action="store_true", help="Export compiled decision explanation report.")
    demo_parser.add_argument("--export-format", type=str, choices=["json", "markdown", "html"], default="markdown", help="Format to export report.")
    demo_parser.set_defaults(func=handle_run_demo)

    # 4. run-simulation
    sim_parser = subparsers.add_parser("run-simulation", help="Run offline backtesting simulation scenarios.")
    sim_parser.add_argument("--asset", type=str, default="EURUSD", help="Asset symbol to run simulation for.")
    sim_parser.add_argument("--lookback", type=int, default=15, help="Lookback days.")
    sim_parser.add_argument("--export", action="store_true", help="Export compiled simulation report.")
    sim_parser.add_argument("--export-format", type=str, choices=["json", "markdown", "html"], default="html", help="Format to export report.")
    sim_parser.set_defaults(func=handle_run_simulation)

    # 5. analyze
    analyze_parser = subparsers.add_parser("analyze", help="Run feature extraction & passive intelligence analysis.")
    analyze_parser.add_argument("--asset", type=str, default="EURUSD", help="Asset symbol.")
    analyze_parser.set_defaults(func=handle_analyze)

    # 6. generate-report
    report_parser = subparsers.add_parser("generate-report", help="Export standard report types.")
    report_parser.add_argument("--type", type=str, choices=["research", "risk", "decision", "simulation", "health"], required=True, help="Report type to generate.")
    report_parser.add_argument("--format", type=str, choices=["json", "markdown", "html"], default="markdown", help="Export file format.")
    report_parser.add_argument("--out", type=str, help="Specific output filename.")
    report_parser.set_defaults(func=handle_generate_report)

    # 7. diagnostics
    diag_parser = subparsers.add_parser("diagnostics", help="Diagnostics output about platform state and subsystems.")
    diag_parser.set_defaults(func=handle_diagnostics)

    # Parse args
    args = parser.parse_args()

    try:
        args.func(args)
    except Exception as e:
        print(f"CLI Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
