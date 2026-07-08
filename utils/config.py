import os
import yaml
from typing import Any, Dict
from dotenv import load_dotenv

# Load env variables
load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG_PATH = os.path.join(BASE_DIR, "config", "config.yaml")
DEFAULT_PROMPTS_PATH = os.path.join(BASE_DIR, "config", "prompts.yaml")

class AppConfig:
    def __init__(self, config_path: str = DEFAULT_CONFIG_PATH):
        self.base_dir = BASE_DIR
        self.config_path = config_path
        self.config_data = self._load_yaml(config_path)
        self._apply_env_overrides()

    def _load_yaml(self, path: str) -> Dict[str, Any]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Config file not found at: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _apply_env_overrides(self):
        # Override settings using environment variables if defined
        if os.getenv("OLLAMA_BASE_URL"):
            self.config_data.setdefault("llm", {})["base_url"] = os.getenv("OLLAMA_BASE_URL")
        if os.getenv("LLM_MODEL"):
            self.config_data.setdefault("llm", {})["model"] = os.getenv("LLM_MODEL")
        if os.getenv("EMBEDDING_MODEL"):
            self.config_data.setdefault("embedding", {})["model_name"] = os.getenv("EMBEDDING_MODEL")
        if os.getenv("RERANKER_MODEL"):
            self.config_data.setdefault("reranker", {})["model_name"] = os.getenv("RERANKER_MODEL")
        if os.getenv("DEVICE"):
            self.config_data.setdefault("embedding", {})["device"] = os.getenv("DEVICE")
            self.config_data.setdefault("reranker", {})["device"] = os.getenv("DEVICE")

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation (e.g. 'llm.model')
        """
        parts = key_path.split(".")
        val = self.config_data
        for p in parts:
            if isinstance(val, dict) and p in val:
                val = val[p]
            else:
                return default
        return val

    def get_prompt(self, name: str) -> str:
        """Get prompt template by name mapping key names."""
        name_map = {
            "system_prompt": "prompt.system",
            "context_template": "prompt.context",
            "user_prompt": "prompt.user"
        }
        mapped_key = name_map.get(name)
        if mapped_key:
            return self.get(mapped_key, "")
        return ""

    def get_absolute_path(self, key_path: str) -> str:
        """
        Resolves config paths to absolute path strings.
        """
        rel_path = self.get(key_path)
        if not rel_path:
            raise ValueError(f"Path config for key '{key_path}' is not defined.")
        # If absolute already, return it
        if os.path.isabs(rel_path):
            return rel_path
        return os.path.normpath(os.path.join(self.base_dir, rel_path))

# Global configuration instance
config = AppConfig()
