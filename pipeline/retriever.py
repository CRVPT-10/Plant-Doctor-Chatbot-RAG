import re
import math
import sqlite3
from typing import List, Tuple, Dict, Any
from langchain_core.documents import Document
from pipeline.vector_store import VectorStoreManager
from utils.config import config
from utils.logger import get_logger

logger = get_logger("retriever")

class SimpleBM25:
    """
    Self-contained lightweight pure-Python BM25 search.
    Provides keyword search over documents.
    """
    def __init__(self, documents: List[Document], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.documents = documents
        self.corpus_size = len(documents)
        
        # Tokenize documents
        self.doc_len = []
        self.doc_term_freqs = []
        self.df = {}
        
        for doc in documents:
            tokens = self._tokenize(doc.page_content)
            self.doc_len.append(len(tokens))
            
            # Count term frequencies
            tf = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1
            self.doc_term_freqs.append(tf)
            
            # Document frequency
            for t in tf.keys():
                self.df[t] = self.df.get(t, 0) + 1
                
        self.avg_doc_len = sum(self.doc_len) / self.corpus_size if self.corpus_size > 0 else 0
        
        # Calculate IDF
        self.idf = {}
        for word, freq in self.df.items():
            # Standard BM25 IDF
            self.idf[word] = math.log((self.corpus_size - freq + 0.5) / (freq + 0.5) + 1.0)

    def _tokenize(self, text: str) -> List[str]:
        # Lowercase and split on non-alphanumeric
        return re.findall(r"\w+", text.lower())

    def score(self, query: str, top_k: int = 5) -> List[Tuple[Document, float]]:
        """Scores all documents against a query and returns top K with scores."""
        if self.corpus_size == 0:
            return []
            
        query_tokens = self._tokenize(query)
        scores = []
        
        for idx, doc in enumerate(self.documents):
            score = 0.0
            tf = self.doc_term_freqs[idx]
            d_len = self.doc_len[idx]
            
            for token in query_tokens:
                if token not in tf:
                    continue
                # BM25 formula
                num = tf[token] * (self.k1 + 1)
                denom = tf[token] + self.k1 * (1.0 - self.b + self.b * (d_len / self.avg_doc_len))
                score += self.idf.get(token, 0.0) * (num / denom)
                
            scores.append((doc, score))
            
        # Sort desc by score
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def score_all(self, query: str) -> Dict[str, float]:
        """Scores all documents against a query and returns a mapping of chunk_id -> score."""
        if self.corpus_size == 0:
            return {}
            
        query_tokens = self._tokenize(query)
        scores = {}
        
        for idx, doc in enumerate(self.documents):
            score = 0.0
            tf = self.doc_term_freqs[idx]
            d_len = self.doc_len[idx]
            
            for token in query_tokens:
                if token not in tf:
                    continue
                # BM25 formula
                num = tf[token] * (self.k1 + 1)
                denom = tf[token] + self.k1 * (1.0 - self.b + self.b * (d_len / self.avg_doc_len))
                score += self.idf.get(token, 0.0) * (num / denom)
                
            chunk_id = doc.metadata.get("chunk_id")
            scores[chunk_id] = score
            
        return scores


class AgriculturalRetriever:
    """
    Retrieves agricultural documents based on configurable strategies:
    - Cosine Similarity (Dense)
    - MMR (Maximal Marginal Relevance)
    - BM25 (Sparse Keyword)
    - Hybrid (Combined Dense & Sparse)
    Filters results by Similarity Threshold when configured.
    """
    def __init__(self, vector_store_manager: VectorStoreManager = None):
        self.vs_manager = vector_store_manager or VectorStoreManager()
        
        # Load configs
        self.search_type = config.get("retrieval.search_type", "similarity")
        self.top_k = config.get("retrieval.top_k", 5)
        self.fetch_k = config.get("retrieval.fetch_k", 10)
        self.similarity_threshold = config.get("retrieval.similarity_threshold", 0.5)
        self.lambda_mult = config.get("retrieval.lambda_mult", 0.5)
        self.hybrid_weight = config.get("retrieval.hybrid_weight", 0.5)

    def retrieve(self, query: str, search_type_override: str = None, top_k_override: int = None, lang_filter: str = None) -> List[Document]:
        """
        Retrieves matching documents based on query, search type, and filters.
        """
        search_type = search_type_override or self.search_type
        top_k = top_k_override or self.top_k
        
        logger.info(f"Retrieving for query: '{query}' | Type: {search_type} | Top K: {top_k}")
        
        if search_type == "similarity":
            results = self._retrieve_dense(query, top_k, lang_filter)
        elif search_type == "mmr":
            results = self._retrieve_mmr(query, top_k, lang_filter)
        elif search_type == "similarity_threshold":
            results = self._retrieve_dense(query, top_k, lang_filter)
            results = [doc for doc in results if doc.metadata.get("score", 0.0) >= self.similarity_threshold]
        elif search_type == "hybrid":
            results = self._retrieve_hybrid(query, top_k, lang_filter)
        else:
            logger.warning(f"Unknown search type {search_type}. Falling back to similarity.")
            results = self._retrieve_dense(query, top_k, lang_filter)
            
        logger.info(f"Retrieved {len(results)} chunks.")
        return results

    def _get_corpus_from_db(self, lang_filter: str = None) -> List[Document]:
        """Loads all documents from metadata SQLite database to construct BM25 index."""
        docs = []
        with sqlite3.connect(self.vs_manager.db_path) as conn:
            cursor = conn.cursor()
            if lang_filter:
                cursor.execute("""
                    SELECT chunk_id, doc_id, source, page, file_path, language, page_content 
                    FROM chunk_metadata WHERE language = ?
                """, (lang_filter,))
            else:
                cursor.execute("""
                    SELECT chunk_id, doc_id, source, page, file_path, language, page_content 
                    FROM chunk_metadata
                """)
            rows = cursor.fetchall()
            for r in rows:
                docs.append(Document(
                    page_content=r[6],
                    metadata={
                        "chunk_id": r[0],
                        "doc_id": r[1],
                        "source": r[2],
                        "page": r[3],
                        "file_path": r[4],
                        "language": r[5]
                    }
                ))
        return docs

    def _retrieve_dense(self, query: str, top_k: int, lang_filter: str = None) -> List[Document]:
        """Retrieves using standard FAISS similarity search."""
        # Note: If lang_filter is active, we might get docs in other languages from FAISS vector search,
        # so we fetch more (e.g. top_k * 4) and then filter manually.
        fetch_limit = top_k * 4 if lang_filter else top_k
        raw_results = self.vs_manager.search_vectors(query, top_k=fetch_limit)
        
        docs = []
        for doc, score in raw_results:
            if lang_filter and doc.metadata.get("language") != lang_filter:
                continue
            doc.metadata["score"] = score
            docs.append(doc)
            
        return docs[:top_k]

    def _retrieve_mmr(self, query: str, top_k: int, lang_filter: str = None) -> List[Document]:
        """
        Retrieves using Maximal Marginal Relevance for search result diversity.
        """
        # Fetch candidate documents first via similarity search
        candidates = self.vs_manager.search_vectors(query, top_k=self.fetch_k)
        if not candidates:
            return []
            
        # Filter by language if needed
        if lang_filter:
            candidates = [(d, s) for d, s in candidates if d.metadata.get("language") == lang_filter]
            
        if not candidates:
            return []
            
        # Get query embedding
        query_embedding = self.vs_manager.embeddings.embed_query(query)
        
        # In langchain FAISS, we can call mmr search directly or compute it manually.
        # Since we use our own metadata layer, we can implement it or just use FAISS's native mmr search.
        # We can implement a clean MMR ranking from our candidates.
        # MMR = arg max_Di [ lambda * Sim(Di, Query) - (1 - lambda) * max_Dj Sim(Di, Dj) ]
        # To compute similarity between documents, we can fetch document embeddings.
        # But to be simple and accurate, we can call FAISS's max_marginal_relevance_search if filter is not needed.
        # If language filter is active or we want custom control:
        # Let's perform standard manual MMR selection:
        selected_docs: List[Document] = []
        
        # Fetch embeddings for all candidate contents
        candidate_docs = [c[0] for c in candidates]
        candidate_embeddings = self.vs_manager.embeddings.embed_documents([d.page_content for d in candidate_docs])
        
        unselected_indices = list(range(len(candidate_docs)))
        
        # Let's run MMR algorithm
        while len(selected_docs) < top_k and unselected_indices:
            best_mmr = -100.0
            best_idx = -1
            
            for idx in unselected_indices:
                # Similarity to query
                sim_query = candidates[idx][1] # Cached Cosine similarity
                
                # Max similarity to already selected docs
                max_sim_selected = 0.0
                if selected_docs:
                    doc_emb = candidate_embeddings[idx]
                    # Compute cosine similarities with selected docs
                    selected_embs = [candidate_embeddings[s] for s in range(len(candidate_docs)) if s not in unselected_indices]
                    
                    # dot product of normalized embeddings = cosine similarity
                    similarities = [np_dot(doc_emb, s_emb) for s_emb in selected_embs]
                    max_sim_selected = max(similarities) if similarities else 0.0
                    
                mmr_score = self.lambda_mult * sim_query - (1.0 - self.lambda_mult) * max_sim_selected
                
                if mmr_score > best_mmr:
                    best_mmr = mmr_score
                    best_idx = idx
                    
            if best_idx == -1:
                break
                
            selected_docs.append(candidate_docs[best_idx])
            selected_docs[-1].metadata["score"] = candidates[best_idx][1]
            unselected_indices.remove(best_idx)
            
        return selected_docs

    def _retrieve_hybrid(self, query: str, top_k: int, lang_filter: str = None) -> List[Document]:
        """
        Combines dense similarity search and sparse BM25 search.
        """
        # Fetch dense results
        dense_results = self._retrieve_dense(query, top_k=top_k * 2, lang_filter=lang_filter)
        
        # Load corpus for BM25
        corpus = self._get_corpus_from_db(lang_filter=lang_filter)
        if not corpus:
            return dense_results[:top_k]
            
        # Run BM25 keyword search
        bm25 = SimpleBM25(corpus)
        bm25_results = bm25.score(query, top_k=top_k * 2)
        all_bm25_scores = bm25.score_all(query)
        
        # Standardize BM25 scores to [0.0, 1.0] range
        max_bm25_score = max(all_bm25_scores.values()) if all_bm25_scores else 0.0
        
        # Merge scores
        doc_scores: Dict[str, Tuple[Document, float, float]] = {} # chunk_id -> (Doc, dense_score, bm25_score)
        
        for doc in dense_results:
            chunk_id = doc.metadata.get("chunk_id")
            dense_score = doc.metadata.get("score", 0.0)
            bm25_raw = all_bm25_scores.get(chunk_id, 0.0)
            normalized_bm25 = bm25_raw / max_bm25_score if max_bm25_score > 0 else 0.0
            doc_scores[chunk_id] = (doc, dense_score, normalized_bm25)
            
        for doc, score in bm25_results:
            chunk_id = doc.metadata.get("chunk_id")
            if chunk_id not in doc_scores:
                normalized_bm25 = score / max_bm25_score if max_bm25_score > 0 else 0.0
                doc_scores[chunk_id] = (doc, 0.0, normalized_bm25)
                
        # Calculate hybrid weighted score
        final_list = []
        for chunk_id, (doc, dense_score, bm25_score) in doc_scores.items():
            # Weighted average
            hybrid_score = self.hybrid_weight * dense_score + (1.0 - self.hybrid_weight) * bm25_score
            doc.metadata["score"] = hybrid_score
            doc.metadata["dense_score"] = dense_score
            doc.metadata["sparse_score"] = bm25_score
            final_list.append(doc)
            
        # Sort and return Top K
        final_list.sort(key=lambda x: x.metadata["score"], reverse=True)
        return final_list[:top_k]

def np_dot(a: List[float], b: List[float]) -> float:
    """Helper dot product since we avoid importing massive numpy functions unnecessarily."""
    return sum(x * y for x, y in zip(a, b))
