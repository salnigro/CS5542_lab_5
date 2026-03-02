import faiss
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"

class Retriever:
    def __init__(self):
        self.model = SentenceTransformer(MODEL_NAME)
        self.index = faiss.read_index("retrieval/index.faiss")

        with open("retrieval/metadata.pkl", "rb") as f:
            self.metadata = pickle.load(f)

    def search(self, query, k=5):
        query_vec = self.model.encode([query]).astype("float32")

        distances, indices = self.index.search(query_vec, k)

        results = []

        for i, idx in enumerate(indices[0]):
            item = self.metadata[idx]

            results.append({
                "text": item["text"],
                "source": item.get("source", "unknown"),
                "score": float(distances[0][i])
            })

        return results
if __name__ == "__main__":
    r = Retriever()
    results = r.search("financial market growth outlook")
    for res in results:
        print(res)