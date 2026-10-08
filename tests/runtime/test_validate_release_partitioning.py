import os

import pytest

from validate_release import ReleaseValidationPlatform


@pytest.mark.parametrize("raw_index", ["abc", "1.0", "-1", "16", "999999"])
def test_invalid_partition_selector_fails_closed(monkeypatch, raw_index):
    monkeypatch.setenv("VALIDATION_PARTITION_INDEX", raw_index)

    validator = ReleaseValidationPlatform.__new__(ReleaseValidationPlatform)
    validator.python_exec = os.sys.executable
    validator.logs_collected = []
    validator.passed_count = 0
    validator.failed_count = 0
    validator.warning_count = 0

    with pytest.raises(RuntimeError, match="Invalid VALIDATION_PARTITION_INDEX"):
        validator.run_automated_tests()


def test_partition_selector_zero_is_deterministic(monkeypatch):
    monkeypatch.setenv("VALIDATION_PARTITION_INDEX", "0")

    validator = ReleaseValidationPlatform.__new__(ReleaseValidationPlatform)
    validator.python_exec = os.sys.executable
    validator.logs_collected = []
    validator.passed_count = 0
    validator.failed_count = 0
    validator.warning_count = 0

    class Completed:
        returncode = 0
        stdout = "============================= 1 passed in 0.01s =============================="
        stderr = ""

    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return Completed()

    monkeypatch.setattr("validate_release.subprocess.run", fake_run)
    result, failures = validator.run_automated_tests()

    assert result["status"] == "PASSED"
    assert result["passed"] == 1
    assert not failures
    assert len(calls) == 1
    assert calls[0][0:3] == [os.sys.executable, "-m", "pytest"]
    assert calls[0][3] == "tests/YarTrader.Tests/Gate1/"
