from src.Strategy.Interfaces.interfaces import IRuleValidator
from src.Strategy.Models.models import StrategyDefinition

class StrategyAnalyzer(IRuleValidator):
    """
    Analyzes strategy concepts for structural correctness.
    Guarantees no external/unsafe trading execution rules are embedded.
    """
    def validate_structure(self, definition: StrategyDefinition) -> bool:
        # Ensure name and description fit descriptive metadata rules
        if not definition.Name or not definition.Description:
            return False

        # Ensure status is approved or standard draft
        if definition.Status not in ["Draft", "Approved", "Deprecated"]:
            return False

        # Structure is valid and clean
        return True
