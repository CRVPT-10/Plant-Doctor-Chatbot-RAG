import pytest
from langchain_core.documents import Document
from pipeline.chunker import DocumentChunker

def test_document_chunker_basic():
    """Verify text is split into chunks correctly and parameters are respected."""
    chunk_size = 100
    chunk_overlap = 20
    chunker = DocumentChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    
    text = "This is a long sentence that will be split by the chunker tool into multiple separate sections for testing."
    doc = Document(page_content=text, metadata={"doc_id": "test_doc", "page": 1, "source": "test.txt"})
    
    chunks = chunker.chunk_document(doc)
    
    assert len(chunks) > 1
    for i, c in enumerate(chunks):
        assert c.metadata["chunk_id"] == f"test_doc_p1_c{i}"
        assert c.metadata["parent_id"] == "test_doc"
        assert len(c.page_content) <= chunk_size

def test_document_chunker_empty():
    """Verify empty document returns empty chunks."""
    chunker = DocumentChunker()
    doc = Document(page_content="   ", metadata={"doc_id": "empty"})
    chunks = chunker.chunk_document(doc)
    assert len(chunks) == 0
