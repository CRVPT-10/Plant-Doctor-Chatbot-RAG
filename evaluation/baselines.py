import sys
import os
from typing import List
from pipeline.vector_store import VectorStoreManager
from pipeline.retriever import AgriculturalRetriever
from utils.logger import get_logger

logger = get_logger("baselines")

def compare_retrieval_strategies(query: str, top_k: int = 5):
    """
    Compares the outputs of Dense vector search, Sparse BM25 keyword search, 
    and Hybrid search for a sample query.
    """
    vs_manager = VectorStoreManager()
    
    # Check if empty
    indexed = vs_manager.get_all_indexed_documents()
    if not indexed:
        print("\n⚠️ Vector database is empty. Please upload documents before running comparisons.\n")
        return
        
    retriever = AgriculturalRetriever(vector_store_manager=vs_manager)
    
    print("\n" + "="*85)
    print(f"🔍 RETRIEVER BASELINE COMPARISON FOR QUERY: '{query}'")
    print("="*85)
    
    # 1. Dense Only
    dense_docs = retriever.retrieve(query, search_type_override="similarity", top_k_override=top_k)
    print("\n🔹 [1] Dense Vector Search (FAISS Cosine Similarity)")
    for i, doc in enumerate(dense_docs):
        print(f"   {i+1}. Chunk ID: {doc.metadata.get('chunk_id')} | Score: {doc.metadata.get('score', 0.0):.4f} | Source: {doc.metadata.get('source')} | Preview: {doc.page_content[:60]}...")
        
    # 2. Sparse Only
    # Standard BM25 requires loading corpus
    corpus = retriever._get_corpus_from_db()
    from pipeline.retriever import SimpleBM25
    bm25 = SimpleBM25(corpus)
    bm25_results = bm25.score(query, top_k=top_k)
    
    print("\n🔹 [2] Sparse Keyword Search (BM25)")
    for i, (doc, score) in enumerate(bm25_results):
        print(f"   {i+1}. Chunk ID: {doc.metadata.get('chunk_id')} | Raw BM25 Score: {score:.2f} | Source: {doc.metadata.get('source')} | Preview: {doc.page_content[:60]}...")
        
    # 3. Hybrid (Dense + Sparse)
    hybrid_docs = retriever.retrieve(query, search_type_override="hybrid", top_k_override=top_k)
    print("\n🔹 [3] Hybrid Search (Combined Dense & Sparse)")
    for i, doc in enumerate(hybrid_docs):
        print(f"   {i+1}. Chunk ID: {doc.metadata.get('chunk_id')} | Hybrid Score: {doc.metadata.get('score', 0.0):.4f} | Dense Score: {doc.metadata.get('dense_score', 0.0):.4f} | Sparse Score: {doc.metadata.get('sparse_score', 0.0):.4f} | Source: {doc.metadata.get('source')} | Preview: {doc.page_content[:60]}...")
        
    # Analyzes Overlap
    dense_ids = {d.metadata.get('chunk_id') for d in dense_docs}
    bm25_ids = {d.metadata.get('chunk_id') for d, _ in bm25_results}
    hybrid_ids = {d.metadata.get('chunk_id') for d in hybrid_docs}
    
    overlap = dense_ids.intersection(bm25_ids)
    print("\n" + "-"*85)
    print(f"📊 SUMMARY OVERLAP ANALYSIS:")
    print(f"   - Total unique chunks retrieved (Dense Union Sparse): {len(dense_ids.union(bm25_ids))}")
    print(f"   - Chunks retrieved by BOTH Dense and Sparse: {len(overlap)}")
    for chunk_id in overlap:
        print(f"     * {chunk_id}")
    print("="*85 + "\n")

if __name__ == "__main__":
    test_query = "tomato leaf disease yellow curling"
    if len(sys.argv) > 1:
        test_query = " ".join(sys.argv[1:])
        
    compare_retrieval_strategies(test_query)
