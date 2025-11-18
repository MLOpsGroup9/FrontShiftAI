# Configs

Configuration files that drive retrieval, generation, and evaluation.

## Key files
- `rag.yaml`: RAG defaults (retriever choice, top_k, reranker settings, prompt template key, LLM backend hint).
- `test_set.yaml`: Seed questions and sampling targets for generating evaluation datasets.
- `experiments/quick_smoke.yaml`: Small, capped run for sanity checks; writes results under `chat_pipeline/results/smoke_test_*`.
- `experiments/full_eval.yaml`: Full test-suite run; writes results under `chat_pipeline/results/eval_*` and `chat_pipeline/results/experiment_summary.json`.

## How overrides work
- `.env` can override generation backends and model paths (e.g., `GENERATION_BACKEND`, `LLAMA_MODEL_PATH`, `HF_MODEL_NAME`).
- Each experiment config can override parts of `rag.yaml` via `pipeline_overrides`.
- Output locations are defined per experiment (`summary_output`, `output_dir` for main/slices/tuning).
