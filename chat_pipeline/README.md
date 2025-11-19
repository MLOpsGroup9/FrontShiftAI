# Chat Pipeline

This package implements two things:
- A retrieval-augmented generation (RAG) service: fetch context from a vector store, build a prompt, and call an LLM backend.
- An evaluation harness: generate test questions, run the pipeline, judge answers, and aggregate metrics and bias slices.

## What lives where
- `rag/`: RAG pipeline entrypoint (`pipeline.py`), retriever/reranker, generator backends, prompt templates, config helpers.
- `configs/`: Runtime configuration (`rag.yaml`), experiment configs (`experiments/`), seed question definitions (`test_set.yaml`).
- `evaluation/`: Question generation, judge client, evaluation runner, artifacts written under `results/`.
- `tracking/`: W&B helpers and the model registry writer (metadata-only).
- `utils/`: Logging setup and email notifier.
- `results/`: Default output location for eval runs (examples.json, summary.json, bias_report.json).

## How to run
- Smoke run (small set, mocked/tiny fixtures): `python -m chat_pipeline.cli --config chat_pipeline/configs/experiments/quick_smoke.yaml`
- Full evaluation: `python -m chat_pipeline.cli --config chat_pipeline/configs/experiments/full_eval.yaml`
- Direct RAG call (ad hoc): `python -m chat_pipeline.rag.pipeline --question "..." --company "..."` (see `pipeline.py` for flags).

## Backends and config precedence
- Generation backend comes from `GENERATION_BACKEND` in the environment; it overrides `rag.yaml` and any experiment overrides. Supported values: `local`, `hf`, `mercury`, `auto`.
- Retrieval, reranking, prompt choices, and caches are configured in `configs/rag.yaml`.
- Eval-specific knobs (datasets, outputs, slice fields, overrides) live in `configs/experiments/*.yaml`.

## Artifacts produced
- Per-run consolidated examples: `results/<run_label>/examples.json` with question, metadata, contexts, answer, metrics.
- Aggregates: `results/<run_label>/summary.json` and `results/<run_label>/bias_report.json`.
- Experiment-level summary: `results/experiment_summary.json` (path can be set per experiment config).

## Environment essentials
- Set tokens/keys for the backends you use (OpenAI, HF, Mercury) in `.env`.
- For local LLaMA via llama-cpp, ensure your build has GPU support if you set `LLAMA_N_GPU_LAYERS=-1`.

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
