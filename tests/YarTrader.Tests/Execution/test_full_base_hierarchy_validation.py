import unittest

from src.Decision.Intelligence.base_reaction_decision_engine import BaseReactionDecisionEngine


class TestFullBaseHierarchyValidation(unittest.TestCase):
    def setUp(self):
        self.engine = BaseReactionDecisionEngine()
        self.parent = {"event_id": "h1", "timeframe": "H1", "exit_direction": 1, "confirmation_time": 100}
        self.child = {"event_id": "m5", "timeframe": "M5", "exit_direction": 1, "confirmation_time": 200}
        self.micro = {"event_id": "m1", "timeframe": "M1", "exit_direction": 1, "confirmation_time": 300}
        self.reaction = {"base_id": "m5", "reaction_number": 1, "penetration_fraction": 0.2, "entry_side": "FROM_ABOVE"}
        self.chain = [
            {"timeframe": "H1", "event_id": "h1", "confirmation_time": 100},
            {"timeframe": "M30", "event_id": "m30", "confirmation_time": 150},
            {"timeframe": "M5", "event_id": "m5", "confirmation_time": 200},
            {"timeframe": "M1", "event_id": "m1", "confirmation_time": 300},
        ]
        self.setup = {"timeframe": "M5", "base_type": "RBR", "parent_relation": "NESTED",
                      "hierarchy_chain": self.chain, "hierarchy_complete_to_m1": True}

    def evaluate(self):
        return self.engine.evaluate(setup=self.setup, quote={"bid": 101.0, "ask": 101.1},
                                    now=300, parent=self.parent, child=self.child,
                                    micro=self.micro, reaction=self.reaction)

    def test_complete_mother_to_m1_chain_passes_structural_validation(self):
        result = self.evaluate()
        self.assertNotIn("Full confirmed Base hierarchy from mother through M1 is incomplete.", result["reason"])

    def test_missing_m1_or_incomplete_flag_fails_closed(self):
        self.setup["hierarchy_complete_to_m1"] = False
        result = self.evaluate()
        self.assertIn("hierarchy from mother through M1 is incomplete", result["reason"])

    def test_out_of_order_timeframes_fail_closed(self):
        self.setup["hierarchy_chain"] = [self.chain[0], self.chain[2], self.chain[1], self.chain[3]]
        result = self.evaluate()
        self.assertIn("ordered from mother timeframe down to M1", result["reason"])


if __name__ == "__main__":
    unittest.main()
