# Chat Pipeline (RAG + Evaluation)

This package owns the retrieval-augmented generation pipeline and the evaluation harness used for smoke tests and full runs.

## Layout
- `rag/` – RAG pipeline (`pipeline.py`), generator backends, retriever/reranker, prompt templates, and config helpers.
- `configs/` – Runtime configs: `rag.yaml`, experiment configs (`experiments/quick_smoke.yaml`, `experiments/full_eval.yaml`), and seed data definitions (`test_set.yaml`).
- `evaluation/` – Test question generation, LLM-as-a-judge scoring, evaluation runner, and artifacts (examples, summaries, bias reports).
- `utils/` – Logging and notification helpers.
- `tracking/` – W&B logging helpers and a simple local model registry (`models_registry/`).
- `results/` – Default destination for evaluation artifacts (per-example JSON, summaries, bias reports, tuning runs).

## Running the pipeline
- **Smoke test:** `python -m chat_pipeline.cli --config chat_pipeline/configs/experiments/quick_smoke.yaml`
- **Full eval:** `python -m chat_pipeline.cli --config chat_pipeline/configs/experiments/full_eval.yaml`
- The RAG stack can also be driven directly via `chat_pipeline/rag/pipeline.py` if you need ad-hoc queries.

## Configuration and backends
- The generation backend comes from `GENERATION_BACKEND` in `.env`; it overrides `configs/rag.yaml` and experiment overrides (`local`, `hf`, `mercury`, or `auto`).
- Retrieval, reranking, and prompt options live in `configs/rag.yaml`.
- Experiment-specific knobs (which dataset, output paths, slice fields) live in `configs/experiments/*.yaml`.

## Outputs
- Per-example results: `results/<run_label>/example_XXXX.json` (includes question, metadata, contexts, answer, and metrics).
- Aggregates: `summary.json` and `bias_report.json` inside each run directory.
- Top-level experiment summary: `results/experiment_summary.json` (path configurable per experiment config).

## Notes
- Hugging Face and Mercury backends require tokens/keys in `.env`.
- Local LLaMA relies on `llama-cpp-python`; set `LLAMA_N_GPU_LAYERS` (e.g., `-1` for full offload) if your build has GPU support.

## Sample `.env`
```
# Generation
GENERATION_BACKEND=local          # options: local | hf | mercury | auto
LLAMA_MODEL_PATH=chat_pipeline/models/Llama-3.2-3B-Instruct-Q4_K_M.gguf
LLAMA_N_GPU_LAYERS=-1             # -1 = full offload if built with GPU
HF_MODEL_NAME=Qwen/Qwen2.5-1.5B-Instruct
HF_API_TOKEN=your_hf_token
INCEPTION_API_KEY=your_mercury_key
INCEPTION_API_BASE=https://api.inceptionlabs.ai/v1/chat/completions
MERCURY_MODEL=mercury

# Judge backends
OPENAI_API_KEY=your_openai_key
JUDGE_MODEL=Qwen/Qwen2.5-3B-Instruct

# Vector store
CHROMA_DIR=data_pipeline/data/vector_db
CHROMA_COLLECTION=frontshift_handbooks

# Logging / tracking
LOG_LEVEL=INFO
CHAT_PIPELINE_LOG_DIR=logs
WANDB_API_KEY=your_wandb_key
WANDB_PROJECT=FrontShiftAI
WANDB_ENTITY=your_wandb_entity

# Notifications
EMAIL_SENDER=alert@example.com
EMAIL_PASSWORD=your_app_password
EMAIL_RECEIVER=alerts@example.com

TOKENIZERS_PARALLELISM=false
PYTHONPATH=/abs/path/to/Final_Project
```
