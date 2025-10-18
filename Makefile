# ----------- FrontShiftAI Makefile -----------


# Run full DVC pipeline
repro:
	dvc repro

# Run specific scripts
run:
	python scripts/run_pipeline.py

# Run LLaMA RAG test
rag:
	python scripts/test_rag_llama.py

est:
	pytest -v tests/

validate:
    python scripts/validate_data.py

report:
	python scripts/validate_data.py > data_pipeline/logs/validation_report.csv

# Clean up cache/logs
clean:
	rm -rf data_pipeline/logs/*.log
	rm -rf **/__pycache__ .pytest_cache


"""
make init
make run
make test
make clean
make rag
make report
"""







