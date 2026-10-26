import os
import time

try:
    import psutil
except ImportError:
    psutil = None

def print_memory(label):
    if psutil:
        process = psutil.Process(os.getpid())
        mem_mb = process.memory_info().rss / (1024 * 1024)
        print(f"[{label}] Memory usage: {mem_mb:.2f} MB")
    else:
        print(f"[{label}] psutil not installed")

print_memory("Before import")
from sentence_transformers import SentenceTransformer
print_memory("After import")

start_time = time.time()
model = SentenceTransformer("BAAI/bge-small-en-v1.5", cache_folder="models/embedding_models", device="cpu")
print_memory("After model load")
print(f"Model loaded in {time.time() - start_time:.2f}s")

start_time = time.time()
embedding = model.encode("what is the eligibility for raithu bhandu", normalize_embeddings=True)
print(f"Embedding generated in {time.time() - start_time:.2f}s")
print("Embedding size:", len(embedding))
