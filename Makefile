# ----------- FrontShiftAI Makefile -----------

# Variables
PYTHON := python
PIPELINE_DIR := data_pipeline/scripts
LOG_DIR := data_pipeline/logs
DATA_DIR := data_pipeline/data

# Default target
.DEFAULT_GOAL := help

.PHONY: repro run rag test validate report clean init help

# -------------------------------------------------------------------
# 📦 DVC + Pipeline Commands
# -------------------------------------------------------------------

## Reproduce full DVC pipeline (download → parse → preprocess → chunk → validate → embed)
repro:
	dvc repro

## Run the entire pipeline manually (without DVC)
run:
	$(PYTHON) $(PIPELINE_DIR)/run_pipeline.py

## Run data validation manually
validate:
	$(PYTHON) $(PIPELINE_DIR)/validate_data.py

## Generate validation report CSV and JSON
report:
	$(PYTHON) $(PIPELINE_DIR)/validate_data.py --report
	@echo "✅ Validation reports generated in $(DATA_DIR)/validated/reports/"

# -------------------------------------------------------------------
# 🧠 RAG / Model Tests
# -------------------------------------------------------------------

## Run LLaMA or RAG pipeline test
rag:
	$(PYTHON) $(PIPELINE_DIR)/test_rag_llama.py

# -------------------------------------------------------------------
# 🧪 Testing
# -------------------------------------------------------------------

## Run all unit and integration tests
test:
	pytest tests -v --maxfail=1 --disable-warnings

# -------------------------------------------------------------------
# 🧹 Cleanup
# -------------------------------------------------------------------

## Clean logs, cache, and temporary files
clean:
	@echo "🧹 Cleaning up logs and caches..."
	rm -rf $(LOG_DIR)/*.log
	rm -rf **/__pycache__ .pytest_cache
	rm -rf $(DATA_DIR)/vector_db/*.chroma*
	@echo "✅ Cleanup complete."

# -------------------------------------------------------------------
# ⚙️ Environment Setup
# -------------------------------------------------------------------

## Initialize or update Python environment
init:
	@echo "📦 Setting up environment..."
	pip install -r requirements.txt
	@echo "✅ Environment ready."

# -------------------------------------------------------------------
# 🆘 Help
# -------------------------------------------------------------------

help:
	@echo ""
	@echo "🚀 FrontShiftAI Makefile Commands"
	@echo "-----------------------------------------"
	@grep -E '^##' Makefile | sed 's/## //'
	@echo ""
