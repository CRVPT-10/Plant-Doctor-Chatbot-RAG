import requests
from typing import Optional
from backend.llm.base import BaseLLMClient
from utils.config import config
from utils.logger import get_logger

logger = get_logger("ollama_llm")

class OllamaLLMClient(BaseLLMClient):
    """
    Client wrapper for interacting with local Ollama service.
    """
    def __init__(self):
        self.base_url = config.get("llm.base_url", "http://localhost:11434").rstrip("/")
        self.model_name = config.get("llm.model", "qwen2.5:7b")
        self.temperature = config.get("llm.temperature", 0.2)
        self.timeout = config.get("llm.timeout", 60.0)
        self.top_p = config.get("llm.top_p", 0.9)
        self.repeat_penalty = config.get("llm.repeat_penalty", 1.1)
        self.num_ctx = config.get("llm.num_ctx", 8192)

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Sends a generation request to Ollama's /api/chat endpoint.
        """
        url = f"{self.base_url}/api/chat"
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "top_p": self.top_p,
                "repeat_penalty": self.repeat_penalty,
                "num_ctx": self.num_ctx
            }
        }
        
        logger.info(f"Sending request to Ollama model '{self.model_name}' at {url}")
        
        try:
            response = requests.post(
                url, 
                json=payload, 
                timeout=self.timeout
            )
            response.raise_for_status()
            response_json = response.json()
            answer = response_json.get("message", {}).get("content", "").strip()
            return answer
            
        except requests.exceptions.ConnectionError:
            error_msg = f"Could not connect to Ollama at {self.base_url}. Is Ollama running? Run 'ollama serve' in your terminal."
            logger.error(error_msg)
            raise ConnectionError(error_msg)
        except requests.exceptions.HTTPError as e:
            error_msg = f"Ollama HTTP error: {e}. Ensure model '{self.model_name}' is downloaded. Run 'ollama pull {self.model_name}'."
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error communicating with Ollama: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def is_available(self) -> bool:
        """Checks if the Ollama service is running and has the model loaded."""
        try:
            tags_url = f"{self.base_url}/api/tags"
            response = requests.get(tags_url, timeout=1.5)
            if response.status_code == 200:
                models = [m.get("name") for m in response.json().get("models", [])]
                available = any(self.model_name in m for m in models)
                if not available:
                    logger.warning(f"Ollama is running, but model '{self.model_name}' is not downloaded. Available: {models}")
                return True
        except Exception:
            pass
        return False
