import requests
from typing import Optional
from backend.llm.base import BaseLLMClient
from utils.config import config
from utils.logger import get_logger

logger = get_logger("groq_llm")

# Groq retires models over time; map known-retired ids to current replacements
# so a stale GROQ_MODEL env var doesn't break production with a 404.
RETIRED_MODEL_MAP = {
    "llama-3.3-70b-versatile": "openai/gpt-oss-120b",  # retired 2026-08-16
    "llama-3.1-8b-instant": "openai/gpt-oss-20b",       # retired 2026-08-16
}

class GroqLLMClient(BaseLLMClient):
    """
    Client wrapper for interacting with Groq Cloud Completion API.
    Uses requests directly to avoid extra dependencies.
    """
    def __init__(self):
        self.api_key = config.get("llm.groq_api_key")
        self.model_name = config.get("llm.groq_model", "openai/gpt-oss-120b")
        # Transparently upgrade a retired model id to a current one.
        if self.model_name in RETIRED_MODEL_MAP:
            replacement = RETIRED_MODEL_MAP[self.model_name]
            logger.warning(
                f"Groq model '{self.model_name}' is retired; using '{replacement}' instead. "
                f"Update the GROQ_MODEL environment variable to silence this."
            )
            self.model_name = replacement
        self.temperature = config.get("llm.temperature", 0.2)
        self.timeout = config.get("llm.timeout", 60.0)
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Sends a chat completions request to Groq API.
        """
        if not self.api_key:
            error_msg = "GROQ_API_KEY is not defined in the environment or configuration."
            logger.error(error_msg)
            raise ValueError(error_msg)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature
        }

        logger.info(f"Sending request to Groq API using model '{self.model_name}'")
        
        try:
            response = requests.post(
                self.base_url, 
                json=payload, 
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            response_json = response.json()
            answer = response_json.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            return answer
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"Groq API HTTP error: {e}. Check if model '{self.model_name}' is supported and api key is valid."
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error communicating with Groq API: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def is_available(self) -> bool:
        """Checks if Groq client has been configured with an API key."""
        return bool(self.api_key)
