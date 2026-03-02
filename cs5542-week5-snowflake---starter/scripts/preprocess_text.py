import re
import pandas as pd
from datasets import load_dataset
import os


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
    all_chunks = []
    seen = set()

    dataset = load_dataset("zeroshot/twitter-financial-news-sentiment")
    df_news = pd.DataFrame(dataset["train"])

    for _, row in df_news.iterrows():
        cleaned = clean_text(row["text"])

        if len(cleaned.split()) < 8:
            continue

        if "heres what happened to the stock market" in cleaned:
            continue

        if cleaned in seen:
            continue
        seen.add(cleaned)

        all_chunks.append({
            "text": cleaned,
            "source": "financial_news"
        })


    retail_path = "data/online_retail_II.csv"

    if os.path.exists(retail_path):
        df_retail = pd.read_csv(retail_path)

        for _, row in df_retail.iterrows():
            description = str(row.get("Description", "")).lower()
            country = str(row.get("Country", ""))
            quantity = str(row.get("Quantity", ""))
            price = str(row.get("Price", ""))

            if len(description.split()) < 3:
                continue

            retail_text = (
                f"Product {description} sold in {country}. "
                f"Quantity {quantity}. Price {price}."
            )

            if retail_text in seen:
                continue
            seen.add(retail_text)

            all_chunks.append({
                "text": retail_text,
                "source": "online_retail"
            })
    olist_path = "data/olist_orders_dataset.csv"

    if os.path.exists(olist_path):
        df_olist = pd.read_csv(olist_path)

        for _, row in df_olist.iterrows():

            order_id = str(row.get("order_id", ""))
            customer_id = str(row.get("customer_id", ""))
            status = str(row.get("order_status", ""))
            purchase_date = str(row.get("order_purchase_timestamp", ""))
            delivered_date = str(row.get("order_delivered_customer_date", ""))
            estimated_date = str(row.get("order_estimated_delivery_date", ""))

            # Skip rows with missing important info
            if not order_id or not status:
                continue

            olist_text = (
                f"Order {order_id} placed by customer {customer_id}. "
                f"Status {status}. "
                f"Purchased on {purchase_date}. "
                f"Delivered on {delivered_date}. "
                f"Estimated delivery {estimated_date}."
            ).lower()

            if olist_text in seen:
                continue

            seen.add(olist_text)

            all_chunks.append({
                "text": olist_text,
                "source": "olist_orders"
            })
    

    pd.DataFrame(all_chunks).to_csv("retrieval/processed_text.csv", index=False)
    print(f"Total chunks created: {len(all_chunks)}")

if __name__ == "__main__":
    build_chunks()