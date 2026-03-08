import faiss
import numpy as np
import yaml
import time
import json
import logging
import os

# Ensure directories exist
os.makedirs("logs", exist_ok=True)
os.makedirs("artifacts", exist_ok=True)

# Setup logging
logging.basicConfig(
    filename="logs/faiss_run.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger("").addHandler(console)

def load_config():
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)["faiss"]

def generate_synthetic_data(num_samples, dimension, seed):
    np.random.seed(seed)
    # Generate vectors and normalize them for inner-product/cosine similarity equivalents or L2
    vectors = np.random.random((num_samples, dimension)).astype("float32")
    return vectors

def main():
    logging.info("Starting FAISS reproducibility test...")
    config = load_config()
    dimension = config["dimension"]
    seed = config["seed"]
    
    # Dataset Generation
    n_train = 50000
    n_query = 100
    logging.info(f"Generating synthetic dataset: {n_train} training samples, {n_query} queries (dim={dimension}).")
    xb = generate_synthetic_data(n_train, dimension, seed)
    xq = generate_synthetic_data(n_query, dimension, seed + 1) # slightly different seed for queries

    # Build Brute-Force Baseline (IndexFlatL2)
    logging.info("Building IndexFlatL2 (Brute Force baseline)...")
    baseline_index = faiss.IndexFlatL2(dimension)
    baseline_index.add(xb)
    
    # Query baseline
    k = 5
    start_time = time.time()
    _, baseline_I = baseline_index.search(xq, k)
    baseline_time = time.time() - start_time
    logging.info(f"Baseline search completed in {baseline_time:.4f} seconds.")

    # Build IVFPQ Index
    nlist = config["nlist"]
    m = config["m"]
    nbits = config["nbits"]
    
    logging.info(f"Building IndexIVFPQ (nlist={nlist}, m={m}, nbits={nbits})...")
    quantizer = faiss.IndexFlatL2(dimension)
    index_ivfpq = faiss.IndexIVFPQ(quantizer, dimension, nlist, m, nbits)
    
    start_time = time.time()
    index_ivfpq.train(xb)
    train_time = time.time() - start_time
    logging.info(f"IVFPQ training completed in {train_time:.4f} seconds.")
    
    index_ivfpq.add(xb)
    index_ivfpq.nprobe = config["nprobe"]
    
    # Query IVFPQ
    start_time = time.time()
    _, ivfpq_I = index_ivfpq.search(xq, k)
    ivfpq_time = time.time() - start_time
    logging.info(f"IVFPQ search completed in {ivfpq_time:.4f} seconds with nprobe={config['nprobe']}.")

    # Calculate Recall@k
    matches = 0
    for i in range(n_query):
        # Intersection of results
        matches += len(set(baseline_I[i]).intersection(set(ivfpq_I[i])))
    
    recall = matches / (n_query * k)
    speedup = baseline_time / ivfpq_time if ivfpq_time > 0 else 0
    
    logging.info(f"Recall@{k}: {recall:.4f}")
    logging.info(f"Speedup vs Baseline: {speedup:.2f}x")

    # Export results to artifact
    metrics = {
        "dataset_size": n_train,
        "dimension": dimension,
        "ivfpq_params": {
            "nlist": nlist, "m": m, "nbits": nbits, "nprobe": config["nprobe"]
        },
        "metrics": {
            "recall": float(recall),
            "baseline_search_time_sec": float(baseline_time),
            "ivfpq_train_time_sec": float(train_time),
            "ivfpq_search_time_sec": float(ivfpq_time),
            "speedup": float(speedup)
        }
    }

    with open("artifacts/metrics.json", "w") as f:
        json.dump(metrics, f, indent=4)
    logging.info("Metrics successfully saved to artifacts/metrics.json")

if __name__ == "__main__":
    main()
