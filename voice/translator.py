import os
import sqlite3
from typing import Dict, Any, Optional, Tuple
from deep_translator import GoogleTranslator
from utils.config import config
from utils.logger import get_logger
from utils.helpers import get_text_hash
from pipeline.vector_store import VectorStoreManager

logger = get_logger("translator")

class LanguageTranslator:
    """
    Handles translation between English and Hindi, Telugu, and Tamil.
    Integrates translation caching and adaptive routing based on local database contents.
    """
    def __init__(self, vector_store_manager: VectorStoreManager = None):
        self.vs_manager = vector_store_manager or VectorStoreManager()
        self.enabled = config.get("voice.translation.enabled", True)
        
        self.cache_dir = config.get_absolute_path("paths.translation_cache_dir")
        os.makedirs(self.cache_dir, exist_ok=True)
        self.cache_db = os.path.join(self.cache_dir, "translations_cache.db")
        self._init_cache_db()

    def _init_cache_db(self):
        with sqlite3.connect(self.cache_db) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS translations (
                    text_hash TEXT PRIMARY KEY,
                    source_text TEXT,
                    source_lang TEXT,
                    target_lang TEXT,
                    translated_text TEXT
                )
            """)
            conn.commit()

    def _get_cached_translation(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        text_hash = get_text_hash(f"{source_lang}->{target_lang}:{text}")
        try:
            with sqlite3.connect(self.cache_db) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT translated_text FROM translations WHERE text_hash = ?", 
                    (text_hash,)
                )
                row = cursor.fetchone()
                if row:
                    return row[0]
        except Exception as e:
            logger.error(f"Error reading translation cache: {e}")
        return None

    def _save_cached_translation(self, text: str, source_lang: str, target_lang: str, translated: str):
        text_hash = get_text_hash(f"{source_lang}->{target_lang}:{text}")
        try:
            with sqlite3.connect(self.cache_db) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO translations (text_hash, source_text, source_lang, target_lang, translated_text) VALUES (?, ?, ?, ?, ?)",
                    (text_hash, text, source_lang, target_lang, translated)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Error saving to translation cache: {e}")

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Translates text from source_lang to target_lang.
        Checks SQLite cache first.
        """
        if not text or not self.enabled or source_lang == target_lang:
            return text
            
        # Check cache
        cached = self._get_cached_translation(text, source_lang, target_lang)
        if cached:
            logger.info(f"Found cached translation for: '{text[:30]}...' ({source_lang}->{target_lang})")
            return cached
            
        logger.info(f"Translating text: '{text[:30]}...' from '{source_lang}' to '{target_lang}'")
        try:
            # Map standard short codes to deep_translator supported codes if necessary
            # GoogleTranslator supports 'hi', 'te', 'ta', 'en' natively
            translator = GoogleTranslator(source=source_lang, target=target_lang)
            translated = translator.translate(text)
            
            # Cache the result
            self._save_cached_translation(text, source_lang, target_lang, translated)
            return translated
        except Exception as e:
            logger.error(f"Translation failed: {e}. Returning original text.")
            return text

    def route_query(self, query: str, detected_lang: str) -> Dict[str, Any]:
        """
        Implements the adaptive multilingual query routing workflow:
        1. If language is English -> Retrieve Directly (no translation)
        2. Else if native documents exist in Vector DB -> Retrieve Native documents directly
        3. Else -> Translate query to English -> Retrieve English -> Generate English response.
        """
        detected_lang = detected_lang.lower()
        if detected_lang == "en":
            logger.info("Adaptive Routing: Query is English. Direct retrieval.")
            return {
                "query": query,
                "retrieve_lang": "en",
                "needs_translation": False,
                "original_lang": "en"
            }
            
        # Check if native documents exist in vector store
        indexed_docs = self.vs_manager.get_all_indexed_documents()
        native_docs_exist = any(doc.get("language") == detected_lang for doc in indexed_docs)
        
        if native_docs_exist:
            logger.info(f"Adaptive Routing: Native documents found in '{detected_lang}'. Native retrieval.")
            return {
                "query": query,
                "retrieve_lang": detected_lang,
                "needs_translation": False,
                "original_lang": detected_lang
            }
        else:
            logger.info(f"Adaptive Routing: No native documents found for '{detected_lang}'. Falling back to English translation workflow.")
            translated_query = self.translate(query, source_lang=detected_lang, target_lang="en")
            return {
                "query": translated_query,
                "retrieve_lang": "en",
                "needs_translation": True,
                "original_lang": detected_lang
            }
