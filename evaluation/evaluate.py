import time
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.metrics import RAGEvaluator
from rag.rag_chain import RAGChain
from pipeline.vector_store import VectorStoreManager
from utils.logger import get_logger

logger = get_logger("evaluation_runner")

# Sample Agriculture QA dataset for benchmarking
BENCHMARK_QA = [
    {
        "query": "What are the symptoms of tomato yellow leaf curl virus?",
        "ground_truth": "Tomato yellow leaf curl virus symptoms include severe stunting, yellowing leaf margins, upward leaf cupping, and reduced fruit yield."
    },
    {
        "query": "How can farmers manage rice blast disease?",
        "ground_truth": "Rice blast is controlled by planting resistant cultivars, avoiding excessive nitrogen fertilizers, maintaining proper water levels, and applying recommended fungicides."
    },
    {
        "query": "What is the recommended nitrogen dose for wheat crops?",
        "ground_truth": "The general recommendation for wheat is 120 kg Nitrogen per hectare, usually split into basal application and top dressing."
    }
]

def run_evaluation_suite():
    """Runs benchmark agricultural queries through RAG, computing all metrics."""
    logger.info("Initializing RAG chain for evaluation...")
    
    vs_manager = VectorStoreManager()
    rag_chain = RAGChain(vector_store_manager=vs_manager)
    evaluator = RAGEvaluator(embeddings=vs_manager.embeddings)
    
    # Check if there are documents in FAISS index to retrieval
    indexed = vs_manager.get_all_indexed_documents()
    if not indexed:
        print("\nWARNING: FAISS index is empty! Evaluation metrics will be mock or fallbacks. Upload documents first.")
        logger.warning("FAISS index is empty during evaluation.")
        
    print("\n" + "="*80)
    print("PLANT DOCTOR CHATBOT RAG EVALUATION BENCHMARK")
    print("="*80)
    
    total_faithfulness = 0.0
    total_precision = 0.0
    total_relevance = 0.0
    total_recall = 0.0
    total_latency = 0.0
    
    num_tests = len(BENCHMARK_QA)
    
    for idx, item in enumerate(BENCHMARK_QA):
        query = item["query"]
        gt = item["ground_truth"]
        
        print(f"\n[{idx+1}/{num_tests}] Query: '{query}'")
        
        # Execute RAG query loop
        start = time.time()
        result = rag_chain.query(query, session_id=f"eval_session_{idx}")
        latency = time.time() - start
        
        answer = result["answer"]
        context_chunks = [src["content"] for src in result["sources"]]
        
        # Compute metrics
        turn_metrics = evaluator.evaluate_turn(
            query=query,
            answer=answer,
            context_chunks=context_chunks,
            ground_truth=gt
        )
        
        print(f"-> Generated Answer: {answer[:120]}...")
        print(f"-> Metrics:")
        print(f"   - Latency: {latency:.2f}s")
        print(f"   - Faithfulness: {turn_metrics['faithfulness']*100:.1f}%")
        print(f"   - Context Precision: {turn_metrics['context_precision']*100:.1f}%")
        print(f"   - Context Recall: {turn_metrics['context_recall']*100:.1f}%")
        print(f"   - Answer Relevancy: {turn_metrics['answer_relevance']*100:.1f}%")
        
        total_faithfulness += turn_metrics["faithfulness"]
        total_precision += turn_metrics["context_precision"]
        total_relevance += turn_metrics["answer_relevance"]
        total_recall += turn_metrics["context_recall"]
        total_latency += latency
        
    avg_faithfulness = total_faithfulness / num_tests
    avg_precision = total_precision / num_tests
    avg_relevance = total_relevance / num_tests
    avg_recall = total_recall / num_tests
    avg_latency = total_latency / num_tests
    
    print("\n" + "="*80)
    print("BENCHMARK AVERAGE PERFORMANCE SUMMARY")
    print("="*80)
    print(f"Avg End-to-End Latency: {avg_latency:.2f}s")
    print(f"Avg Faithfulness (Grounding): {avg_faithfulness*100:.1f}%")
    print(f"Avg Context Precision (Retrieval): {avg_precision*100:.1f}%")
    print(f"Avg Context Recall (Retrieval): {avg_recall*100:.1f}%")
    print(f"Avg Answer Relevancy (LLM): {avg_relevance*100:.1f}%")
    print("="*80 + "\n")

if __name__ == "__main__":
    run_evaluation_suite()
