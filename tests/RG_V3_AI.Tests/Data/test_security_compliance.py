import os
import ast
import unittest


class TestDataLayerSecurityCompliance(unittest.TestCase):
    """
    Automated security scan proving that the newly implemented Data Connector Layer
    maintains absolute zero dependency on Broker, Order, Execution, or Position namespaces. (5 tests)
    """

    def setUp(self) -> None:
        self.data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../src/Data"))
        self.forbidden_namespaces = {"broker", "order", "execution", "positionmanager"}

    def test_security_1_zero_forbidden_imports(self) -> None:
        """Verify no direct imports of forbidden trading namespaces exist in AST."""
        for root, _, files in os.walk(self.data_dir):
            for file in files:
                if not file.endswith(".py"):
                    continue

                filepath = os.path.join(root, file)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()

                try:
                    tree = ast.parse(content, filename=filepath)
                except SyntaxError:
                    self.fail(f"Syntax error parsing {filepath}")

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            self._verify_not_forbidden(alias.name, filepath)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            self._verify_not_forbidden(node.module, filepath)
                        for alias in node.names:
                            self._verify_not_forbidden(alias.name, filepath)

    def _verify_not_forbidden(self, name: str, filepath: str) -> None:
        parts = name.lower().split(".")
        for part in parts:
            if part in self.forbidden_namespaces:
                self.fail(f"Security Violation in {filepath}: Forbidden trading/execution namespace '{part}' imported.")

    def test_security_2_zero_raw_execution_keywords(self) -> None:
        """Verify no active execution commands are in the file."""
        forbidden_raw_tokens = {"place_order", "open_position", "execute_trade", "buy_signal", "sell_signal"}

        for root, _, files in os.walk(self.data_dir):
            for file in files:
                if not file.endswith(".py") or "validation.py" in file:
                    # skip validator/compliance check string collections
                    continue

                filepath = os.path.join(root, file)
                with open(filepath, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                for line_idx, line in enumerate(lines):
                    clean_line = line.split("#")[0].strip() # ignore comments
                    for token in forbidden_raw_tokens:
                        if token in clean_line:
                            self.fail(
                                f"Leakage Violation in {filepath}:{line_idx + 1}: Raw execution token '{token}' found."
                            )

    def test_security_3_no_trading_state_variables(self) -> None:
        """Verify there are no account, leverage, or trade variables present."""
        forbidden_vars = {"account_balance", "leverage_factor", "portfolio_weights_active"}

        for root, _, files in os.walk(self.data_dir):
            for file in files:
                if not file.endswith(".py"):
                    continue

                filepath = os.path.join(root, file)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()

                for var in forbidden_vars:
                    self.assertNotIn(var, content.lower(), f"Leakage Violation in {filepath}: Variable '{var}' found.")

    def test_security_4_strictly_passive_methods(self) -> None:
        """Verify there are no active write/request socket connections."""
        for root, _, files in os.walk(self.data_dir):
            for file in files:
                if not file.endswith(".py"):
                    continue

                filepath = os.path.join(root, file)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()

                self.assertNotIn("socket.send", content.lower())
                self.assertNotIn("socket.connect", content.lower())

    def test_security_5_no_broker_references_in_class_fields(self) -> None:
        """Verify there are no broker-specific attributes declared."""
        for root, _, files in os.walk(self.data_dir):
            for file in files:
                if not file.endswith(".py"):
                    continue

                filepath = os.path.join(root, file)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()

                self.assertNotIn("broker_adapter", content.lower())
                self.assertNotIn("broker_api", content.lower())
