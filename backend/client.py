import os
import requests
from typing import Dict, Any, List, Optional

class PlantDoctorAPIClient:
    """
    API client for communicating with the FastAPI backend endpoints.
    """
    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")

    def get_health(self) -> Dict[str, Any]:
        """Queries status of backend modules."""
        url = f"{self.base_url}/health"
        try:
            resp = requests.get(url, timeout=5.0)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            return {"status": "offline", "error": str(e), "faiss_index_ready": False, "ollama_ready": False}
        return {"status": "offline", "faiss_index_ready": False, "ollama_ready": False}

    def chat_query(self, query: str, session_id: str, language: str) -> Dict[str, Any]:
        """Submits a text query to the RAG backend."""
        url = f"{self.base_url}/chat"
        payload = {
            "query": query,
            "session_id": session_id,
            "language": language
        }
        resp = requests.post(url, json=payload, timeout=90.0)
        resp.raise_for_status()
        return resp.json()

    def voice_query(self, audio_bytes: bytes, session_id: str, language: str) -> Dict[str, Any]:
        """Submits a WAV recording file to the STT+RAG backend."""
        url = f"{self.base_url}/voice"
        files = {"file": ("query.wav", audio_bytes, "audio/wav")}
        data = {
            "session_id": session_id,
            "language": language
        }
        resp = requests.post(url, files=files, data=data, timeout=120.0)
        resp.raise_for_status()
        return resp.json()

    def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Retrieves conversation history memory window for a specific session."""
        url = f"{self.base_url}/history"
        try:
            resp = requests.get(url, params={"session_id": session_id}, timeout=5.0)
            if resp.status_code == 200:
                return resp.json().get("history", [])
        except Exception:
            return []
        return []

    def clear_history(self, session_id: str) -> bool:
        """Deletes conversation memory for a session."""
        url = f"{self.base_url}/history"
        try:
            resp = requests.delete(url, params={"session_id": session_id}, timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    def rebuild_index(self) -> bool:
        """Triggers a full rebuild of the FAISS vector index."""
        url = f"{self.base_url}/embed"
        try:
            resp = requests.post(url, timeout=300.0)
            return resp.status_code == 200
        except Exception:
            return False

    def upload_document(self, file_name: str, file_bytes: bytes, file_type: str) -> Dict[str, Any]:
        """Uploads a manual document to parse and index."""
        url = f"{self.base_url}/upload"
        files = {"file": (file_name, file_bytes, file_type)}
        resp = requests.post(url, files=files, timeout=300.0)
        resp.raise_for_status()
        return resp.json()

    def translate_text(self, text: str, target_lang: str, source_lang: str = "en") -> Dict[str, Any]:
        """Translates text and returns translated answer and TTS audio URL."""
        url = f"{self.base_url}/translate"
        payload = {
            "text": text,
            "source_lang": source_lang,
            "target_lang": target_lang
        }
        resp = requests.post(url, json=payload, timeout=60.0)
        resp.raise_for_status()
        return resp.json()
