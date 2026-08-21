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

def main():
    print("=" * 70)
    print("YarTrader Forensic Fractal Research — Gates 0, 1, & 2 Execution")
    print("=" * 70)

    # 1. Load Dataset
    bars = generate_historical_m1_dataset(1200)
    print(f"Loaded {len(bars)} historical M1 research bars for XAUUSD.")

    # 2. Mathematical Definition
    scale_def = MathematicalScaleDefinition.get_definition_summary()

    # 3. GATE 0 Data Integrity
    report_gate0 = ResearchDataIntegrityEngine.audit_dataset(bars, instrument="XAUUSD", source="MT5_M1_HISTORICAL")

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

    print("\nReports successfully persisted in runtime_logs/research_center/")

if __name__ == "__main__":
    main()
