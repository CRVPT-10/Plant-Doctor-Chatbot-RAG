import os
import json
from typing import List, Tuple, Dict
from utils.config import config
from utils.logger import get_logger

logger = get_logger("memory")

class ConversationMemory:
    """
    Manages session-based conversation history using a sliding memory window.
    """
    def __init__(self, window_size: int = None):
        self.window_size = window_size or config.get("memory.window_size", 5)
        # Store structured as session_id -> List[Tuple[query, response]]
        self._sessions: Dict[str, List[Tuple[str, str]]] = {}

    def get_history(self, session_id: str) -> List[Tuple[str, str]]:
        """Retrieves history for a session up to the sliding window limit."""
        if session_id not in self._sessions:
            return []
        # Return last N turns
        return self._sessions[session_id][-self.window_size:]

    def get_all_history(self, session_id: str) -> List[Tuple[str, str]]:
        """Retrieves entire history for a session."""
        return self._sessions.get(session_id, [])

    def add_interaction(self, session_id: str, query: str, response: str):
        """Adds a Q&A interaction to session history."""
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        self._sessions[session_id].append((query, response))
        logger.info(f"Added interaction to session {session_id}. Total history turns: {len(self._sessions[session_id])}")

    def clear_session(self, session_id: str):
        """Clears memory for a specific session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"Cleared session history for {session_id}")

    def clear_all(self):
        """Clears all session memory."""
        self._sessions.clear()
        logger.info("Cleared all conversation sessions memory.")
