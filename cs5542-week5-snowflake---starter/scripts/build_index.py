import faiss
import pickle
import pandas as pd
from sentence_transformers import SentenceTransformer
import numpy as np

MODEL_NAME = "all-MiniLM-L6-v2"

def build_index():
    df = pd.read_csv("retrieval/processed_text.csv")

    model = SentenceTransformer(MODEL_NAME)

    embeddings = model.encode(
        df["text"].tolist(),
        show_progress_bar=True
    )

    embeddings = np.array(embeddings).astype("float32")

    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)

    faiss.write_index(index, "retrieval/index.faiss")

    with open("retrieval/metadata.pkl", "wb") as f:
        pickle.dump(df.to_dict("records"), f)

    print("Index built successfully.")

if __name__ == "__main__":
    build_index()