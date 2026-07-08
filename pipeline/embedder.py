import os
import sqlite3
import json
import numpy as np
from typing import List
from langchain.embeddings.base import Embeddings
from sentence_transformers import SentenceTransformer
from utils.config import config
from utils.logger import get_logger
from utils.helpers import get_text_hash

logger = get_logger("embedder")

class CachedEmbeddings(Embeddings):
    """
    Custom LangChain Embeddings class that wraps SentenceTransformer 
    and caches vector embeddings in a local SQLite database to prevent redundant CPU/GPU compute.
    """
    def __init__(self, model_name: str = None, device: str = None):
        self.model_name = model_name or config.get("embedding.model_name", "BAAI/bge-small-en-v1.5")
        self.device = device or config.get("embedding.device", "cpu")
        self.models_dir = config.get_absolute_path("paths.models_dir")
        self.cache_dir = config.get_absolute_path("paths.embedding_cache_dir")
        
        # Ensure directories exist
        os.makedirs(self.cache_dir, exist_ok=True)
        embedding_models_dir = os.path.join(self.models_dir, "embedding_models")
        os.makedirs(embedding_models_dir, exist_ok=True)
        
        # Connect to SQLite cache
        self.db_path = os.path.join(self.cache_dir, "embeddings_cache.db")
        self._init_db()
        
        # Load SentenceTransformer model locally
        logger.info(f"Loading SentenceTransformer: {self.model_name} on device {self.device}")
        self.model = SentenceTransformer(
            self.model_name,
            cache_folder=embedding_models_dir,
            device=self.device
        )
        logger.info("SentenceTransformer model loaded successfully.")

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    text_hash TEXT PRIMARY KEY,
                    embedding BLOB,
                    text_content TEXT,
                    model_name TEXT
                )
            """)
            conn.commit()

    def _get_cached_embedding(self, text_hash: str) -> List[float]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT embedding FROM embeddings WHERE text_hash = ? AND model_name = ?", 
                    (text_hash, self.model_name)
                )
                row = cursor.fetchone()
                if row:
                    # Deserialize BLOB back to list of floats
                    arr = np.frombuffer(row[0], dtype=np.float32)
                    return arr.tolist()
        except Exception as e:
            logger.error(f"Error reading embedding cache: {e}")
        return []

    def _save_cached_embedding(self, text_hash: str, embedding: List[float], text_content: str):
        try:
            arr = np.array(embedding, dtype=np.float32)
            blob = arr.tobytes()
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO embeddings (text_hash, embedding, text_content, model_name) VALUES (?, ?, ?, ?)",
                    (text_hash, blob, text_content, self.model_name)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Error writing to embedding cache: {e}")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed list of documents, utilizing cache for already computed items."""
        embeddings = [[] for _ in texts]
        to_compute_indices = []
        to_compute_texts = []
        
        # Check cache
        for idx, text in enumerate(texts):
            text_hash = get_text_hash(text)
            cached = self._get_cached_embedding(text_hash)
            if cached:
                embeddings[idx] = cached
            else:
                to_compute_indices.append(idx)
                to_compute_texts.append(text)
                
        # Compute missing
        if to_compute_texts:
            logger.info(f"Computing embeddings for {len(to_compute_texts)} items...")
            computed_vectors = self.model.encode(
                to_compute_texts, 
                show_progress_bar=False,
                normalize_embeddings=True
            )
            
            # Save to cache and populate return list
            for sub_idx, idx in enumerate(to_compute_indices):
                vec = computed_vectors[sub_idx].tolist()
                embeddings[idx] = vec
                text_hash = get_text_hash(to_compute_texts[sub_idx])
                self._save_cached_embedding(text_hash, vec, to_compute_texts[sub_idx])
                
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        """Embed single query string."""
        text_hash = get_text_hash(text)
        cached = self._get_cached_embedding(text_hash)
        if cached:
            return cached
            
        vector = self.model.encode(text, normalize_embeddings=True).tolist()
        self._save_cached_embedding(text_hash, vector, text)
        return vector
