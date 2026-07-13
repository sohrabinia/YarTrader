from abc import ABC, abstractmethod
from typing import List
from src.Learning.Models.models import LearningFeedback, ImprovementSuggestion

class ILearningEngine(ABC):
    """Interface defining operations for processing past feedback loops to suggest improvements."""
    @abstractmethod
    def process_feedback(self, feedback: LearningFeedback) -> None:
        """Stores or records feedback packets."""
        pass

    @abstractmethod
    def generate_suggestions(self) -> List[ImprovementSuggestion]:
        """Runs mathematical optimization parameters to generate suggestions."""
        pass
