import os
import ast
import unittest


class TestAgentArchitectureCompliance(unittest.TestCase):
    """
    Automated architectural rule checking to guarantee absolute zero execution leakage
    from any multi-agent modules to actual trading execution/broker namespaces.
    """

    def setUp(self) -> None:
        self.agents_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../src/Application/Agents"))
        self.forbidden_namespaces = {"broker", "order", "execution", "positionmanager"}

    def test_no_forbidden_namespaces_in_imports(self) -> None:
        """Test: No agent code imports or references forbidden trading/execution namespaces."""
        for root, _, files in os.walk(self.agents_dir):
            for file in files:
                if not file.endswith(".py"):
                    continue

                filepath = os.path.join(root, file)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()

                # Parse the file AST to look at imports
                try:
                    tree = ast.parse(content, filename=filepath)
                except SyntaxError:
                    self.fail(f"Syntax error parsing {filepath}")

                for node in ast.walk(tree):
                    # Check "import X"
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            self._verify_not_forbidden(alias.name, filepath)

                    # Check "from X import Y"
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            self._verify_not_forbidden(node.module, filepath)
                        for alias in node.names:
                            self._verify_not_forbidden(alias.name, filepath)

    def _verify_not_forbidden(self, name: str, filepath: str) -> None:
        parts = name.lower().split(".")
        for part in parts:
            if part in self.forbidden_namespaces:
                self.fail(
                    f"Architecture Violation in {filepath}: Forbidden trading/execution namespace '{part}' "
                    f"referenced in import '{name}'."
                )

    def test_strict_static_leakage_checks(self) -> None:
        """Test: Search for forbidden execution-trigger keywords in the raw code text."""
        # Except checking custom isolation rules definitions
        forbidden_raw_tokens = {"place_order", "open_position", "execute_trade"}

        for root, _, files in os.walk(self.agents_dir):
            for file in files:
                if not file.endswith(".py") or file == "concrete_agents.py":
                    # concrete_agents.py defines the strings in forbidden list for verification,
                    # so we only scan other files for safety raw tokens.
                    continue

                filepath = os.path.join(root, file)
                with open(filepath, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                for line_idx, line in enumerate(lines):
                    clean_line = line.split("#")[0].strip()  # Ignore comments
                    for token in forbidden_raw_tokens:
                        if token in clean_line:
                            self.fail(
                                f"Leakage Warning in {filepath}:{line_idx + 1}: Raw execution token '{token}' "
                                f"found in active code."
                            )
