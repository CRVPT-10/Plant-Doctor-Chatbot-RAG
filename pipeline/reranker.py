import os
from typing import List
# pyrefly: ignore [missing-import]
from sentence_transformers import CrossEncoder
from langchain_core.documents import Document
from utils.config import config
from utils.logger import get_logger

logger = get_logger("reranker")

class CrossEncoderReranker:
    """
    Reranks retrieved documents using a Cross-Encoder model (BAAI/bge-reranker-base).
    Computes a query-document match score and re-sorts results.
    """
    def __init__(self, model_name: str = None, device: str = None):
        self.enabled = config.get("reranker.enabled", True)
        self.model_name = model_name or config.get("reranker.model_name", "BAAI/bge-reranker-base")
        self.device = device or config.get("reranker.device", "cpu")
        self.models_dir = config.get_absolute_path("paths.models_dir")
        self.top_n = config.get("reranker.top_n", 3)
        
        self.model = None
        if self.enabled:
            reranker_cache_dir = os.path.join(self.models_dir, "reranker")
            os.makedirs(reranker_cache_dir, exist_ok=True)
            
            logger.info(f"Loading CrossEncoder: {self.model_name} on device {self.device}")
            try:
                self.model = CrossEncoder(
                    self.model_name,
                    cache_folder=reranker_cache_dir,
                    device=self.device
                )
                logger.info("CrossEncoder reranker loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load CrossEncoder reranker: {e}. Disabling reranker.")
                self.enabled = False

    def rerank(self, query: str, documents: List[Document]) -> List[Document]:
        """
        Reranks a list of retrieved documents against the query.
        Returns the top N reranked documents.
        """
        if not self.enabled or not self.model or not documents:
            logger.info("Reranking skipped (disabled or empty input).")
            # If skipped, return up to top_n documents directly
            return documents[:self.top_n]
            
        logger.info(f"Reranking {len(documents)} documents against query: '{query}'")
        
        # Build query-document pairs
        pairs = [[query, doc.page_content] for doc in documents]
        
        try:
            # Predict scores (higher is more relevant)
            scores = self.model.predict(pairs)
            
            # Attach score to metadata and sort
            import math
            reranked_docs = []
            for doc, score in zip(documents, scores):
                doc.metadata["rerank_score"] = float(score)
                
                # Fetch original retrieval hybrid score
                retrieval_score = doc.metadata.get("score", 0.5)
                retrieval_score = max(0.0, min(1.0, retrieval_score))
                
                # Sigmoid mapping of raw logit score
                try:
                    sig_score = 1.0 / (1.0 + math.exp(-float(score)))
                except Exception:
                    sig_score = 0.5
                    
                # Combined score: 40% retrieval, 60% rerank
                doc.metadata["combined_score"] = 0.4 * retrieval_score + 0.6 * sig_score
                reranked_docs.append(doc)
                
            # Sort descending by combined score
            reranked_docs.sort(key=lambda x: x.metadata["combined_score"], reverse=True)
            
            # Log top reranked document scores
            for i, doc in enumerate(reranked_docs[:3]):
                logger.info(f"Reranked Top {i+1}: Source: {doc.metadata.get('source')} | Score: {doc.metadata.get('combined_score'):.4f} | Rerank Raw: {doc.metadata.get('rerank_score'):.4f}")
                
            return reranked_docs[:self.top_n]
            
        except Exception as e:
            logger.error(f"Error during reranking: {e}. Returning original ranking.")
            return documents[:self.top_n]
