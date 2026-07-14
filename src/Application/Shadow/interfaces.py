from abc import ABC, abstractmethod
from typing import Any
from src.Application.Shadow.models import ShadowSession, ShadowReport


class IShadowModeEngine(ABC):
    """Interface for running, managing, and auditing read-only Shadow Mode instances."""

    @abstractmethod
    def start_session(self, symbol: str, timeframe: str) -> ShadowSession:
        """Starts a live-tracking shadow session for the specified instrument."""
        pass

    @abstractmethod
    def execute_tick(self, session_id: str) -> ShadowReport:
        """Ingests live market ticks, triggers the pipeline, and aggregates passive metrics."""
        pass

    @abstractmethod
    def stop_session(self, session_id: str) -> ShadowSession:
        """Gracefully halts the live-tracking shadow session."""
        pass
