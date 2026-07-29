from abc import ABC, abstractmethod
from typing import Optional

class BaseLLMClient(ABC):
    """
    Abstract base class for all LLM client implementations.
    """
    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Generates text using the provider's API.
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Checks if the LLM provider service is available/connected.
        """
        pass
