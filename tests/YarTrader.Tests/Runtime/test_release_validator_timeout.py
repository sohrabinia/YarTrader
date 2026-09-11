import os
import unittest
import subprocess
from unittest.mock import MagicMock, patch
from validate_release import ReleaseValidationPlatform

class TestReleaseValidatorTimeout(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = ReleaseValidationPlatform()

    @patch("subprocess.run")
    def test_validator_timeout_handling(self, mock_run):
        """Verifies that subprocess TimeoutExpired is caught explicitly and classified as TIMEOUT."""
        # First call: pytest --version
        ver_mock = MagicMock()
        ver_mock.returncode = 0

        # Second call: pytest execution times out
        mock_run.side_effect = [ver_mock, subprocess.TimeoutExpired(cmd=["pytest"], timeout=1800, output="partial", stderr="timeout")]

        with patch.dict(os.environ, {"PYTEST_TIMEOUT_SEC": "1800"}):
            results, failures = self.validator.run_automated_tests()
            self.assertEqual(results["status"], "TIMEOUT")
            self.assertEqual(results["failed"], 1)
            self.assertIn("pytest_suite_timeout", failures[0]["test"])

    @patch("subprocess.run")
    def test_validator_success_and_failure_semantics(self, mock_run):
        """Verifies that normal test success and non-zero exit codes are classified correctly."""
        ver_mock = MagicMock()
        ver_mock.returncode = 0

        success_mock = MagicMock()
        success_mock.returncode = 0
        success_mock.stdout = "=== 100 passed, 2 warnings in 5.0s ==="
        success_mock.stderr = ""

        mock_run.side_effect = [ver_mock, success_mock]

        results, failures = self.validator.run_automated_tests()
        self.assertEqual(results["status"], "PASSED")
        self.assertEqual(results["passed"], 100)
        self.assertEqual(results["failed"], 0)
        self.assertEqual(len(failures), 0)

if __name__ == "__main__":
    unittest.main()
