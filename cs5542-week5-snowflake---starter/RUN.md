# Run Instructions

This repository has been designed for deterministic, one-command reproducibility.

### Prerequisites
- Python 3.10+
- `pip` or `conda`

### 1. Re-create the Environment
All dependencies are strictly declared.
```bash
make install
```

### 2. Verify System State (Smoke Test)
Before running extensive tasks, prove the FAISS libraries and configs are valid:
```bash
make test
```

### 3. Run the FAISS Reproducibility Target
Execute the fully automated, config-driven benchmark. This will generate the dataset, train two indexes (L2 vs IVFPQ), evaluate them, and save outputs.
```bash
make reproduce
```

### Outputs Generated
- **`logs/faiss_run.log`**: Detailed timestamps and debug traces.
- **`artifacts/metrics.json`**: Structured report containing recall, speedups, and dimensions.

### Editing Hyperparameters
You can tweak the FAISS parameters (such as clusters, probes, bits, or seed) without changing any python scripts by editing the `config.yaml` file natively.
