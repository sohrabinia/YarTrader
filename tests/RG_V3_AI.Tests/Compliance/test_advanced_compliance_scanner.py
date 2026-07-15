import os
import unittest
import tempfile
from src.Application.Audit.compliance_scanner import ComplianceScanner


class TestAdvancedComplianceScanner(unittest.TestCase):
    """
    Unit tests for the AST compliance_scanner verifying correct distinguishing
    between allowed defensive definitions and actual forbidden trading execution/definitions.
    """

    def setUp(self) -> None:
        self.scanner = ComplianceScanner()

    def test_allowed_defensive_assignment_and_lists(self) -> None:
        """Verify that string literals, definitions, and list configurations are completely allowed."""
        safe_code = """
# Safe compliance definitions
forbidden_actions = [
    "place_order",
    "create_order",
    "send_transaction",
    "execute_trade",
    "buy_signal",
    "sell_signal"
]

def check_safety(action: str) -> bool:
    return action in forbidden_actions
"""
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False, encoding="utf-8") as temp:
            temp.write(safe_code)
            temp_path = temp.name

        try:
            violations = self.scanner.scan_file(temp_path)
            self.assertEqual(len(violations), 0, f"Expected no violations, found: {violations}")
        finally:
            os.remove(temp_path)

    def test_allowed_directory_paths_skip(self) -> None:
        """Verify files in allowed audit, validation, and configuration directories skip check."""
        for path in [
            "src/Application/Audit/some_file.py",
            "src/Application/Validation/another_file.py",
            "src/Infrastructure/Configuration/settings.py"
        ]:
            self.assertTrue(self.scanner.is_path_allowed(path))

    def test_rejected_function_definitions(self) -> None:
        """Verify defining a function with a forbidden keyword is correctly rejected."""
        bad_code = """
def place_order():
    pass
"""
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False, encoding="utf-8") as temp:
            temp.write(bad_code)
            temp_path = temp.name

        try:
            violations = self.scanner.scan_file(temp_path)
            self.assertEqual(len(violations), 1)
            self.assertEqual(violations[0][1], "Function Definition Violation")
            self.assertIn("Defines forbidden function 'place_order'", violations[0][2])
        finally:
            os.remove(temp_path)

    def test_rejected_active_function_calls(self) -> None:
        """Verify calling a function with a forbidden keyword is correctly rejected."""
        bad_code = """
def run_app():
    send_transaction()
"""
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False, encoding="utf-8") as temp:
            temp.write(bad_code)
            temp_path = temp.name

        try:
            violations = self.scanner.scan_file(temp_path)
            self.assertEqual(len(violations), 1)
            self.assertEqual(violations[0][1], "Active Call Violation")
            self.assertIn("Executes forbidden call to 'send_transaction'", violations[0][2])
        finally:
            os.remove(temp_path)

    def test_rejected_attribute_calls(self) -> None:
        """Verify calling an attribute method with a forbidden keyword is correctly rejected."""
        bad_code = """
def run_app(broker):
    broker.create_order()
"""
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False, encoding="utf-8") as temp:
            temp.write(bad_code)
            temp_path = temp.name

        try:
            violations = self.scanner.scan_file(temp_path)
            self.assertEqual(len(violations), 1)
            self.assertEqual(violations[0][1], "Active Call Violation")
            self.assertIn("Executes forbidden call to 'create_order'", violations[0][2])
        finally:
            os.remove(temp_path)
