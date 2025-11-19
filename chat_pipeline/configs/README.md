# Configurations

Central place for runtime knobs.

## Files
- `rag.yaml`: RAG defaults (retriever, reranker, prompt template, backend hint, batch sizes).
- `test_set.yaml`: Seed questions and sampling targets used by the question generator; carries slice/domain metadata.
- `experiments/quick_smoke.yaml`: Small evaluation run for CI; outputs under `chat_pipeline/results/smoke_test_*`.
- `experiments/full_eval.yaml`: Full evaluation run; outputs under `chat_pipeline/results/eval_*` and `chat_pipeline/results/experiment_summary.json`.

## Override order
1) Environment variables (e.g., `GENERATION_BACKEND`, `LLAMA_MODEL_PATH`, `HF_MODEL_NAME`, `CHROMA_DIR`).  
2) Experiment config `pipeline_overrides` in `experiments/*.yaml`.  
3) Base defaults in `rag.yaml`.

## Outputs
Each experiment config defines `summary_output` and `output_dir` for main/slices/tuning. Evaluation artifacts land under these paths; registry metadata is managed separately by the registry writer.***
