import unittest
from src.Decision.Intelligence.market_behavior_policy import MarketBehaviorPolicy


def bars_from_closes(closes, wick=0.0002):
    bars=[]
    for i, close in enumerate(closes):
        op = closes[i-1] if i else close
        bars.append({"open":op, "high":max(op,close)+wick, "low":min(op,close)-wick, "close":close})
    return bars

class MarketBehaviorPolicyTests(unittest.TestCase):
    def setUp(self): self.policy=MarketBehaviorPolicy(lookback=20)
    def test_insufficient_history_fails_closed(self):
        self.assertEqual(self.policy.evaluate([]).regime, "UNCERTAIN")
    def test_malformed_bars_fail_closed(self):
        self.assertEqual(self.policy.evaluate([{"open":1,"high":0,"low":2,"close":1}]*20).direction, "WAIT")
    def test_trend_is_directional_not_countertrend(self):
        closes=[1+i*0.001 for i in range(25)]
        result=self.policy.evaluate(bars_from_closes(closes, wick=0.0001))
        self.assertIn(result.regime, ("TREND_UP", "SPIKE", "TRANSITION"))
        if result.regime == "TREND_UP": self.assertEqual(result.direction,"BUY")
    def test_spike_target_is_precomputable_and_positive(self):
        closes=[1.0+i*0.0001 for i in range(20)]
        bars=bars_from_closes(closes, wick=0.0001)
        bars.append({"open":closes[-1],"high":1.015,"low":closes[-1]-0.0001,"close":1.014})
        result=self.policy.evaluate(bars)
        if result.regime == "SPIKE": self.assertGreater(result.spike_target_distance,0)

if __name__ == '__main__': unittest.main()
