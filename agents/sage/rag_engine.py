import chromadb
import os


class RAGEngine:
    def __init__(self):
        host = os.getenv("CHROMA_HOST", "localhost")
        port = int(os.getenv("CHROMA_PORT", 8000))
        self.client = chromadb.HttpClient(host=host, port=port)
        try:
            self.collection = self.client.get_collection("product_docs")
        except Exception:
            self.collection = self.client.create_collection("product_docs")

    def search(self, query: str, n_results: int = 3):
        results = self.collection.query(query_texts=[query], n_results=n_results)
        return results

    def add_documents(self, docs: list, ids: list):
        self.collection.add(documents=docs, ids=ids)
