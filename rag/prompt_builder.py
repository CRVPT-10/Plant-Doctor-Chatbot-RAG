from typing import List, Tuple
from langchain_core.documents import Document
from utils.config import config
from utils.logger import get_logger

logger = get_logger("prompt_builder")

class RAGPromptBuilder:
    """
    Constructs the system and user prompts for RAG execution, 
    incorporating context documents and historical memory.
    """
    def __init__(self):
        self.system_template = config.get_prompt("system_prompt")
        self.context_template = config.get_prompt("context_template")
        self.user_template = config.get_prompt("user_prompt")

    def build_context_string(self, docs: List[Document]) -> str:
        """Formats retrieved documents into a single context string."""
        if not docs:
            return "No relevant agricultural documents found in the database."
            
        formatted_chunks = []
        for idx, doc in enumerate(docs):
            meta = doc.metadata
            chunk_str = self.context_template.format(
                source=meta.get("source", "Unknown Document"),
                page=meta.get("page", "N/A"),
                chunk_id=meta.get("chunk_id", f"chunk_{idx}"),
                content=doc.page_content
            )
            formatted_chunks.append(chunk_str)
            
        return "\n\n".join(formatted_chunks)

    def build_history_string(self, history: List[Tuple[str, str]]) -> str:
        """Formats previous Q&A turns into a single text string."""
        if not history:
            return "No previous conversation history."
            
        formatted_turns = []
        for q, a in history:
            formatted_turns.append(f"Farmer: {q}\nPlant Doctor: {a}")
            
        return "\n\n".join(formatted_turns)

    def build_prompts(
        self, 
        query: str, 
        docs: List[Document], 
        history: List[Tuple[str, str]]
    ) -> Tuple[str, str]:
        """
        Builds the system prompt and user prompt ready to send to the LLM.
        """
        context_str = self.build_context_string(docs)
        history_str = self.build_history_string(history)
        
        user_prompt = self.user_template.format(
            history=history_str,
            context=context_str,
            question=query
        )
        
        return self.system_template, user_prompt
