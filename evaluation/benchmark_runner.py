import time
from rag.rag_chain import RAGChain
from pipeline.vector_store import VectorStoreManager
from utils.logger import get_logger

logger = get_logger("benchmark_runner")

BENCHMARK_QUERIES = [
    "yellowing of tomato leaves treatment",
    "rice blast disease chemical control",
    "basal nitrogen dose for organic wheat crop",
    "how to prevent aphids in vegetables",
    "organic pesticide home recipe"
]

def run_speed_benchmark():
    """
    Stress-tests the pipeline with multiple queries, measuring average speeds.
    """
    logger.info("Initializing speed benchmark runner...")
    vs_manager = VectorStoreManager()
    rag_chain = RAGChain(vector_store_manager=vs_manager)
    
    indexed = vs_manager.get_all_indexed_documents()
    if not indexed:
        print("\n⚠️ FAISS index is empty. Benchmarking speed on empty index (low latency fallback).")
        
    print("\n" + "="*80)
    print("⚡ PLANT DOCTOR PIPELINE LATENCY SPEED BENCHMARK ⚡")
    print("="*80)
    
    total_retrieval = 0.0
    total_rerank = 0.0
    total_llm = 0.0
    total_e2e = 0.0
    
    num_queries = len(BENCHMARK_QUERIES)
    
    for idx, q in enumerate(BENCHMARK_QUERIES):
        print(f"Run {idx+1}/{num_queries}: '{q}'")
        
        # Track end to end time
        e2e_start = time.time()
        result = rag_chain.query(q, session_id=f"benchmark_session_{idx}")
        e2e_latency = time.time() - e2e_start
        
        metrics = result.get("metrics", {})
        
        total_retrieval += metrics.get("retrieval_time_sec", 0.0)
        total_rerank += metrics.get("rerank_time_sec", 0.0)
        total_llm += metrics.get("llm_inference_time_sec", 0.0)
        total_e2e += e2e_latency
        
        print(f"   - Retrieval: {metrics.get('retrieval_time_sec', 0.0)*1000:.1f}ms")
        print(f"   - Rerank: {metrics.get('rerank_time_sec', 0.0)*1000:.1f}ms" if metrics.get('rerank_time_sec') else "   - Rerank: Disabled")
        print(f"   - LLM: {metrics.get('llm_inference_time_sec', 0.0)*1000:.1f}ms")
        print(f"   - Total End-to-End: {e2e_latency:.2f}s")
        
    print("\n" + "="*80)
    print("📊 LATENCY BENCHMARK METRIC AVERAGES")
    print("="*80)
    print(f"Average Vector Retrieval: {total_retrieval / num_queries * 1000:.1f} ms")
    print(f"Average Cross-Rerank:     {total_rerank / num_queries * 1000:.1f} ms")
    print(f"Average LLM Generation:    {total_llm / num_queries * 1000:.1f} ms")
    print(f"Average End-to-End:        {total_e2e / num_queries:.3f} seconds")
    print("="*80 + "\n")

if __name__ == "__main__":
    run_speed_benchmark()
