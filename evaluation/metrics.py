import re
from typing import List, Dict, Any, Optional
from pipeline.embedder import CachedEmbeddings
from utils.logger import get_logger

logger = get_logger("evaluation_metrics")

class RAGEvaluator:
    """
    Computes local RAG evaluation metrics (Faithfulness, Relevancy, 
    Precision, Recall) using cached sentence embeddings.
    """
    def __init__(self, embeddings: CachedEmbeddings = None):
        self.embeddings = embeddings or CachedEmbeddings()

    def _cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        dot_product = sum(x * y for x, y in zip(vec_a, vec_b))
        norm_a = sum(x * x for x in vec_a) ** 0.5
        norm_b = sum(x * x for x in vec_b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)

    def calculate_answer_relevance(self, query: str, answer: str) -> float:
        """Calculates similarity between query and generated answer."""
        if not query or not answer:
            return 0.0
        q_emb = self.embeddings.embed_query(query)
        a_emb = self.embeddings.embed_query(answer)
        return float(self._cosine_similarity(q_emb, a_emb))

    def calculate_context_precision(self, query: str, context_chunks: List[str]) -> float:
        """
        Context Precision: How relevant are the retrieved chunks to the query?
        Calculated as the average similarity between the query and each context chunk.
        """
        if not query or not context_chunks:
            return 0.0
            
        q_emb = self.embeddings.embed_query(query)
        chunk_embs = self.embeddings.embed_documents(context_chunks)
        
        similarities = [self._cosine_similarity(q_emb, c_emb) for c_emb in chunk_embs]
        return float(sum(similarities) / len(similarities)) if similarities else 0.0

    def calculate_faithfulness(self, answer: str, context_chunks: List[str]) -> float:
        """
        Faithfulness: Is the answer derived strictly from context?
        Measures the fraction of generated answer sentences that are semantically 
        grounded in the retrieved context chunks (similarity >= 0.70).
        """
        if not answer or not context_chunks:
            return 1.0 # Vacuously faithful if empty
            
        # Split answer into sentences
        sentences = [s.strip() for s in re.split(r"[.!?\n]+", answer) if len(s.strip()) > 8]
        if not sentences:
            return 1.0
            
        # Combine all context into a set of context sentences
        context_text = " ".join(context_chunks)
        context_sentences = [s.strip() for s in re.split(r"[.!?\n]+", context_text) if len(s.strip()) > 8]
        if not context_sentences:
            return 0.0
            
        # Embed all sentences
        sentence_embs = self.embeddings.embed_documents(sentences)
        context_embs = self.embeddings.embed_documents(context_sentences)
        
        grounded_sentences = 0
        for s_emb in sentence_embs:
            # Check if this sentence matches ANY context sentence closely
            max_sim = 0.0
            for c_emb in context_embs:
                sim = self._cosine_similarity(s_emb, c_emb)
                if sim > max_sim:
                    max_sim = sim
            
            # Grounding threshold (0.65 is reasonable for semantic sentence match)
            if max_sim >= 0.65:
                grounded_sentences += 1
                
        return float(grounded_sentences / len(sentences))

    def calculate_context_recall(self, query: str, context_chunks: List[str], ground_truth: str) -> float:
        """
        Context Recall: Did we retrieve all the information needed to answer the query?
        Measures semantic coverage of the ground truth sentences by the retrieved context.
        """
        if not ground_truth or not context_chunks:
            return 0.0
            
        # Split ground truth into sentences
        gt_sentences = [s.strip() for s in re.split(r"[.!?\n]+", ground_truth) if len(s.strip()) > 8]
        if not gt_sentences:
            return 1.0
            
        context_text = " ".join(context_chunks)
        context_sentences = [s.strip() for s in re.split(r"[.!?\n]+", context_text) if len(s.strip()) > 8]
        if not context_sentences:
            return 0.0
            
        gt_embs = self.embeddings.embed_documents(gt_sentences)
        context_embs = self.embeddings.embed_documents(context_sentences)
        
        covered_gt = 0
        for gt_emb in gt_embs:
            max_sim = 0.0
            for c_emb in context_embs:
                sim = self._cosine_similarity(gt_emb, c_emb)
                if sim > max_sim:
                    max_sim = sim
            if max_sim >= 0.65:
                covered_gt += 1
                
        return float(covered_gt / len(gt_sentences))

    def evaluate_turn(self, query: str, answer: str, context_chunks: List[str], ground_truth: Optional[str] = None) -> Dict[str, float]:
        """Runs all applicable evaluations for a single turn."""
        metrics = {
            "faithfulness": self.calculate_faithfulness(answer, context_chunks),
            "context_precision": self.calculate_context_precision(query, context_chunks),
            "answer_relevance": self.calculate_answer_relevance(query, answer)
        }
        if ground_truth:
            metrics["context_recall"] = self.calculate_context_recall(query, context_chunks, ground_truth)
            
        return metrics
