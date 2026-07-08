import os
import sys

# Add project root directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.rag_chain import RAGChain
from utils.logger import get_logger

logger = get_logger("cli_test")

def main():
    if len(sys.argv) < 2:
        print("\n[Error] Please provide a query string.")
        print("Usage: python scripts/test_query.py \"<your question here>\" [--lang <code_str>]\n")
        sys.exit(1)
        
    query = sys.argv[1]
    
    # Check for optional language filter
    lang_filter = None
    if "--lang" in sys.argv:
        idx = sys.argv.index("--lang")
        if idx + 1 < len(sys.argv):
            lang_filter = sys.argv[idx + 1]

    print(f"\nQuerying RAG Chain: '{query}' (Language Filter: {lang_filter})")
    
    try:
        rag = RAGChain()
        res = rag.query(query, session_id="cli_test_session", lang_filter=lang_filter)
        
        print("\n" + "="*80)
        print("PLANT DOCTOR RESPONSE:")
        print("="*80)
        print(res["answer"])
        print("\n" + "="*80)
        print(f"Confidence Score: {res['confidence']*100:.1f}%")
        print(f"Retrieval Latency: {res['metrics'].get('retrieval_time_sec', 0.0)*1000:.1f}ms")
        print(f"Rerank Latency:    {res['metrics'].get('rerank_time_sec', 0.0)*1000:.1f}ms")
        print(f"LLM Inference:     {res['metrics'].get('llm_inference_time_sec', 0.0)*1000:.1f}ms")
        print(f"Total Time:        {res['metrics'].get('total_time_sec', 0.0):.3f}s")
        print(f"From Response Cache: {res['metrics'].get('cached', False)}")
        
        print("\nSources Cited:")
        for idx, src in enumerate(res["sources"]):
            print(f"  [{idx+1}] File: {src['source']} (Page {src['page']}) | Similarity Score: {src['score']:.4f}")
            print(f"      Snippet: \"{src['content'][:120]}...\"")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n[Error] Execution failed: {e}")
        logger.exception("CLI test query failure")

if __name__ == "__main__":
    main()
