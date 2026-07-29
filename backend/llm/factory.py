from backend.llm.base import BaseLLMClient
from backend.llm.ollama_client import OllamaLLMClient
from backend.llm.groq_client import GroqLLMClient
from utils.config import config
from utils.logger import get_logger

logger = get_logger("llm_factory")

class LLMFactory:
    """
    Factory class to dynamically instantiate the correct LLM provider client.
    """
    @staticmethod
    def get_client() -> BaseLLMClient:
        provider = config.get("llm.provider", "ollama").lower()
        logger.info(f"LLMFactory instantiating client for provider: '{provider}'")
        
        if provider == "groq":
            return GroqLLMClient()
        elif provider == "ollama":
            return OllamaLLMClient()
        else:
            logger.warning(f"Unknown LLM provider '{provider}', falling back to OllamaLLMClient.")
            return OllamaLLMClient()
