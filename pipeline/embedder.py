import os
import sqlite3
import json
import time
import requests
import numpy as np
from typing import List, Optional
from langchain.embeddings.base import Embeddings
from utils.config import config
from utils.logger import get_logger
from utils.helpers import get_text_hash

logger = get_logger("embedder")

class CachedEmbeddings(Embeddings):
    """
    Custom LangChain Embeddings class that wraps SentenceTransformer 
    and caches vector embeddings in a local SQLite database to prevent redundant CPU/GPU compute.
    Supports local offline generation (SentenceTransformer) or cloud API (Groq).
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
        
        # Load embedding model based on LLM provider
        self.provider = config.get("llm.provider", "ollama").lower()
        self.model = None
        self.use_api = (self.provider == "groq")
        
        if self.use_api:
            logger.info("Using Hugging Face Serverless API router for cloud embeddings (no local PyTorch/SentenceTransformer loaded).")
        else:
            # Load SentenceTransformer model locally
            logger.info(f"Loading SentenceTransformer: {self.model_name} on device {self.device}")
            from sentence_transformers import SentenceTransformer
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

    def _embed_via_hf(self, texts: List[str]) -> List[List[float]]:
        model_id = "BAAI/bge-small-en-v1.5"
        
        # We will try both URLs to be robust
        urls = [
            f"https://api-inference.huggingface.co/models/{model_id}",
            f"https://router.huggingface.co/hf-inference/models/{model_id}"
        ]
        
        headers = {}
        hf_token = os.getenv("HF_TOKEN") or os.getenv("HF_API_KEY")
        if hf_token:
            headers["Authorization"] = f"Bearer {hf_token}"
        else:
            raise ValueError("HF_TOKEN (Hugging Face API Token) is required for production cloud embeddings. Please set it in your environment variables.")
            
        payload = {
            "inputs": texts,
            "options": {"wait_for_model": False}  # Don't hold the connection open forever; handle cold start via retries
        }
        
        logger.info(f"Generating embeddings for {len(texts)} texts via Hugging Face Serverless API ({model_id})...")
        
        max_retries = 5
        retry_delay = 3.0
        
        for attempt in range(max_retries):
            # Alternate URLs across retries to bypass any single endpoint routing block
            url = urls[attempt % len(urls)]
            try:
                # Use a tuple for timeout: (connection_timeout, read_timeout)
                # 5.0 seconds to connect, 15.0 seconds to read
                resp = requests.post(url, json=payload, headers=headers, timeout=(5.0, 15.0))
                
                # If model is loading, Hugging Face returns 503
                if resp.status_code == 503:
                    try:
                        info = resp.json()
                        est_time = info.get("estimated_time", 20.0)
                    except Exception:
                        est_time = 20.0
                    logger.warning(f"Hugging Face model '{model_id}' is loading. Estimated time: {est_time}s. Retrying in {retry_delay}s... (Attempt {attempt+1}/{max_retries})")
                    time.sleep(retry_delay)
                    continue
                    
                resp.raise_for_status()
                embeddings = resp.json()
                
                # Ensure return format is List[List[float]]
                if isinstance(embeddings, list) and len(embeddings) > 0:
                    if isinstance(embeddings[0], list):
                        if isinstance(embeddings[0][0], list):
                            # Mean pool sequence dimension
                            pooled = []
                            for item in embeddings:
                                arr = np.mean(np.array(item), axis=0)
                                pooled.append(arr.tolist())
                            return pooled
                        return embeddings
                    elif isinstance(embeddings[0], (int, float)):
                        return [embeddings]
                raise ValueError(f"Unexpected response format from Hugging Face: {type(embeddings)}")
                
            except requests.exceptions.Timeout as te:
                logger.warning(f"Timeout querying Hugging Face API ({url}) on attempt {attempt+1}/{max_retries}: {te}. Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Failed to generate embeddings via Hugging Face after {max_retries} attempts: {e}")
                    raise RuntimeError(f"Hugging Face embedding error: {e}")
                logger.warning(f"Error querying Hugging Face API ({url}) on attempt {attempt+1}/{max_retries}: {e}. Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
                
        raise RuntimeError(f"Hugging Face embedding error: Model failed to load within {max_retries} retries.")

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
            if self.use_api:
                computed_vectors = self._embed_via_hf(to_compute_texts)
            else:
                logger.info(f"Computing embeddings for {len(to_compute_texts)} items...")
                computed_vectors = self.model.encode(
                    to_compute_texts, 
                    show_progress_bar=False,
                    normalize_embeddings=True
                ).tolist()
            
            # Save to cache and populate return list
            for sub_idx, idx in enumerate(to_compute_indices):
                vec = computed_vectors[sub_idx]
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
            
        if self.use_api:
            # We prefix query for retrieval search as required by BGE models
            query_prefix = "Represent this sentence for searching relevant passages: "
            prefixed_text = query_prefix + text
            vector = self._embed_via_hf([prefixed_text])[0]
        else:
            vector = self.model.encode(text, normalize_embeddings=True).tolist()
            
        self._save_cached_embedding(text_hash, vector, text)
        return vector
