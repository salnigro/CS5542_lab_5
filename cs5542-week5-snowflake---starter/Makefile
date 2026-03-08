.PHONY: install test reproduce clean

install:
	pip install -r requirements.txt

test:
	pytest tests/test_faiss_smoke.py -v

reproduce:
	python scripts/run_faiss_repro.py

clean:
	rm -f retrieval/index.faiss
	rm -f retrieval/metadata.pkl
	rm -f logs/*.log
	rm -rf __pycache__
	rm -rf scripts/__pycache__
	rm -rf tests/__pycache__
	rm -rf .pytest_cache
