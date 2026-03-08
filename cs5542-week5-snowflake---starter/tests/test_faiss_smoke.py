import pytest
import faiss
import numpy as np
import yaml
import os

def load_test_config():
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)["faiss"]

def test_faiss_ivfpq_smoke():
    """
    A quick smoke test to verify FAISS is installed properly,
    can initialize an IVFPQ index, train it, and run a search
    without crashing.
    """
    config = load_test_config()
    d = config["dimension"]
    
    # We must have enough points to fill out the clusters
    # nlist in test config is 10, so we need at least 390 samples for faiss training
    # generally n_samples >= nlist * 39
    num_samples = max(500, config["nlist"] * 40) 
    
    np.random.seed(config["seed"])
    xb = np.random.random((num_samples, d)).astype("float32")
    xq = np.random.random((2, d)).astype("float32")
    
    quantizer = faiss.IndexFlatL2(d)
    index = faiss.IndexIVFPQ(quantizer, d, config["nlist"], config["m"], config["nbits"])
    
    # Train and add
    assert not index.is_trained
    index.train(xb)
    assert index.is_trained
    
    index.add(xb)
    assert index.ntotal == num_samples
    
    # Search
    k = 3
    index.nprobe = config["nprobe"]
    D, I = index.search(xq, k)
    
    # Assert output shapes
    assert I.shape == (2, k)
    assert D.shape == (2, k)
    
    # Assert distances are valid (not all NaNs/Infinity)
    assert not np.isnan(D).any()
    
def test_directory_structure():
    assert os.path.exists("config.yaml")
    assert os.path.exists("requirements.txt")
    assert os.path.exists("Makefile")
