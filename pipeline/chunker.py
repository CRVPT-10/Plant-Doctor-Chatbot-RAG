from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from utils.config import config
from utils.logger import get_logger

logger = get_logger("chunker")

class DocumentChunker:
    """Chunks LangChain Documents using configurable text splitter settings."""
    
    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        self.chunk_size = chunk_size or config.get("chunker.chunk_size", 1000)
        self.chunk_overlap = chunk_overlap or config.get("chunker.chunk_overlap", 200)
        
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            is_separator_regex=False
        )

    def chunk_document(self, doc: Document) -> List[Document]:
        """Splits a single Document into a list of chunked Document objects with unique chunk IDs."""
        if not doc.page_content.strip():
            return []
            
        chunks = self.splitter.split_documents([doc])
        chunked_docs = []
        
        # Add metadata and unique ID to each chunk
        for idx, chunk in enumerate(chunks):
            doc_id = chunk.metadata.get("doc_id", "unknown_doc")
            page = chunk.metadata.get("page", 1)
            chunk_id = f"{doc_id}_p{page}_c{idx}"
            
            # Make sure we don't mutate original metadata but keep it clean
            new_metadata = chunk.metadata.copy()
            new_metadata.update({
                "chunk_id": chunk_id,
                "chunk_index": idx,
                "parent_id": doc_id,
            })
            
            chunked_docs.append(Document(
                page_content=chunk.page_content,
                metadata=new_metadata
            ))
            
        return chunked_docs

    def chunk_documents(self, docs: List[Document]) -> List[Document]:
        """Splits multiple Documents into chunks."""
        all_chunks = []
        for doc in docs:
            all_chunks.extend(self.chunk_document(doc))
        logger.info(f"Split {len(docs)} document pages into {len(all_chunks)} chunks.")
        return all_chunks
