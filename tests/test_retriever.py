import pytest
from langchain_core.documents import Document
from pipeline.retriever import SimpleBM25

def test_simple_bm25_search():
    """Verify BM25 keyword matching and scoring works with standard corpus."""
    docs = [
        Document(page_content="Tomato plants suffer from leaf curl virus transmitted by whiteflies.", metadata={"chunk_id": "c1"}),
        Document(page_content="Rice blast disease is caused by Magnaporthe oryzae fungi.", metadata={"chunk_id": "c2"}),
        Document(page_content="Wheat crops require balanced nitrogen dose of 120 kg/ha.", metadata={"chunk_id": "c3"}),
    ]
    
    bm25 = SimpleBM25(docs)
    
    # Query matching tomato
    results = bm25.score("tomato whitefly", top_k=2)
    assert len(results) > 0
    assert results[0][0].metadata["chunk_id"] == "c1"
    assert results[0][1] > 0.0
    
    # Query matching wheat
    results_wheat = bm25.score("nitrogen doses", top_k=1)
    assert results_wheat[0][0].metadata["chunk_id"] == "c3"
