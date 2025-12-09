# Chat Pipeline Guide

Welcome to the Chat Pipeline! This folder contains everything needed to take an employee handbook, retrieve the most relevant passages, ask an AI model to answer a question, and then double‑check that the answer is trustworthy. This document explains the system like a user manual so that anyone – even without a machine-learning background – can understand what is happening and how to run it.

---

## 1. Big Picture (The "Brain")

Think of the pipeline as three cooperating teams that simulate how a human expert would answer a question:

1.  **Librarian (RAG)** – Finds the right paragraphs from the knowledge base using the `rag/` logic.
2.  **Audit Team (Evaluation)** – Asks many test questions, grades every answer using an AI Judge (OpenAI), and generates report cards in `results/`.
3.  **Operations (Registry)** – Pushes successful "brains" (configurations) to a secure vault (`models_registry` on GCS) so the app always uses a safe, tested version.

---

## 2. How a Question Flows Through the System

1.  **Retrieval** – We look up relevant handbook passages from a Chroma vector database.
2.  **Optional reranking** – A smaller "judge" model reorders the passages so the most useful ones are at the top.
3.  **Answer drafting** – The system prompts the LLM (OpenAI, Mercury, or Llama) with the user's question + the retrieved handbook text.
4.  **Evaluation (The "Quality Gate")** – Before we let a new version go live, we run it against hundreds of test questions. An "AI Judge" grades the answers. If the score is > 3.0/5, we automatically "Promote" it to the registry.

## 2.5 Automated Rebuilds (New)

The backend now orchestrates full index rebuilds via Celery tasks when companies are added or removed. This process:
1.  Updates `url.json` with the latest company list.
2.  Runs the ingestion pipeline (`pipeline_runner.py`).
3.  Syncs the fresh vector store to GCS (`gsutil rsync`).
4.  Pods (on restart) pull the latest data from GCS.


---

## 3. Running the Pipeline

> All commands assume you are in the project root and have `PYTHONPATH` pointing to it (the workflows do this automatically).

### Quick smoke run
Runs a tiny question set with mocked services – perfect for CI or sanity checks.
```bash
python -m chat_pipeline.cli --config chat_pipeline/configs/experiments/quick_smoke.yaml
```

### Core or full evaluation
These use the real question sets and the configured backend.
```bash
# Core
python -m chat_pipeline.cli --config chat_pipeline/configs/experiments/core_eval.yaml

# Full
python -m chat_pipeline.cli --config chat_pipeline/configs/experiments/full_eval.yaml
```

### Self-hosted variants
When running on the Mac self-hosted runner we use the dedicated configs:
```bash
python -m chat_pipeline.cli --config chat_pipeline/configs/experiments/core_eval_self_hosted.yaml --mode generate
python -m chat_pipeline.cli --config chat_pipeline/configs/experiments/core_eval_self_hosted.yaml --mode judge
```
The same pattern applies to `full_eval_self_hosted.yaml`. The CLI can run `generate`, `judge`, or `full` (both phases back-to-back).

### Ad-hoc question answering
Need to ask a question directly?
```bash
python -m chat_pipeline.rag.pipeline --question "How do I request PTO?" --company "FrontShift"
```

---

## 4. Configuration Reference

### Environment variables (highest priority)

Set these in `.env` or the GitHub Actions secrets:

```
GENERATION_BACKEND=mercury        # local | hf | mercury | auto
LLAMA_MODEL_PATH=chat_pipeline/models/Llama-3.2-3B-Instruct-Q4_K_M.gguf
LLAMA_N_GPU_LAYERS=-1             # full GPU offload if supported
HF_MODEL_NAME=Qwen/Qwen2.5-1.5B-Instruct
HF_API_TOKEN=...
INCEPTION_API_KEY=...
INCEPTION_API_BASE=https://api.inceptionlabs.ai/v1
MERCURY_MODEL=mercury

OPENAI_API_KEY=...                # judge model
JUDGE_MODEL=Qwen/Qwen2.5-3B-Instruct

CHROMA_DIR=data_pipeline/data/vector_db
CHROMA_REMOTE_URI=gs://frontshiftai-data/data/vector_db
CHROMA_COLLECTION=frontshift_handbooks

MODEL_REGISTRY_DIR=models_registry          # or gs://bucket/path
MODEL_REGISTRY_CACHE=models_registry        # local staging folder for remote registries

WANDB_API_KEY=...
WANDB_PROJECT=FrontShiftAI
WANDB_ENTITY=group9mlops-northeastern-university

EMAIL_SENDER=alerts@example.com
EMAIL_PASSWORD=app_password
EMAIL_RECEIVER=ops@example.com

TOKENIZERS_PARALLELISM=false
PYTHONPATH=/abs/path/to/Final_Project
```

