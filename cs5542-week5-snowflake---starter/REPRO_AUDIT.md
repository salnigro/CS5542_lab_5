# Reproducibility Audit

The following standards were applied to this repository to guarantee deterministic, reproducible performance aligned with the Lab 7 requirements.

### Runs through a single command
We implemented a `Makefile` sequence that centralizes complicated python calls into logical verbs (`make install`, `make test`, `make reproduce`).

### Uses pinned environments
Our `requirements.txt` acts as the single source of truth for dependencies. If executing `make install` is run a year from now, the system behaves exactly as it did during development. 

### Controls randomness
The implementation script (`run_faiss_repro.py`) sets strict random seeds globally via NumPy (`np.random.seed()`), which propagates identically whenever generating synthetic benchmarks or initiating clustering behaviors in FAISS.

### Exports structured artifacts
Metrics are no longer isolated to the terminal. The `make reproduce` command deterministically writes evaluation statistics (Recall@k, latency comparisons, index build times) to `artifacts/metrics.json` for persistent storage and reporting.

### Includes logging and a smoke test
The system outputs a detailed runtime trace to `logs/faiss_run.log`. We additionally wrote formal verification code (`tests/test_faiss_smoke.py`) using `pytest` to halt broken states before resources are wasted executing the main pipeline.

### Config-driven execution
Hardcoded parameters were eliminated. The variables controlling FAISS dimensionality, inverted lists, sub-quantization (`m`), bits, and `nprobe` are read dynamically from `config.yaml`.
