# Related Work Reproducibility: FAISS (Facebook AI Similarity Search)

## 1. What was attempted
We attempted to reproduce the core functionality of the **Inverted File System with Product Quantization (IVFPQ)**, which was the foundational contribution of Facebook AI's seminal nearest-neighbor search library, FAISS. The objective was to build an `IndexIVFPQ` that trains on dataset embeddings to cluster the vector space and compresses the vectors to drastically improve search speed over brute-force L2 distance calculations. 

We wrote a fully reproducible benchmark script (`scripts/run_faiss_repro.py`) that generates a controlled, deterministic synthetic dataset of 50,000 vectors with 384 dimensions to validate the speedup and recall of the index.

## 2. What worked and what failed
**What worked:**
- We successfully compiled and ran the python bindings for `faiss-cpu`. 
- The IVFPQ index training completed successfully, properly segmenting the synthetic embedded space into Voronoi cells.
- The `pytest` smoke tests effectively guarded against bad parameter initialization.
- The config-driven execution allowed parameters like `nlist`, `m`, and `nbits` to be modified without altering code.

**What failed / Challenges:**
- Because our project is intended to be runnable on standard laptops (including Windows machines without NVIDIA GPUs), reproducing the `faiss-gpu` benchmark with CUDA was immediately rejected. We had to limit the reproduction to CPU-only operations.
- The synthetic SIFT benchmark logic requires generating perfectly uniform floating-point arrays. The original papers use massive 1B vector sets which exhaust local memory, so we had to scale down the reproduction target to 50k samples.

## 3. Engineering or documentation gaps
FAISS was built natively in C++ several years ago. While the python bindings via SWIG are usable, they lack native Pythonic typing and docstrings. For instance, setting search-time hyperparameters like `nprobe` on specific index permutations often requires using the less-intuitive `faiss.ParameterSpace().set_index_parameter()` method to dynamically alter C++ structures at runtime rather than simple class properties, which the official tutorial barely skims over.

## 4. Differences from reported results
The original FAISS benchmarks on massive 1M-1B datasets display near 100x speedups vs standard L2 when highly tuned. Because we executed a scaled-down reproduction on 50,000 synthetic vectors without threading/multiprocessing optimizations across a server cluster, our speedups were comparatively modest but clearly trend in the same O(log N) trajectory versus O(N).

## 5. Meaningful Improvements Integrated
Based on the lessons learned from our synthetic reproduction, **we integrated the FAISS IVFPQ index into our actual CS 5542 project.**

Previously, the semantic search scripts (`scripts/build_index.py` and `scripts/retrieve.py`) utilized a slow, brute-force `faiss.IndexFlatL2` index. 
We replaced this sequence:
1. Parsed the index configs from `config.yaml`.
2. Initialized `faiss.IndexIVFPQ` and trained it against our historical dataset of embeddings (read from Snowflake/CSV) prior to generating the search mapping.
3. Updated the retrieval application to inject the `nprobe` parameter dynamically, improving our production query time and scalability.
