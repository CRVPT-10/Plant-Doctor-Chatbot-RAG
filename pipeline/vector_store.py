import os
import sqlite3
from typing import List, Tuple, Dict, Any
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from pipeline.embedder import CachedEmbeddings
from utils.config import config
from utils.logger import get_logger

logger = get_logger("vector_store")

class VectorStoreManager:
    """
    Manages the FAISS index and the separate SQLite Metadata storage database.
    Supports incremental addition, deletion, and rebuilding.
    """
    def __init__(self, embeddings: CachedEmbeddings = None):
        self.embeddings = embeddings or CachedEmbeddings()
        self.faiss_dir = config.get_absolute_path("vector_store.index_path")
        self.db_path = config.get_absolute_path("vector_store.metadata_db")
        
        # Ensure directories exist
        os.makedirs(self.faiss_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        self._init_db()
        self.vector_store = self._load_vector_store()

    def _init_db(self):
        """Initialize metadata database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chunk_metadata (
                    chunk_id TEXT PRIMARY KEY,
                    doc_id TEXT,
                    source TEXT,
                    page INTEGER,
                    file_path TEXT,
                    language TEXT,
                    page_content TEXT
                )
            """)
            conn.commit()

    def _load_vector_store(self) -> FAISS:
        """Loads FAISS vector store from disk or creates a new empty one."""
        index_file = os.path.join(self.faiss_dir, "index.faiss")
        if os.path.exists(index_file):
            logger.info("Loading existing FAISS index...")
            try:
                # On Windows/Langchain, allow_dangerous_deserialization=True is required
                # since we trust our own saved index.
                return FAISS.load_local(
                    self.faiss_dir, 
                    self.embeddings, 
                    allow_dangerous_deserialization=True
                )
            except Exception as e:
                logger.error(f"Error loading FAISS index: {e}. Recreating empty index.")
        
        logger.info("FAISS index not found or failed to load. Creating empty index.")
        # Create an initial empty index. FAISS requires at least 1 document to initialize,
        # so we inject a placeholder and then remove it, or initialize with a small test doc.
        init_doc = Document(
            page_content="seed_document_for_init",
            metadata={"chunk_id": "seed", "doc_id": "seed", "source": "seed"}
        )
        vs = FAISS.from_documents([init_doc], self.embeddings)
        # Note: we don't save the seed to metadata db
        return vs

    def save(self):
        """Saves the FAISS index to disk."""
        self.vector_store.save_local(self.faiss_dir)
        logger.info(f"FAISS index saved to {self.faiss_dir}")

    def add_documents(self, chunks: List[Document]):
        """
        Incrementally adds chunked documents to FAISS and metadata DB.
        """
        if not chunks:
            return
            
        logger.info(f"Adding {len(chunks)} chunks to Vector Store.")
        
        # Prepare list for FAISS and lists for DB insertion
        faiss_docs = []
        db_entries = []
        
        for chunk in chunks:
            chunk_id = chunk.metadata.get("chunk_id")
            if not chunk_id:
                logger.warning(f"Chunk without ID detected. Skipping chunk: {chunk.page_content[:30]}")
                continue
                
            faiss_docs.append(chunk)
            db_entries.append((
                chunk_id,
                chunk.metadata.get("parent_id", "unknown_doc"),
                chunk.metadata.get("source", "unknown_source"),
                chunk.metadata.get("page", 1),
                chunk.metadata.get("file_path", ""),
                chunk.metadata.get("language", "en"),
                chunk.page_content
            ))
            
        if not faiss_docs:
            return

        # Add to FAISS. If empty index has 'seed' document, we replace or merge
        # Langchain FAISS handles adding documents cleanly.
        self.vector_store.add_documents(faiss_docs)
        
        # Add to separate SQLite metadata DB
        with sqlite3.connect(self.db_path) as conn:
            conn.executemany("""
                INSERT OR REPLACE INTO chunk_metadata 
                (chunk_id, doc_id, source, page, file_path, language, page_content)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, db_entries)
            conn.commit()
            
        # Persist index
        self.save()
        logger.info(f"Successfully indexed {len(faiss_docs)} chunks.")

    def delete_document(self, doc_id: str):
        """
        Deletes all chunks of a document by document ID.
        """
        logger.info(f"Deleting document {doc_id} from Vector Store.")
        
        # Find matching chunk IDs from Metadata database
        chunk_ids = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT chunk_id FROM chunk_metadata WHERE doc_id = ?", (doc_id,))
            chunk_ids = [row[0] for row in cursor.fetchall()]
            
        if not chunk_ids:
            logger.warning(f"No chunk metadata found for document: {doc_id}")
            return
            
        # Try to delete from FAISS using langchain's delete method.
        # Langchain FAISS class matches document IDs stored internally.
        # In langchain FAISS, the IDs inside vectorstore are not necessarily chunk_ids.
        # However, we can locate the internal docstore keys and delete them.
        try:
            # Look up internal IDs
            internal_ids = []
            for k, doc in self.vector_store.docstore._dict.items():
                if doc.metadata.get("doc_id") == doc_id or doc.metadata.get("parent_id") == doc_id:
                    internal_ids.append(k)
            
            if internal_ids:
                self.vector_store.delete(internal_ids)
                logger.info(f"Deleted {len(internal_ids)} chunks from FAISS index.")
            else:
                logger.warning("No internal index keys matched for deletion in FAISS.")
        except Exception as e:
            logger.error(f"Error deleting from FAISS index: {e}")
            
        # Delete from metadata DB
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM chunk_metadata WHERE doc_id = ?", (doc_id,))
            conn.commit()
            
        self.save()
        logger.info(f"Successfully deleted document {doc_id}.")

    def search_vectors(self, query: str, top_k: int = 5) -> List[Tuple[Document, float]]:
        """
        Search for top_k similar vectors and look up their details in the separate SQLite metadata database.
        Returns a list of tuples containing (Document, similarity_score).
        """
        # Search in FAISS
        # similarity_search_with_score returns list of tuples: (Document, float_score)
        # Note: FAISS score is typically L2 distance (lower is closer) or Cosine Similarity if normalized (higher is closer).
        # In langchain FAISS: similarity_search_with_score returns L2 distance.
        # If embeddings are normalized, cosine distance = 1 - cosine_similarity = L2^2 / 2
        # Let's map it to similarity score: similarity = 1 - (distance / 2) if normalized, or similar.
        raw_results = self.vector_store.similarity_search_with_score(query, k=top_k)
        
        results = []
        with sqlite3.connect(self.db_path) as conn:
            for doc, distance in raw_results:
                chunk_id = doc.metadata.get("chunk_id")
                if not chunk_id:
                    continue
                    
                # Look up separate metadata DB
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT source, page, file_path, language, page_content
                    FROM chunk_metadata WHERE chunk_id = ?
                """, (chunk_id,))
                row = cursor.fetchone()
                
                # Convert L2 distance to Cosine Similarity score: similarity = 1 - (distance / 2)
                # Ensure score bounds [0.0, 1.0]
                similarity_score = max(0.0, min(1.0, 1.0 - (float(distance) / 2.0)))
                
                if row:
                    source, page, file_path, language, page_content = row
                    metadata = {
                        "chunk_id": chunk_id,
                        "doc_id": doc.metadata.get("doc_id", source),
                        "source": source,
                        "page": page,
                        "file_path": file_path,
                        "language": language,
                        "score": similarity_score
                    }
                    ret_doc = Document(page_content=page_content, metadata=metadata)
                    results.append((ret_doc, similarity_score))
                else:
                    # Fallback to langchain document if sqlite row is missing (e.g. seed document)
                    if chunk_id == "seed":
                        continue
                    doc.metadata["score"] = similarity_score
                    results.append((doc, similarity_score))
                    
        return results

    def is_document_indexed(self, doc_id: str) -> bool:
        """Checks if a document ID already exists in the metadata DB."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM chunk_metadata WHERE doc_id = ? LIMIT 1", (doc_id,))
            return cursor.fetchone() is not None
            
    def get_all_indexed_documents(self) -> List[Dict[str, Any]]:
        """Returns metadata summary of all documents in the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT doc_id, source, language, COUNT(*) 
                FROM chunk_metadata 
                GROUP BY doc_id, source, language
            """)
            rows = cursor.fetchall()
            return [
                {"doc_id": r[0], "source": r[1], "language": r[2], "chunks_count": r[3]}
                for r in rows
            ]
            
    def clear_all(self):
        """Clears both FAISS index and metadata DB."""
        logger.info("Clearing all data from Vector Store and Metadata DB.")
        # Delete FAISS index files
        for f in ["index.faiss", "index.pkl"]:
            path = os.path.join(self.faiss_dir, f)
            if os.path.exists(path):
                os.remove(path)
                
        # Clear database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DROP TABLE IF EXISTS chunk_metadata")
            conn.commit()
            
        self._init_db()
        self.vector_store = self._load_vector_store()
        logger.info("Vector store reset complete.")
