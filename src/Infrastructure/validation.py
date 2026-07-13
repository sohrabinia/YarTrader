import math
from typing import Any, Dict, List
from src.Infrastructure.exceptions import ValidationException

class ModelValidator:
    """
    Extensible and unified model validation utility.
    Guarantees structural, numerical, and relational constraints across data, research, and strategy models.
    """
    @staticmethod
    def validate_positive(value: float, name: str) -> None:
        """Enforces that a float value is positive (> 0)."""
        if value <= 0 or math.isnan(value):
            raise ValidationException(f"Validation Error: '{name}' must be strictly positive. Value={value}")

    @staticmethod
    def validate_non_negative(value: float, name: str) -> None:
        """Enforces that a float value is non-negative (>= 0)."""
        if value < 0 or math.isnan(value):
            raise ValidationException(f"Validation Error: '{name}' must be non-negative. Value={value}")

    @staticmethod
    def validate_range(value: float, min_val: float, max_val: float, name: str) -> None:
        """Enforces that a float value fits strictly inside a range boundary."""
        if value < min_val or value > max_val or math.isnan(value):
            raise ValidationException(f"Validation Error: '{name}' must fit inside [{min_val}, {max_val}]. Value={value}")

    @staticmethod
    def validate_non_empty_string(value: str, name: str) -> None:
        """Enforces that a string is non-empty and non-blank."""
        if not value or not value.strip():
            raise ValidationException(f"Validation Error: '{name}' cannot be empty or blank.")

    @staticmethod
    def validate_weights_sum(weights: Dict[str, float], limit: float, name: str) -> None:
        """Enforces that the sum of the weight allocations fits inside a leverage threshold."""
        total = sum(weights.values())
        if total > limit or math.isnan(total):
            raise ValidationException(f"Validation Error: Sum of '{name}' ({total}) exceeds leverage limit of {limit}.")
