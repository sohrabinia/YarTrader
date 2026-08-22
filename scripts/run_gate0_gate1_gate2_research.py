"""
Run Execution Script for Gates 0, 1, and 2
Processes historical dataset and outputs DataIntegrityReport, BaselineReport, and ScaleConstructionReport.
"""

import sys
import os
import json

# Add root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.Research.Brain.fractal_data_scale_engine import (
    MathematicalScaleDefinition,
    ResearchDataIntegrityEngine,
    ResearchBaselineEngine,
    ScaleConstructionEngine
)

def generate_historical_m1_dataset(count=1000):
    bars = []
    price = 2000.0
    for i in range(count):
        high = price + (i % 5) * 0.5 + 1.0
        low = price - (i % 3) * 0.4 - 0.5
        close = low + (high - low) * 0.6
        open_p = low + (high - low) * 0.4
        bars.append({
            "timestamp": 1700000000 + i * 60,
            "open": round(open_p, 2),
            "high": round(high, 2),
            "low": round(low, 2),
            "close": round(close, 2),
            "volume": 100 + (i % 10) * 10
        })
        price = close
    return bars

def load_authentic_real_dataset():
    """
    Loads authentic historical MT5 M1 dataset if available in data/research/.
    Does NOT fabricate synthetic data if absent.
    """
    candidate_paths = [
        "data/research/xauusd_m1_real.json",
        "data/research/xauusd_m1_historical.json"
    ]
    for path in candidate_paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                records = data.get("records", [])
                metadata = data.get("dataset_metadata", {})
                if records and not metadata.get("is_synthetic", False):
                    return records, metadata
    return None, None

def main():
    print("=" * 70)
    print("YarTrader Forensic Fractal Research — Gates 0, 1, & 2 Execution")
    print("=" * 70)

    # 1. Load Authentic Dataset
    real_bars, metadata = load_authentic_real_dataset()
    if not real_bars:
        print("REAL_DATA_UNAVAILABLE: No authentic MT5 M1 historical dataset found in data/research/.")
        print("Research execution stopped in accordance with Truthfulness Gate & Stop Condition.")
        os.makedirs("runtime_logs/research_center", exist_ok=True)
        report_stop = {
            "status": "REAL_DATA_UNAVAILABLE",
            "gate": 0,
            "passed": False,
            "message": "No authentic MT5 M1 historical market data file present in data/research/. Execution halted to prevent data fabrication."
        }
        with open("runtime_logs/research_center/DataIntegrityReport.json", "w", encoding="utf-8") as f:
            json.dump(report_stop, f, indent=2)
        return

    bars = real_bars
    source_id = metadata.get("source_identifier", "MT5_ALPARI_HISTORICAL_SNAPSHOT")
    version_id = metadata.get("immutable_version_id", "xauusd_m1_real")
    print(f"Loaded authentic historical dataset '{version_id}' from disk with {len(bars)} M1 records.")

    # 2. Mathematical Definition
    scale_def = MathematicalScaleDefinition.get_definition_summary()

    # 3. GATE 0 Data Integrity
    report_gate0 = ResearchDataIntegrityEngine.audit_dataset(bars, instrument="XAUUSD", source=source_id)
    report_gate0["data_classification"] = "REAL HISTORICAL DATA" if real_bars else "SYNTHETIC DATA"

    # 4. GATE 1 Baseline Benchmark
    report_gate1 = ResearchBaselineEngine.compute_baseline(bars, scale_factors=[1, 4, 16, 64])

    # 5. GATE 2 Scale Construction
    scaled_x4 = ScaleConstructionEngine.build_scale_family(bars, multiplier=4)
    scaled_x3 = ScaleConstructionEngine.build_scale_family(bars, multiplier=3)
    report_gate2 = ScaleConstructionEngine.audit_scale_construction(scaled_x4, scaled_x3)

    print("\n--- GATE 0: DataIntegrityReport ---")
    print(json.dumps(report_gate0, indent=2))

    print("\n--- GATE 1: BaselineReport ---")
    print(json.dumps(report_gate1, indent=2))

    print("\n--- GATE 2: ScaleConstructionReport ---")
    print(json.dumps(report_gate2, indent=2))

    # Output reports to disk
    os.makedirs("runtime_logs/research_center", exist_ok=True)
    with open("runtime_logs/research_center/DataIntegrityReport.json", "w", encoding="utf-8") as f:
        json.dump(report_gate0, f, indent=2)
    with open("runtime_logs/research_center/BaselineReport.json", "w", encoding="utf-8") as f:
        json.dump(report_gate1, f, indent=2)
    with open("runtime_logs/research_center/ScaleConstructionReport.json", "w", encoding="utf-8") as f:
        json.dump(report_gate2, f, indent=2)

    if real_bars:
        with open("runtime_logs/research_center/DataIntegrityReport_REAL.json", "w", encoding="utf-8") as f:
            json.dump(report_gate0, f, indent=2)
        with open("runtime_logs/research_center/BaselineReport_REAL.json", "w", encoding="utf-8") as f:
            json.dump(report_gate1, f, indent=2)
        with open("runtime_logs/research_center/ScaleConstructionReport_REAL.json", "w", encoding="utf-8") as f:
            json.dump(report_gate2, f, indent=2)

    print("\nReports successfully persisted in runtime_logs/research_center/")

if __name__ == "__main__":
    main()
