import pytest
from langchain_core.documents import Document
from rag.prompt_builder import RAGPromptBuilder

def test_rag_prompt_builder():
    """Verify prompt builder formats system and user messages correctly."""
    builder = RAGPromptBuilder()
    
    docs = [
        Document(page_content="Tomato leaf curl virus is spread by whiteflies.", metadata={"source": "tomato.txt", "page": 1, "chunk_id": "ch1"})
    ]
    history = [("hello", "Hi! how can I help?")]
    query = "What spreads the virus?"
    
    system_prompt, user_prompt = builder.build_prompts(query, docs, history)
    
    # Assertions
    assert "Plant Doctor" in system_prompt
    assert "tomato.txt" in user_prompt
    assert "Page: 1" in user_prompt
    assert "What spreads the virus?" in user_prompt
    assert "Hi! how can I help?" in user_prompt
    assert "I could not find sufficient information in the agricultural documents." in user_prompt
