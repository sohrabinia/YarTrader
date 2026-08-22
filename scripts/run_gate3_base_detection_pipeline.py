"""
YarTrader Master Task — Gate 3 Multi-Scale Base Detection Pipeline Runner
Executes ratio-agnostic Base discovery across constructed scale families (x3 and x4) on authentic market data.
Strictly enforces Truthfulness Gate (halts on REAL_DATA_UNAVAILABLE without synthetic fallback).
"""

import sys
import os
import json

# Add root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.Research.Brain.mt_data_acquisition import MTDataAcquisitionEngine
from src.Research.Brain.fractal_data_scale_engine import ScaleConstructionEngine
from src.Research.Brain.fractal_base_detection_engine import Gate3BaseDetectorEngine

def generate_persian_forensic_report(
    selection_report: dict,
    gate3_report_x4: dict,
    gate3_report_x3: dict
) -> dict:
    """
    Generates a Persian-readable forensic research report summarizing Gate 3 discoveries.
    """
    total_x4 = gate3_report_x4.get("total_bases_detected", 0)
    total_x3 = gate3_report_x3.get("total_bases_detected", 0)
    grand_total = total_x4 + total_x3

    verdict = "BASE_STRUCTURE_DETECTED" if grand_total >= 10 else ("WEAK_EVIDENCE" if grand_total > 0 else "NO_BASE_STRUCTURE_DETECTED")

    fa_verdict_explanation = {
        "BASE_STRUCTURE_DETECTED": "شواهد اولیه وجود نواحی تراکم (Base) در مقیاس‌های مختلف بازار تایید شد.",
        "WEAK_EVIDENCE": "شواهد ضعیف یا محدود از نواحی تراکم در مقیاس‌ها پیدا شد.",
        "NO_BASE_STRUCTURE_DETECTED": "هیچ ساختار Base معناداری در مقیاس‌های بررسی‌شده کشف نشد.",
        "REAL_DATA_UNAVAILABLE": "داده واقعی بازار در دسترس نیست. اجرای تحقیق متوقف شد."
    }

    x4_scales_summary = {}
    for s_label, s_data in gate3_report_x4.get("results_by_scale", {}).items():
        x4_scales_summary[s_label] = {
            "تعداد_کندل": s_data.get("bar_count", 0),
            "تعداد_بیس_کشف_شده": s_data.get("base_count", 0)
        }

    x3_scales_summary = {}
    for s_label, s_data in gate3_report_x3.get("results_by_scale", {}).items():
        x3_scales_summary[s_label] = {
            "تعداد_کندل": s_data.get("bar_count", 0),
            "تعداد_بیس_کشف_شده": s_data.get("base_count", 0)
        }

    return {
        "عنوان": "گزارش کشف فاز ۳ — شناسایی بیس‌های چندمقیاسه در داده واقعی بازار",
        "نسخه_الگوریتم": Gate3BaseDetectorEngine.ALGORITHM_VERSION,
        "ارزیابی_کلی": verdict,
        "توضیح_فارسی": fa_verdict_explanation.get(verdict, ""),
        "داده_ورودی": {
            "نماد": selection_report.get("symbol", "XAUUSD"),
            "کارگزار": selection_report.get("broker", "UNKNOWN"),
            "تعداد_کل_کندل_M1": selection_report.get("record_count", 0),
            "کیفیت_داده": selection_report.get("quality_status", "UNKNOWN"),
            "کلاس_داده": "REAL_HISTORICAL"
        },
        "نتایج_خانواده_x4": {
            "مجموع_بیس‌ها": total_x4,
            "جزئیات_مقیاس‌ها": x4_scales_summary
        },
        "نتایج_خانواده_x3": {
            "مجموع_بیس‌ها": total_x3,
            "جزئیات_مقیاس‌ها": x3_scales_summary
        },
        "اصول_تحقیق": "شناسایی بدون فرض قبلی درباره صحت فراکتال. داده‌ها مستقل در هر مقیاس تحلیل شده‌اند."
    }

def main():
    print("=" * 70)
    print("YarTrader Master Task — Gate 3 Multi-Scale Base Detection Pipeline")
    print("=" * 70)

    out_dir = "runtime_logs/research_center"
    os.makedirs(out_dir, exist_ok=True)

    # 1. Environment Discovery & Source Selection
    discovery = MTDataAcquisitionEngine.discover_environment()
    selection_report = MTDataAcquisitionEngine.select_data_source(discovery)

    if selection_report.get("quality_status") == "REAL_DATA_UNAVAILABLE":
        print("\n" + "!" * 70)
        print("FINAL VERDICT: REAL_DATA_UNAVAILABLE")
        print("Reason:", selection_report.get("selection_reason"))
        print("!" * 70)

        report_halt = {
            "gate": 3,
            "gate_name": "Multi-Scale Base Detection",
            "verdict": "REAL_DATA_UNAVAILABLE",
            "DATA_CLASSIFICATION": "REAL_DATA_UNAVAILABLE",
            "message": "Gate 3 execution halted. Authentic MT4/MT5 historical market dataset unavailable."
        }
        with open(os.path.join(out_dir, "Gate3_BaseDetectionReport_REAL.json"), "w", encoding="utf-8") as f:
            json.dump(report_halt, f, indent=2)
        return

    selected_file = selection_report.get("selected_filepath")
    bars, metadata = MTDataAcquisitionEngine.load_authentic_dataset(selected_file)

    if not bars:
        print("\nFINAL VERDICT: REAL_DATA_UNAVAILABLE")
        return

    print(f"\nLoaded authentic dataset with {len(bars)} M1 records for Gate 3 analysis.")

    # 2. Scale Construction (x4 and x3)
    scaled_x4 = ScaleConstructionEngine.build_scale_family(bars, multiplier=4)
    scaled_x3 = ScaleConstructionEngine.build_scale_family(bars, multiplier=3)

    # 3. Gate 3 Ratio-Agnostic Base Detection
    detector = Gate3BaseDetectorEngine(min_duration_bars=4, max_compression_threshold=1.2)
    gate3_x4 = detector.detect_multiscale_bases(scaled_x4)
    gate3_x3 = detector.detect_multiscale_bases(scaled_x3)

    grand_total_bases = gate3_x4["total_bases_detected"] + gate3_x3["total_bases_detected"]
    verdict = "BASE_STRUCTURE_DETECTED" if grand_total_bases >= 10 else ("WEAK_EVIDENCE" if grand_total_bases > 0 else "NO_BASE_STRUCTURE_DETECTED")

    combined_gate3_report = {
        "gate": 3,
        "gate_name": "Multi-Scale Base Detection",
        "verdict": verdict,
        "DATA_CLASSIFICATION": "REAL_HISTORICAL",
        "grand_total_bases_detected": grand_total_bases,
        "family_x4_results": gate3_x4,
        "family_x3_results": gate3_x3,
        "sha256_dataset_hash": metadata.get("sha256_hash")
    }

    persian_report = generate_persian_forensic_report(selection_report, gate3_x4, gate3_x3)

    # Save reports
    with open(os.path.join(out_dir, "Gate3_BaseDetectionReport_REAL.json"), "w", encoding="utf-8") as f:
        json.dump(combined_gate3_report, f, indent=2)
    with open(os.path.join(out_dir, "Gate3_PersianForensicReport_REAL.json"), "w", encoding="utf-8") as f:
        json.dump(persian_report, f, ensure_ascii=False, indent=2)

    print(f"\nGate 3 Base Detection completed. Total Bases Detected: {grand_total_bases}")
    print(f"FINAL VERDICT: {verdict}")

if __name__ == "__main__":
    main()
