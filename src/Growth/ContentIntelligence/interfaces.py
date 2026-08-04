from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class ContentIntelligenceInterface(ABC):
    """
    Abstract interface for Content Intelligence generation, decouples core content creation
    from specific LLM providers (Gemini, Claude, OpenAI, or Local Mock).
    """

    @abstractmethod
    def generate_draft(self, payload: Dict[str, Any], language: str = "en") -> Dict[str, Any]:
        """
        Generates structured content draft using incoming payload.
        MUST retain 100% source intelligence traceability metadata.
        """
        pass
