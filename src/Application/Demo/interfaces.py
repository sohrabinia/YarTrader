from abc import ABC, abstractmethod
from typing import Any
from src.Application.Demo.models import DemoScenario, DemoExecutionResult, DemoReport


class IDemoScenarioRunner(ABC):
    """Interface for orchestrating and running continuous intelligence demo scenarios."""

    @abstractmethod
    def run_scenario(self, scenario: DemoScenario) -> DemoExecutionResult:
        """Executes a complete demo scenario through the RG_V3_AI intelligence layers."""
        pass


class IDemoReportGenerator(ABC):
    """Interface for generating formatted human-readable reports of demo scenarios."""

    @abstractmethod
    def generate_report(self, result: DemoExecutionResult) -> DemoReport:
        """Translates a DemoExecutionResult into a comprehensive trace-complete DemoReport."""
        pass
