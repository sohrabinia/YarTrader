import json
from typing import Dict, Any

class ResearchReportGenerator:
    """
    Generates machine-readable JSON and human-readable Markdown research reports.
    Summarizes Train/Val/Test performance, Walk-Forward Optimization results, Overfitting diagnostics, and Baseline comparisons.
    """
    @staticmethod
    def generate_markdown_report(
        experiment_provenance: Dict[str, Any],
        baseline_comparison: Dict[str, Any],
        walk_forward_summary: Dict[str, Any],
        overfitting_summary: Dict[str, Any]
    ) -> str:
        md = []
        md.append("# YARTRADER RESEARCH OPTIMIZATION REPORT")
        md.append(f"**Experiment ID:** `{experiment_provenance.get('experiment_id')}`  ")
        md.append(f"**Commit SHA:** `{experiment_provenance.get('git_commit_sha')}`  ")
        md.append(f"**Dataset Hash:** `{experiment_provenance.get('dataset_hash')}`  ")
        md.append(f"**Symbol / TF:** `{experiment_provenance.get('symbol')} / {experiment_provenance.get('timeframe')}`  \n")

        md.append("---")
        md.append("## 1. BASELINE COMPARISON")
        verdict = baseline_comparison.get("comparison_verdict", "UNKNOWN")
        md.append(f"**Verdict:** `{verdict}`  ")
        md.append(f"**Net PnL Difference:** `${baseline_comparison.get('pnl_diff', 0.0):.2f}`  ")
        md.append(f"**Win Rate Difference:** `{baseline_comparison.get('win_rate_diff_pct', 0.0):.2f}%`  \n")

        md.append("---")
        md.append("## 2. WALK-FORWARD OPTIMIZATION (WFO) SUMMARY")
        md.append(f"**Windows Evaluated:** {walk_forward_summary.get('windows_evaluated', 0)}  ")
        md.append(f"**Profitable Windows:** {walk_forward_summary.get('profitable_windows', 0)} ({walk_forward_summary.get('profitability_ratio_pct', 0.0)}%)  ")
        md.append(f"**Aggregate OOS Net PnL:** `${walk_forward_summary.get('aggregate_oos_net_pnl', 0.0):.2f}`  \n")

        md.append("---")
        md.append("## 3. OVERFITTING DIAGNOSTICS")
        md.append(f"**Status:** `{overfitting_summary.get('status', 'UNKNOWN')}`  ")
        md.append(f"**Overfitting Detected:** `{overfitting_summary.get('overfitting_detected', False)}`  ")
        warnings = overfitting_summary.get("warning_reasons", [])
        if warnings:
            md.append("**Warnings:**")
            for w in warnings:
                md.append(f"- {w}")
        else:
            md.append("**Warnings:** None (Passes robustness criteria)")

        md.append("\n---")
        md.append("## 4. PROMOTION BOUNDARY NOTICE")
        md.append("```text")
        md.append("RESEARCH CANDIDATE ONLY — NO AUTOMATIC PRODUCTION PROMOTION")
        md.append("Trading Core remains 100% frozen. This research result does NOT replace live or demo trading configuration.")
        md.append("```")

        return "\n".join(md)

    @staticmethod
    def generate_json_report(payload: Dict[str, Any]) -> str:
        return json.dumps(payload, indent=2)
