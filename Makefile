# ----------- FrontShiftAI Makefile -----------

.PHONY: repro run rag test validate report clean init

# Run full DVC pipeline
repro:
	dvc repro

# Run full pipeline (extract → preprocess → validate → embed)
run:
	python scripts/run_pipeline.py

# Run LLaMA RAG test
rag:
	python scripts/test_rag_llama.py

# Run unit and integration tests
test:
	pytest -v --maxfail=1 --disable-warnings

# Validate processed data
validate:
	python scripts/validate_data.py

# Generate validation report CSV
report:
	python scripts/validate_data.py > data_pipeline/logs/validation_report.csv

# Clean up cache and logs
clean:
	rm -rf data_pipeline/logs/*.log
	rm -rf **/__pycache__ .pytest_cache

# (Optional) Initialize environment
# init:
# 	conda env create -f environment.yml || conda env update -f environment.yml
# 	pip install -r requirements.txt


# Usage:
# make repro      → Run DVC pipeline
# make run        → Run all stages via run_pipeline.py
# make test       → Run unit + integration tests
# make validate   → Validate final data outputs
# make clean      → Remove cache and logs
# make rag        → Run RAG LLaMA test
# make report     → Generate validation report CSV
