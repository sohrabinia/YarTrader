"""Retired legacy portfolio-scoring engine.

YarTrader now has one decision strategy: hierarchical Base behavior and Base
re-entry reaction. This module remains only to fail clearly for old imports.
"""


class AutonomousDecisionEngine:
    def __init__(self, *args, **kwargs):
        raise RuntimeError(
            "Legacy portfolio-scoring decisions are disabled. Use "
            "src.Decision.Intelligence.engine.DecisionEngine for Base-only decisions."
        )
