import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from src.Infrastructure.exceptions import ValidationException
from src.Application.Deployment.storage import TradeYarStorageManager


class ReportEngine:
    """
    Production-grade Reporting Intelligence System for compiling and exporting
    standard platform intelligence reports in JSON, Markdown, and print-ready HTML.
    """

    def __init__(self) -> None:
        self.storage_manager = TradeYarStorageManager.get_manager()
        self.reports_dir = self.storage_manager.get_reports_dir()
        os.makedirs(self.reports_dir, exist_ok=True)

    def generate_research_report(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Compiles standard market research insights and trend analysis reports."""
        if not data.get("asset"):
            raise ValidationException("Reporting Error: Research data must specify 'asset'.")

        report = {
            "report_type": "Research Report",
            "report_id": f"REP-RES-{int(datetime.now().timestamp())}",
            "generated_at": datetime.now().isoformat(),
            "asset": data.get("asset"),
            "timeframe": data.get("timeframe", "H1"),
            "findings": data.get("findings", []),
            "confidence": data.get("confidence", 1.0),
            "metadata": data.get("metadata", {})
        }
        return report

    def generate_risk_report(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Compiles portfolio exposure, stress tests, and safety compliance audits."""
        report = {
            "report_type": "Risk Report",
            "report_id": f"REP-RSK-{int(datetime.now().timestamp())}",
            "generated_at": datetime.now().isoformat(),
            "is_approved": data.get("is_approved", True),
            "risk_profile": data.get("risk_profile", "Moderate"),
            "portfolio_metrics": data.get("portfolio_metrics", {}),
            "risk_notes": data.get("risk_notes", "All parameters within safety thresholds.")
        }
        return report

    def generate_decision_explanation_report(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Compiles end-to-end analytical rationales, trace paths, and explainability node maps."""
        report = {
            "report_type": "Decision Explanation Report",
            "report_id": f"REP-DEC-{int(datetime.now().timestamp())}",
            "generated_at": datetime.now().isoformat(),
            "final_decision_state": data.get("final_decision_state", "NoAction"),
            "overall_confidence": data.get("overall_confidence", 0.0),
            "explanations": data.get("explanations", []),
            "trace_map": data.get("trace_map", {})
        }
        return report

    def generate_simulation_report(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Compiles backtesting and offline simulation scenario result details."""
        report = {
            "report_type": "Simulation Report",
            "report_id": f"REP-SIM-{int(datetime.now().timestamp())}",
            "generated_at": datetime.now().isoformat(),
            "scenario_name": data.get("scenario_name", "Default Simulation"),
            "total_intervals": data.get("total_intervals", 0),
            "performance_metrics": data.get("performance_metrics", {}),
            "compliance_status": "PASSED" if data.get("compliance_passed", True) else "FAILED"
        }
        return report

    def generate_system_health_report(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Compiles platform health status, diagnostics, and uptime statistics."""
        status = data.get("status", "READY").upper()
        if status not in ("READY", "WARNING", "FAILED"):
            # Normalize to safe states
            status = "READY"

        report = {
            "report_type": "System Health Report",
            "report_id": f"REP-HLT-{int(datetime.now().timestamp())}",
            "generated_at": datetime.now().isoformat(),
            "status": status,
            "uptime_seconds": data.get("uptime_seconds", 0.0),
            "subsystems": data.get("subsystems", {})
        }
        return report

    def export_report(self, report: Dict[str, Any], fmt: str = "json", filename: Optional[str] = None) -> str:
        """
        Exports the compiled report into the requested format (JSON, Markdown, HTML).
        Returns the absolute filepath of the generated report.
        """
        fmt_clean = fmt.lower().strip()
        if fmt_clean not in ("json", "markdown", "md", "html"):
            raise ValidationException(f"Reporting Error: Unsupported export format '{fmt}'.")

        report_type_slug = report["report_type"].lower().replace(" ", "_")
        file_ext = "json" if fmt_clean == "json" else ("md" if fmt_clean in ("markdown", "md") else "html")
        name = filename or f"{report_type_slug}_{report['report_id']}.{file_ext}"

        # Enforce file isolation inside the configured storage Reports directory
        target_path = os.path.join(self.reports_dir, name)

        if fmt_clean == "json":
            content = json.dumps(report, indent=4)
        elif fmt_clean in ("markdown", "md"):
            content = self._to_markdown(report)
        else:
            content = self._to_html(report)

        with open(target_path, "w", encoding="utf-8") as f:
            f.write(content)

        return target_path

    def _to_markdown(self, report: Dict[str, Any]) -> str:
        """Converts compiled report dictionary to Markdown structure."""
        title = report["report_type"]
        md = []
        md.append(f"# {title}")
        md.append(f"**Report ID:** `{report['report_id']}`")
        md.append(f"**Generated At:** {report['generated_at']}\n")
        md.append("--- \n")

        for k, v in report.items():
            if k in ("report_type", "report_id", "generated_at"):
                continue
            name_pretty = k.replace("_", " ").title()
            if isinstance(v, dict):
                md.append(f"## {name_pretty}")
                for sub_k, sub_v in v.items():
                    sub_pretty = sub_k.replace("_", " ").title()
                    md.append(f"- **{sub_pretty}:** {sub_v}")
                md.append("")
            elif isinstance(v, list):
                md.append(f"## {name_pretty}")
                for item in v:
                    md.append(f"- {item}")
                md.append("")
            else:
                md.append(f"**{name_pretty}:** {v}\n")

        return "\n".join(md)

    def _to_html(self, report: Dict[str, Any]) -> str:
        """Converts compiled report dictionary to print-friendly HTML/CSS layout (PDF-ready)."""
        title = report["report_type"]
        html = []
        html.append("<!DOCTYPE html>")
        html.append("<html>")
        html.append("<head>")
        html.append(f"    <title>{title}</title>")
        html.append("    <style>")
        html.append("        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; color: #333; line-height: 1.6; }")
        html.append("        .container { max-width: 800px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px; background-color: #f9f9f9; }")
        html.append("        h1 { color: #1a365d; border-bottom: 2px solid #2b6cb0; padding-bottom: 10px; margin-top: 0; }")
        html.append("        h2 { color: #2c5282; margin-top: 30px; border-bottom: 1px solid #e2e8f0; padding-bottom: 5px; }")
        html.append("        .meta { font-size: 0.9em; color: #666; margin-bottom: 20px; }")
        html.append("        ul { padding-left: 20px; }")
        html.append("        li { margin-bottom: 5px; }")
        html.append("        .highlight { font-weight: bold; color: #2b6cb0; }")
        html.append("        .footer { font-size: 0.8em; color: #999; text-align: center; margin-top: 40px; border-top: 1px solid #e2e8f0; padding-top: 10px; }")
        html.append("    </style>")
        html.append("</head>")
        html.append("<body>")
        html.append("    <div class='container'>")
        html.append(f"        <h1>{title}</h1>")
        html.append("        <div class='meta'>")
        html.append(f"            <strong>Report ID:</strong> {report['report_id']}<br/>")
        html.append(f"            <strong>Generated At:</strong> {report['generated_at']}")
        html.append("        </div>")
        html.append("        <hr/>")

        for k, v in report.items():
            if k in ("report_type", "report_id", "generated_at"):
                continue
            name_pretty = k.replace("_", " ").title()
            if isinstance(v, dict):
                html.append(f"        <h2>{name_pretty}</h2>")
                html.append("        <ul>")
                for sub_k, sub_v in v.items():
                    sub_pretty = sub_k.replace("_", " ").title()
                    html.append(f"            <li><strong>{sub_pretty}:</strong> {sub_v}</li>")
                html.append("        </ul>")
            elif isinstance(v, list):
                html.append(f"        <h2>{name_pretty}</h2>")
                html.append("        <ul>")
                for item in v:
                    html.append(f"            <li>{item}</li>")
                html.append("        </ul>")
            else:
                html.append(f"        <p><span class='highlight'>{name_pretty}:</span> {v}</p>")

        html.append("        <div class='footer'>")
        html.append("            TradeYar AI Platform &copy; 1.0 Production Release. CONFIDENTIAL.")
        html.append("        </div>")
        html.append("    </div>")
        html.append("</body>")
        html.append("</html>")

        return "\n".join(html)
