import os
import argparse
from utils.config import config
from utils.logger import get_logger
from pipeline.document_loader import DocumentLoader
from pipeline.chunker import DocumentChunker
from pipeline.embedder import CachedEmbeddings
from pipeline.vector_store import VectorStoreManager

logger = get_logger("ingestion")

def ingest_directory(directory_path: str = None, force_rebuild: bool = False):
    """
    Ingests all supported documents in a directory.
    Skips already indexed documents unless force_rebuild is True.
    """
    dir_to_ingest = directory_path or config.get_absolute_path("paths.documents_dir")
    logger.info(f"Starting ingestion process. Directory: {dir_to_ingest}, Force Rebuild: {force_rebuild}")
    
    # Ensure source directory exists
    os.makedirs(dir_to_ingest, exist_ok=True)
    
    # Initialize embedder and vector store manager
    embeddings = CachedEmbeddings()
    vector_store = VectorStoreManager(embeddings=embeddings)
    
    if force_rebuild:
        logger.info("Force rebuild requested. Clearing vector store...")
        vector_store.clear_all()
        
    chunker = DocumentChunker()
    
    # List all files in the directory
    supported_extensions = {".pdf", ".docx", ".txt", ".md"}
    files_to_process = []
    for root, _, filenames in os.walk(dir_to_ingest):
        for fname in filenames:
            ext = os.path.splitext(fname)[1].lower()
            if ext in supported_extensions:
                files_to_process.append(os.path.join(root, fname))
                
    if not files_to_process:
        logger.info("No documents found in directory to process.")
        return
        
    logger.info(f"Found {len(files_to_process)} document(s) in documents directory.")
    
    new_chunks = []
    processed_count = 0
    skipped_count = 0
    
    for filepath in files_to_process:
        doc_id = os.path.basename(filepath)
        
        # Check if already indexed
        if not force_rebuild and vector_store.is_document_indexed(doc_id):
            logger.info(f"Document {doc_id} is already indexed. Skipping.")
            skipped_count += 1
            continue
            
        logger.info(f"Processing: {filepath}")
        try:
            # Load
            docs = DocumentLoader.load_file(filepath)
            if not docs:
                logger.warning(f"No content extracted from {filepath}. Skipping.")
                continue
                
            # Chunk
            chunks = chunker.chunk_documents(docs)
            new_chunks.extend(chunks)
            processed_count += 1
        except Exception as e:
            logger.error(f"Failed to process document {filepath}: {e}")
            
    if new_chunks:
        logger.info(f"Indexing {len(new_chunks)} chunks in total...")
        vector_store.add_documents(new_chunks)
        logger.info(f"Successfully processed {processed_count} document(s). Indexed {len(new_chunks)} chunks.")
    else:
        logger.info("No new document chunks to index.")
        
    logger.info(f"Ingestion process finished. Processed: {processed_count}, Skipped: {skipped_count}.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest agricultural documents into the vector database.")
    parser.add_argument("--dir", type=str, help="Directory containing source documents.")
    parser.add_argument("--rebuild", action="store_true", help="Force rebuild/clear the vector database before ingesting.")
    args = parser.parse_args()
    
    ingest_directory(directory_path=args.dir, force_rebuild=args.rebuild)