### Experiment configs (`chat_pipeline/configs/experiments/*.yaml`)

Each file defines:
- **logging** – Level and optional log directory.
- **wandb** – Project/entity/tags and whether logging is disabled.
- **execution_modes** – Choose `ray`, `multiprocessing`, or `sequential` per environment (CI vs local).
- **eval** – Question sources, output folders, slice fields, and overrides (e.g., use the local LLaMA backend).
- **tuning** – Optional small grid search with overrides for `top_k`, reranker settings, etc.

The general precedence is:
1. Environment variables.
2. Experiment `pipeline_overrides`.
3. Base defaults in `configs/rag.yaml`.

---

## 5. Outputs and Where to Find Them

After running any evaluation you will see the following structure under `chat_pipeline/results/`:

| File/Folder | Meaning |
| --- | --- |
| `*_main/examples.jsonl` | Every example with metadata, retrieved contexts, generated answer, judge scores, and latency. |
| `*_main/summary.json` | Overall averages (precision, recall, groundedness, etc.). |
| `*_slices/bias_report.json` | Slice-level averages so we can spot bias. Slice dimensions are driven by `slice_fields` in the config (default: `slice`). |
| `core_experiment_summary*.json` / `full_experiment_summary*.json` | Top-level dashboards summarizing the entire run. |
| `results/quality_gate.txt` | PASS/FAIL written by `tracking/compute_quality_gate.py`. |
| `models_registry/` | When a model passes the gate and we run `tracking/deploy_model.py`, a new version folder is created here with metadata, copied artifacts, and a `latest` pointer. |

Artifacts are uploaded to GitHub Actions in the workflows so other jobs (deploy, rollback, smoke tests) can consume them.

---

## 6. Common Tasks

### Run the quality gate locally
```
python -m chat_pipeline.tracking.compute_quality_gate
cat chat_pipeline/results/quality_gate.txt
```

### Promote a model after a good evaluation
```
python -m chat_pipeline.tracking.deploy_model \
  --model-name frontshift-rag \
  --model-path models/Llama-3.2-3B-Instruct-Q4_K_S.gguf
```
The script checks the gate result, copies the evaluation artifacts, writes `metadata.json`, and (if `MODEL_REGISTRY_DIR` points to a GCS bucket) syncs the registry automatically.

### Roll back to a prior version
```
python -m chat_pipeline.tracking.rollback_model --list-versions
python -m chat_pipeline.tracking.rollback_model --target-version v3 --reason "Regression in groundedness"
```

---

## 7. Glossary

- **RAG (Retrieval-Augmented Generation)** – A workflow where we retrieve relevant documents before answering a question, ensuring responses stay grounded in the source material.
- **Slices / bias report** – Groups of questions that share a property (e.g., “construction safety”). We average scores per slice to see whether the model performs poorly for a subset.
- **Groundedness** – Measures how closely the answer sticks to the provided context.
- **Answer relevance** – Checks whether the response actually answers the question.
- **Hallucination score** – Higher numbers mean the model invented facts not supported by the context.
- **Quality gate** – Simple PASS/FAIL logic that checks the latest run against thresholds before deployment.
- **Registry** – A lightweight folder structure (`models_registry/`) holding metadata for each promoted build. The workflows sync it to cloud storage so production can trust the “latest” pointer.

---

By following this guide you can explore, run, and troubleshoot every part of the chat pipeline. When in doubt, start by running the smoke test, inspect the results under `chat_pipeline/results/`, and review the logs on GitHub Actions. Everything else — model promotion, rollback, and deployment — builds on top of these same artifacts. Happy experimenting!
