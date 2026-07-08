import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.retriever import AgriculturalRetriever

def main():
    retriever = AgriculturalRetriever()
    query = "How do we treat the disease that tomato crop suffers from?"
    
    print(f"Query: {query}")
    print("\n--- RETRIEVING TOP 15 CANDIDATES ---")
    results = retriever.retrieve(query, top_k_override=15)
    for idx, doc in enumerate(results):
        print(f"[{idx}] Source: {doc.metadata.get('source')} | Score: {doc.metadata.get('score')} | Content: {doc.page_content}")

if __name__ == "__main__":
    main()
