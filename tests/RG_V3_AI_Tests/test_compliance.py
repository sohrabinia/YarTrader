import os
import unittest

class TestArchitectureCompliance(unittest.TestCase):
    """
    Automated architectural compliance rules validating layer separation and
    ensuring zero leakage from Agents/Intelligence modules into execution/broker/trading.
    """

    def test_unidirectional_dependency_rules(self) -> None:
        """Test that Agent classes contain absolutely no imports of execution or broker namespaces."""
        agent_paths = [
            "src/Decision/Intelligence/Agents/models.py",
            "src/Decision/Intelligence/Agents/agents.py",
            "src/Decision/Intelligence/Agents/services.py"
        ]

        forbidden_imports = [
            "src.Execution",
            "src.Execution.Broker",
            "src.Execution.Orders",
            "src.Execution.Positions"
        ]

        for path in agent_paths:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    for forbidden in forbidden_imports:
                        self.assertNotIn(forbidden, content, f"Compliance Violation: Forbidden import '{forbidden}' found in '{path}'.")

    def test_safety_keyword_leakage_checks(self) -> None:
        """Test that Agent source files contain absolutely no active live trading keywords or execution logic."""
        agent_paths = [
            "src/Decision/Intelligence/Agents/models.py",
            "src/Decision/Intelligence/Agents/agents.py",
            "src/Decision/Intelligence/Agents/services.py"
        ]

        forbidden_keywords = [
            "place_order",
            "execute_trade",
            "buy_signal",
            "sell_signal",
            "broker_connection = active",
            "send_transaction"
        ]

        for path in agent_paths:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    for kw in forbidden_keywords:
                        self.assertNotIn(kw, content, f"Compliance Violation: Forbidden trading keyword '{kw}' found in '{path}'.")
