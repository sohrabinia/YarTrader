import os
import ast
import unittest


class TestDataProvidersSecurityCompliance(unittest.TestCase):
    """
    Automated security scan proving that the newly implemented Data Providers (MT5, Economic, News)
    maintain absolute zero dependency on Broker execution, Orders, Trades, or Position Management. (5 tests)
    """

    def setUp(self) -> None:
        self.providers_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../src/Data/Providers"))
        self.forbidden_namespaces = {"brokercommand", "order", "execute", "trade", "positionmanagement"}

    def test_security_1_zero_forbidden_imports(self) -> None:
        """Verify no direct imports of forbidden trading namespaces exist in AST."""
        for root, dirs, files in os.walk(self.providers_dir):
            if "__pycache__" in root:
                continue

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
        forbidden_raw_tokens = {"place_order", "open_position", "execute_trade", "buy_signal", "sell_signal", "brokercommand"}

        for root, dirs, files in os.walk(self.providers_dir):
            if "__pycache__" in root:
                continue

            for file in files:
                filepath = os.path.join(root, file)
                with open(filepath, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                for line_idx, line in enumerate(lines):
                    clean_line = line.split("#")[0].strip() # ignore comments
                    for token in forbidden_raw_tokens:
                        if token in clean_line.lower():
                            self.fail(
                                f"Leakage Violation in {filepath}:{line_idx + 1}: Raw execution token '{token}' found."
                            )

    def test_security_3_no_trading_state_variables(self) -> None:
        """Verify there are no account, leverage, or trade variables present."""
        forbidden_vars = {"account_balance", "leverage_factor", "portfolio_weights_active"}

        for root, dirs, files in os.walk(self.providers_dir):
            if "__pycache__" in root:
                continue

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
        for root, dirs, files in os.walk(self.providers_dir):
            if "__pycache__" in root:
                continue

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
        for root, dirs, files in os.walk(self.providers_dir):
            if "__pycache__" in root:
                continue

            for file in files:
                if not file.endswith(".py"):
                    continue

                filepath = os.path.join(root, file)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()

                self.assertNotIn("broker_adapter", content.lower())
                self.assertNotIn("broker_api", content.lower())
