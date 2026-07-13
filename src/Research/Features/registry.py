from typing import Dict, List, Optional, Tuple
from src.Infrastructure.exceptions import ValidationException
from src.Research.Features.interfaces import IFeatureCalculator
from src.Research.Features.models import FeatureDefinition


class FeatureRegistry:
    """Manages feature definitions and associated calculator lookups."""

    def __init__(self) -> None:
        self._definitions: Dict[str, FeatureDefinition] = {}
        self._calculators: Dict[str, IFeatureCalculator] = {}

    def register_feature(
        self,
        definition: FeatureDefinition,
        calculator: IFeatureCalculator
    ) -> None:
        """Registers a feature definition and its corresponding calculator."""
        if not definition.Name or not definition.Name.strip():
            raise ValidationException("Validation Error: Feature name cannot be empty.")

        self._definitions[definition.Name] = definition
        self._calculators[definition.Name] = calculator

    def get_calculator(self, feature_name: str) -> Optional[IFeatureCalculator]:
        """Retrieves the registered calculator for a specific feature."""
        return self._calculators.get(feature_name)

    def get_definition(self, feature_name: str) -> Optional[FeatureDefinition]:
        """Retrieves the definition of a registered feature."""
        return self._definitions.get(feature_name)

    def list_features(self) -> List[FeatureDefinition]:
        """Lists all registered feature definitions."""
        return list(self._definitions.values())

    def get_calculators_by_definition(self) -> List[Tuple[FeatureDefinition, IFeatureCalculator]]:
        """Returns all registered feature definitions paired with their calculators."""
        pairs = []
        for name, definition in self._definitions.items():
            calc = self._calculators.get(name)
            if calc:
                pairs.append((definition, calc))
        return pairs

    def clear(self) -> None:
        """Clears all registered features from the registry."""
        self._definitions.clear()
        self._calculators.clear()
