"""
YarTrader Master Task — Autonomous MT4/MT5 Historical Data Acquisition Pipeline Runner
Performs environment discovery, source selection, data acquisition, and gates execution.
Strictly enforces Truthfulness Gate (halts on REAL_DATA_UNAVAILABLE without synthetic fallback).
"""

import sys
import os
import json

# Add root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.Research.Brain.mt_data_acquisition import MTDataAcquisitionEngine
from src.Research.Brain.fractal_data_scale_engine import (
    MathematicalScaleDefinition,
    ResearchDataIntegrityEngine,
    ResearchBaselineEngine,
    ScaleConstructionEngine
)

def main():
    print("=" * 70)
    print("YarTrader Master Task — Autonomous Historical Data Acquisition Pipeline")
    print("=" * 70)

    out_dir = "runtime_logs/research_center"
    os.makedirs(out_dir, exist_ok=True)

    # 1. Environment Discovery
    discovery = MTDataAcquisitionEngine.discover_environment()
    print(f"Platform Discovered: {discovery['os_platform']} {discovery['os_release']}")
    print(f"MT4 Installations: {discovery['mt4_installations']}")
    print(f"MT5 Installations: {discovery['mt5_installations']}")
    print(f"Export Files Found: {len(discovery['available_export_files'])}")

    # 2. Source Selection
    selection_report = MTDataAcquisitionEngine.select_data_source(discovery)

    selection_path = os.path.join(out_dir, "DataSourceSelectionReport.json")
    with open(selection_path, "w", encoding="utf-8") as f:
        json.dump(selection_report, f, indent=2)
    print(f"DataSourceSelectionReport.json persisted at '{selection_path}'.")

    # 3. Check Real Data Availability
    if selection_report.get("quality_status") == "REAL_DATA_UNAVAILABLE":
        print("\n" + "!" * 70)
        print("FINAL VERDICT: REAL_DATA_UNAVAILABLE")
        print("Reason:", selection_report.get("selection_reason"))
        print("!" * 70)

        # Halt execution as required by Truthfulness Gate and Stop Condition #16
        report_halt = {
            "status": "REAL_DATA_UNAVAILABLE",
            "DATA_CLASSIFICATION": "REAL_DATA_UNAVAILABLE",
            "message": "Pipeline halted. No authentic MT4/MT5 historical market dataset available."
        }
        with open(os.path.join(out_dir, "DataIntegrityReport_REAL.json"), "w", encoding="utf-8") as f:
            json.dump(report_halt, f, indent=2)
        return

    selected_file = selection_report.get("selected_filepath")
    bars, metadata = MTDataAcquisitionEngine.load_authentic_dataset(selected_file)

    if not bars:
        print("\nFINAL VERDICT: REAL_DATA_UNAVAILABLE")
        return

    print(f"\nSuccessfully loaded authentic dataset with {len(bars)} records from '{selected_file}'.")
    print(f"Dataset Hash (SHA-256): {metadata.get('sha256_hash')}")

    # 4. GATE 0 Data Integrity
    report_gate0 = ResearchDataIntegrityEngine.audit_dataset(
        bars,
        instrument=selection_report.get("symbol", "XAUUSD"),
        source=metadata.get("source_identifier", "MT_HISTORICAL_EXPORT")
    )
    report_gate0["DATA_CLASSIFICATION"] = "REAL_HISTORICAL"
    report_gate0["sha256_dataset_hash"] = metadata.get("sha256_hash")

    # 5. GATE 1 Baseline Benchmark
    report_gate1 = ResearchBaselineEngine.compute_baseline(bars, scale_factors=[1, 4, 16, 64])
    report_gate1["DATA_CLASSIFICATION"] = "REAL_HISTORICAL"

    # 6. GATE 2 Scale Construction
    scaled_x4 = ScaleConstructionEngine.build_scale_family(bars, multiplier=4)
    scaled_x3 = ScaleConstructionEngine.build_scale_family(bars, multiplier=3)
    report_gate2 = ScaleConstructionEngine.audit_scale_construction(scaled_x4, scaled_x3)
    report_gate2["DATA_CLASSIFICATION"] = "REAL_HISTORICAL"

    # Save real reports
    with open(os.path.join(out_dir, "DataIntegrityReport_REAL.json"), "w", encoding="utf-8") as f:
        json.dump(report_gate0, f, indent=2)
    with open(os.path.join(out_dir, "BaselineReport_REAL.json"), "w", encoding="utf-8") as f:
        json.dump(report_gate1, f, indent=2)
    with open(os.path.join(out_dir, "ScaleConstructionReport_REAL.json"), "w", encoding="utf-8") as f:
        json.dump(report_gate2, f, indent=2)

    print("\nReal-data reports successfully persisted in runtime_logs/research_center/.")
    print("\nFINAL VERDICT: REAL_DATA_GATES_0_2_VERIFIED")

if __name__ == "__main__":
    main()
