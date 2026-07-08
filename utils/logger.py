import os
import logging
from logging.handlers import RotatingFileHandler

# Define workspace directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "logs")

# Ensure logs directory exists
os.makedirs(LOG_DIR, exist_ok=True)

# Formatter definitions
standard_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
retrieval_formatter = logging.Formatter(
    "%(asctime)s | %(message)s"
)

# App Logger Setup
app_logger = logging.getLogger("plant_doctor_app")
app_logger.setLevel(logging.INFO)

# Avoid adding duplicate handlers if re-imported
if not app_logger.handlers:
    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(standard_formatter)
    app_logger.addHandler(console_handler)
    
    # File Handler
    app_file_path = os.path.join(LOG_DIR, "app.log")
    app_file_handler = RotatingFileHandler(
        app_file_path, maxBytes=10*1024*1024, backupCount=5, encoding="utf-8"
    )
    app_file_handler.setFormatter(standard_formatter)
    app_logger.addHandler(app_file_handler)

# Retrieval Logger Setup
retrieval_logger = logging.getLogger("plant_doctor_retrieval")
retrieval_logger.setLevel(logging.INFO)

if not retrieval_logger.handlers:
    # Retrieval File Handler
    retrieval_file_path = os.path.join(LOG_DIR, "retrieval.log")
    retrieval_file_handler = RotatingFileHandler(
        retrieval_file_path, maxBytes=10*1024*1024, backupCount=5, encoding="utf-8"
    )
    retrieval_file_handler.setFormatter(retrieval_formatter)
    retrieval_logger.addHandler(retrieval_file_handler)

def get_logger(name: str = "app") -> logging.Logger:
    """Returns the app logger."""
    return app_logger

def log_retrieval(query: str, retrieved_docs: list, reranked_docs: list, metrics: dict):
    """
    Log query, chunks, scores, and latency info to retrieval.log.
    """
    log_msg = f"QUERY: {query}\n"
    log_msg += "RETRIEVED CHUNKS:\n"
    for idx, doc in enumerate(retrieved_docs):
        meta = doc.metadata
        log_msg += f"  [{idx}] Doc: {meta.get('source', 'Unknown')}, Page: {meta.get('page', 'N/A')}, Score (original): {meta.get('score', 0.0):.4f}, Content Preview: {doc.page_content[:100]}...\n"
    
    log_msg += "RERANKED CHUNKS:\n"
    for idx, doc in enumerate(reranked_docs):
        meta = doc.metadata
        log_msg += f"  [{idx}] Doc: {meta.get('source', 'Unknown')}, Page: {meta.get('page', 'N/A')}, Rerank Score: {meta.get('rerank_score', 0.0):.4f}, Content Preview: {doc.page_content[:100]}...\n"
    
    log_msg += f"METRICS: {metrics}\n"
    log_msg += "-" * 80
    retrieval_logger.info(log_msg)
