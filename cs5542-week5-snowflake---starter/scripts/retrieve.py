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

        distances, indices = self.index.search(query_vec, k * 3)

        results = []
        seen_texts = set()

        for idx in indices[0]:
            text = self.metadata[idx]["text"]

            if text in seen_texts:
                continue

            seen_texts.add(text)
            results.append(self.metadata[idx])

            if len(results) >= k:
                break

        return results

if __name__ == "__main__":
    r = Retriever()
    results = r.search("financial market growth outlook")
    for res in results:
        print(res)