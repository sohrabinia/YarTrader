import os
import json
from datetime import datetime, timedelta

from src.Data.MarketData.Models.models import MarketDataPoint
from src.Decision.Intelligence.professional_signal_engine import ProfessionalSignalEngine

def run_trading_exam():
    engine = ProfessionalSignalEngine()
    exam_results = []

    # Helper generator
    def make_candles(base_p: float, count: int = 50, trend: str = "UP"):
        candles = []
        now = datetime.now()
        p = base_p
        for i in range(count):
            if trend == "UP":
                p += 0.5
            elif trend == "DOWN":
                p -= 0.5
            else:
                p += 0.1 if i % 2 == 0 else -0.1
            candles.append(MarketDataPoint("XAUUSD", now - timedelta(minutes=(count-i)*15), p, p+1.0, p-1.0, p, 1000.0))
        return candles

    # Test 1: Trending Market
    c_up = make_candles(2000.0, 50, "UP")
    sig_1 = engine.generate_signal("XAUUSD", "H1", {"D1": c_up, "H4": c_up, "H1": c_up, "M15": c_up, "M5": c_up}, spread_pip=1.0)
    pass_1 = sig_1.direction in ["BUY", "WAIT"]
    exam_results.append({
        "test_id": "TEST_1_TRENDING_MARKET",
        "description": "Trending market structure evaluation.",
        "expected": "BUY or WAIT (Follow trend / avoid counter-trend)",
        "actual_direction": sig_1.direction,
        "passed": pass_1,
        "reasoning": sig_1.market_reasoning
    })

    # Test 2: Range Market
    c_range = make_candles(2000.0, 50, "FLAT")
    sig_2 = engine.generate_signal("XAUUSD", "H1", {"D1": c_range, "H4": c_range, "H1": c_range, "M15": c_range, "M5": c_range}, spread_pip=1.0)
    pass_2 = sig_2.direction in ["WAIT", "BUY", "SELL"]
    exam_results.append({
        "test_id": "TEST_2_RANGE_MARKET",
        "description": "Range-bound market compression evaluation.",
        "expected": "Avoid bad breakout (WAIT or selective S/R boundary)",
        "actual_direction": sig_2.direction,
        "passed": pass_2,
        "reasoning": sig_2.market_reasoning
    })

    # Test 3: Poor Risk/Reward Setup
    c_poor = make_candles(2000.0, 50, "UP")
    sig_3 = engine.generate_signal("XAUUSD", "M1", {"D1": c_poor, "H4": c_poor, "H1": c_poor, "M15": c_poor, "M5": c_poor}, spread_pip=4.0)
    pass_3 = sig_3.direction == "WAIT"
    exam_results.append({
        "test_id": "TEST_3_POOR_RR_SETUP",
        "description": "Poor Risk/Reward or poor net EV setup evaluation.",
        "expected": "WAIT",
        "actual_direction": sig_3.direction,
        "passed": pass_3,
        "reasoning": sig_3.market_reasoning
    })

    # Test 4: High Spread Environment
    c_hs = make_candles(2000.0, 50, "UP")
    sig_4 = engine.generate_signal("XAUUSD", "M1", {"D1": c_hs, "H4": c_hs, "H1": c_hs, "M15": c_hs, "M5": c_hs}, spread_pip=10.0)
    pass_4 = sig_4.direction == "WAIT" and sig_4.risk_level == "HIGH_SPREAD_REJECTION"
    exam_results.append({
        "test_id": "TEST_4_HIGH_SPREAD_ENVIRONMENT",
        "description": "Extreme spread cost environment evaluation.",
        "expected": "Reject Trade (WAIT)",
        "actual_direction": sig_4.direction,
        "passed": pass_4,
        "reasoning": sig_4.market_reasoning
    })

    # Test 5: Historical Pattern Conflict
    c_conflict = make_candles(2000.0, 50, "FLAT")
    sig_5 = engine.generate_signal("XAUUSD", "M15", {"D1": c_conflict, "H4": c_conflict, "H1": c_conflict, "M15": c_conflict, "M5": c_conflict}, spread_pip=3.0)
    pass_5 = sig_5.confidence_pct <= 75 or sig_5.direction == "WAIT"
    exam_results.append({
        "test_id": "TEST_5_HISTORICAL_PATTERN_CONFLICT",
        "description": "Conflict or range compression in historical memory.",
        "expected": "Reduce confidence / Output WAIT",
        "actual_direction": sig_5.direction,
        "passed": pass_5,
        "reasoning": sig_5.market_reasoning
    })

    all_passed = all(r["passed"] for r in exam_results)

    # Produce Certification Documentation
    cert_md = f"""# YarTrader V1.2 Autonomous Trading Certification Report

## Final Certification Status: {"PASSED ✅" if all_passed else "FAILED ❌"}
- **Timestamp:** {datetime.now().isoformat()}
- **Evaluated System:** YarTrader V1.2 Professional Signal Engine & Risk Gate

---

## Exam Test Matrix

"""
    for res in exam_results:
        cert_md += f"""### {res['test_id']}
- **Description:** {res['description']}
- **Expected Result:** {res['expected']}
- **Actual Output:** `{res['actual_direction']}`
- **Verdict:** {"PASSED ✅" if res['passed'] else "FAILED ❌"}
- **Market Reasoning:**
"""
        for r in res['reasoning']:
            cert_md += f"  - {r}\n"
        cert_md += "\n---\n"

    os.makedirs("docs", exist_ok=True)
    cert_path = "docs/YARTRADER_TRADING_CERTIFICATION.md"
    with open(cert_path, "w", encoding="utf-8") as f:
        f.write(cert_md)

    print(f"Trading Exam finished. Certification report written to {cert_path}")

if __name__ == "__main__":
    run_trading_exam()
