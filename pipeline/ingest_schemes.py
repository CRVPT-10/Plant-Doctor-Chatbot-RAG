import os
import sys
import argparse

# Add parent directory to path to support imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config import config
from pipeline.embedder import CachedEmbeddings
from pipeline.vector_store import VectorStoreManager
from pipeline.ingest import ingest_directory

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest government schemes into the vector database.")
    parser.add_argument("--rebuild", action="store_true", help="Force rebuild/clear the schemes vector database.")
    args = parser.parse_args()
    
    govt_schemes_dir = config.get_absolute_path("paths.govt_schemes_documents_dir") or "data/govt_schemes/documents"
    govt_schemes_faiss_dir = config.get_absolute_path("paths.govt_schemes_faiss_index_dir") or "data/govt_schemes/faiss"
    govt_schemes_db_path = config.get_absolute_path("paths.govt_schemes_metadata_db") or "data/govt_schemes/metadata/metadata.db"
    
    # Ensure folders exist
    os.makedirs(govt_schemes_dir, exist_ok=True)
    os.makedirs(govt_schemes_faiss_dir, exist_ok=True)
    os.makedirs(os.path.dirname(govt_schemes_db_path), exist_ok=True)
    
    print(f"Initializing government schemes vector store at {govt_schemes_faiss_dir}...")
    embeddings = CachedEmbeddings()
    vector_store = VectorStoreManager(
        embeddings=embeddings,
        faiss_dir=govt_schemes_faiss_dir,
        db_path=govt_schemes_db_path
    )
    
    print(f"Ingesting documents from {govt_schemes_dir}...")
    ingest_directory(
        directory_path=govt_schemes_dir, 
        force_rebuild=args.rebuild, 
        vector_store=vector_store
    )
    print("Ingestion of government schemes completed!")
