import re
import pandas as pd
from datasets import load_dataset

def clean_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"[^a-zA-Z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def chunk_text(text, chunk_size=300, overlap=50):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i+chunk_size])
        chunks.append(chunk)
    return chunks

def build_chunks():
    dataset = load_dataset("zeroshot/twitter-financial-news-sentiment")
    df = pd.DataFrame(dataset["train"])

    all_chunks = []
    seen = set()

    for _, row in df.iterrows():
        cleaned = clean_text(row["text"])

        # Filter short text
        if len(cleaned.split()) < 8:
            continue

        chunks = chunk_text(cleaned)

        for chunk in chunks:
            # Remove duplicates
            if chunk in seen:
                continue
            seen.add(chunk)

            all_chunks.append({
                "text": chunk,
                "label": row["label"]
            })

    pd.DataFrame(all_chunks).to_csv("retrieval/processed_text.csv", index=False)

if __name__ == "__main__":
    build_chunks()