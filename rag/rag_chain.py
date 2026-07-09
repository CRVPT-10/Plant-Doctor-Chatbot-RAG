
import os
import time
import sqlite3
import json
from typing import List, Tuple, Dict, Any, Optional
from langchain_core.documents import Document
from pipeline.vector_store import VectorStoreManager
from pipeline.retriever import AgriculturalRetriever
from pipeline.reranker import CrossEncoderReranker
from rag.llm_client import OllamaClient
from rag.prompt_builder import RAGPromptBuilder
from rag.memory import ConversationMemory
from utils.config import config
from utils.logger import get_logger, log_retrieval
from utils.helpers import get_text_hash

logger = get_logger("rag_chain")

class RAGChain:
    """
    Coordinates Retrieval -> Reranking -> Prompt Assembly -> LLM Generation.
    Includes caching for LLM responses and performance latency metrics.
    """
    def __init__(
        self,
        vector_store_manager: VectorStoreManager = None,
        llm_client: OllamaClient = None,
        memory: ConversationMemory = None
    ):
        self.vs_manager = vector_store_manager or VectorStoreManager()
        self.retriever = AgriculturalRetriever(vector_store_manager=self.vs_manager)
        self.reranker = CrossEncoderReranker()
        self.llm_client = llm_client or OllamaClient()
        self.prompt_builder = RAGPromptBuilder()
        self.memory = memory or ConversationMemory()
        
        self.response_cache_dir = config.get_absolute_path("paths.response_cache_dir")
        os.makedirs(self.response_cache_dir, exist_ok=True)
        self.cache_db = os.path.join(self.response_cache_dir, "responses_cache.db")
        self._init_cache_db()

    def _init_cache_db(self):
        with sqlite3.connect(self.cache_db) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS responses (
                    input_hash TEXT PRIMARY KEY,
                    query TEXT,
                    response TEXT,
                    sources_json TEXT,
                    confidence REAL
                )
            """)
            conn.commit()

    def _get_cached_response(self, input_hash: str) -> Optional[Tuple[str, List[Dict[str, Any]], float]]:
        try:
            with sqlite3.connect(self.cache_db) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT response, sources_json, confidence FROM responses WHERE input_hash = ?", 
                    (input_hash,)
                )
                row = cursor.fetchone()
                if row:
                    response, sources_json, confidence = row
                    return response, json.loads(sources_json), float(confidence)
        except Exception as e:
            logger.error(f"Error reading response cache: {e}")
        return None

    def _save_cached_response(self, input_hash: str, query: str, response: str, sources: List[Dict[str, Any]], confidence: float):
        try:
            with sqlite3.connect(self.cache_db) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO responses (input_hash, query, response, sources_json, confidence) VALUES (?, ?, ?, ?, ?)",
                    (input_hash, query, response, json.dumps(sources), confidence)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Error writing response cache: {e}")

    def query(self, user_query: str, session_id: str = "default_session", lang_filter: str = None) -> Dict[str, Any]:
        """
        Processes a user query: Retrieves documents, Reranks them, 
        Builds the prompt, calls LLM (or cache), updates memory, and logs metrics.
        """
        start_time = time.time()
        
        # Normalize query: strip trailing spaces and punctuation (like ? and .) to stabilize dense/sparse retrieval and caching
        normalized_query = user_query.strip()
        while normalized_query and (normalized_query[-1] in "?!.,;:"):
            normalized_query = normalized_query[:-1].strip()
        if normalized_query:
            user_query = normalized_query
        
        # 1. Fetch memory history
        history = self.memory.get_history(session_id)
        
        # 2. Retrieve Candidate Documents (Retrieve 15 candidates for reranking)
        retrieval_start = time.time()
        candidate_docs = self.retriever.retrieve(user_query, top_k_override=15, lang_filter=lang_filter)
        retrieval_time = time.time() - retrieval_start
        
        # 3. Rerank Documents and select the top K (e.g. 5)
        rerank_start = time.time()
        reranked_docs = self.reranker.rerank(user_query, candidate_docs)
        reranked_docs = reranked_docs[:self.retriever.top_k]
        rerank_time = time.time() - rerank_start
        
        # Compute confidence score based on the average similarity score (or rerank score) of final docs
        # If Cross-Encoder is used, we can map bge rerank scores (range: arbitrary, e.g. -5 to +5) to [0.0, 1.0].
        # BGE reranker outputs logits. Let's compute average of retrieval scores if rerank scores are not easily normalized.
        # Alternatively, we can use retrieval score or standard sigmoid mapping for cross encoder scores.
        # Let's use the average retrieval scores of the top-reranked docs. It is normalized cosine similarity.
        if reranked_docs:
            scores = [doc.metadata.get("combined_score", doc.metadata.get("score", 0.5)) for doc in reranked_docs]
            confidence = sum(scores) / len(scores)
        else:
            confidence = 0.0
            
        # Filter memory history to prevent repeating fallback answers (repetition bias)
        clean_history = []
        fallback_phrase = "I could not find sufficient information in the agricultural documents."
        for q, a in history:
            if fallback_phrase.strip().lower() not in a.strip().lower():
                clean_history.append((q, a))

        # 4. Construct prompts
        system_prompt, user_prompt = self.prompt_builder.build_prompts(user_query, reranked_docs, clean_history)
        
        # Prepend explicit language target instruction to system prompt to prevent Qwen Chinese default responses
        lang_names = {
            "en": "English",
            "hi": "Hindi",
            "te": "Telugu",
            "ta": "Tamil"
        }
        target_lang_name = lang_names.get(lang_filter, "English") if lang_filter else "English"
        lang_instruction = f"IMPORTANT: You MUST write your response in {target_lang_name}. Never use any other language (such as Chinese, etc.).\n"
        system_prompt = lang_instruction + system_prompt
        
        # Prepare cache input key: combined system, user prompt, and session history length
        # (This handles cache invalidation when history changes)
        input_key_str = f"system:{system_prompt}|user:{user_prompt}"
        input_hash = get_text_hash(input_key_str)
        
        # 5. Check response cache
        cached = self._get_cached_response(input_hash)
        if cached:
            response_text, sources, cached_confidence = cached
            logger.info("Found cached response. Skipping LLM execution.")
            
            # Update memory with cached response
            self.memory.add_interaction(session_id, user_query, response_text)
            
            total_time = time.time() - start_time
            metrics = {
                "retrieval_time_sec": retrieval_time,
                "rerank_time_sec": rerank_time,
                "llm_inference_time_sec": 0.0,
                "total_time_sec": total_time,
                "cached": True
            }
            log_retrieval(user_query, candidate_docs, reranked_docs, metrics)
            
            return {
                "answer": response_text,
                "sources": sources,
                "confidence": cached_confidence,
                "metrics": metrics
            }
            
        # 6. Execute LLM generation
        llm_start = time.time()
        try:
            response_text = self.llm_client.generate(user_prompt, system_prompt=system_prompt)
        except Exception as e:
            # Fallback handling
            response_text = "I am sorry, but I encountered an error connecting to the LLM backend."
            logger.error(f"LLM generate error: {e}")
            
        llm_time = time.time() - llm_start
        total_time = time.time() - start_time
        
        # Extract source lists for return value
        sources = []
        for doc in reranked_docs:
            sources.append({
                "source": doc.metadata.get("source"),
                "page": doc.metadata.get("page"),
                "chunk_id": doc.metadata.get("chunk_id"),
                "score": doc.metadata.get("score"),
                "rerank_score": doc.metadata.get("rerank_score"),
                "content": doc.page_content
            })
            
        # Save to Cache (only if it is a successful search result rather than LLM error or fallback message)
        fallback_phrase = "I could not find sufficient information in the agricultural documents."
        is_fallback = fallback_phrase.strip().lower() in response_text.strip().lower()
        
        if "encountered an error" not in response_text and not is_fallback:
            self._save_cached_response(input_hash, user_query, response_text, sources, confidence)
            
        # Add to memory regardless
        self.memory.add_interaction(session_id, user_query, response_text)
            
        metrics = {
            "retrieval_time_sec": retrieval_time,
            "rerank_time_sec": rerank_time,
            "llm_inference_time_sec": llm_time,
            "total_time_sec": total_time,
            "cached": False
        }
        
        # Log metrics to retrieval.log
        log_retrieval(user_query, candidate_docs, reranked_docs, metrics)
        
        return {
            "answer": response_text,
            "sources": sources,
            "confidence": confidence,
            "metrics": metrics
        }

    def clear_cache(self) -> bool:
        """Clears all entries in the response cache database."""
        try:
            with sqlite3.connect(self.cache_db) as conn:
                conn.execute("DELETE FROM responses")
                conn.commit()
            logger.info("Response cache cleared successfully.")
            return True
        except Exception as e:
            logger.error(f"Error clearing response cache: {e}")
            return False
