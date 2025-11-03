
# FrontShiftAI – Machine Learning and Evaluation Pipeline (ML + CI/CD)

This README documents the Machine Learning pipeline, evaluation modules, experiment tracking, and CI/CD automation used in the FrontShiftAI project. It focuses on everything under `ml_pipeline/` and the model artifacts in `models/` and `models_registry/`. The data ingestion and preprocessing pipeline under `data_pipeline/` is intentionally excluded here because it is documented separately.

The material is written at a graduate student level and is intended to be both explanatory and operationally useful. It explains design choices, how each component works, and how they interact in continuous integration and deployment.

---

## Table of Contents

1. [Overview](#overview)  
2. [Directory Structure](#directory-structure)  
3. [Core Components](#core-components)  
   3.1. [RAG Retrieval Utilities](#rag-retrieval-utilities)  
   3.2. [Evaluation Modules](#evaluation-modules)  
   3.3. [Experiment Tracking](#experiment-tracking)  
   3.4. [Local Model Registry](#local-model-registry)  
   3.5. [Evaluation Pipeline Runner](#evaluation-pipeline-runner)  
4. [End to End Flow: ML Evaluation and Registry](#end-to-end-flow-ml-evaluation-and-registry)  
5. [CI and CD Workflows](#ci-and-cd-workflows)  
   5.1. [CI Job: Train and Validate](#ci-job-train-and-validate)  
   5.2. [CD Job: Deploy to Registry](#cd-job-deploy-to-registry)  
   5.3. [Notify Job: Email Summary](#notify-job-email-summary)  
6. [Workflow Diagrams](#workflow-diagrams)  
7. [Configuration and Environment](#configuration-and-environment)  
8. [Usage: Running Locally](#usage-running-locally)  
9. [Quality Gates and Rollback Strategy](#quality-gates-and-rollback-strategy)  
10. [Troubleshooting](#troubleshooting)  
11. [Change Log and Evolution](#change-log-and-evolution)  

---

## Overview

The Machine Learning pipeline in FrontShiftAI evaluates retrieval augmented generation models built to answer HR policy questions using company handbooks. The pipeline operates after vectorization and storage in ChromaDB and focuses on:
- Retrieval quality evaluation using semantic similarity and precision@k.
- Bias detection across different companies or document sources.
- Sensitivity testing to paraphrase variations.
- Unified metric aggregation and visualization.
- Experiment tracking with Weights and Biases.
- Model export and local model registry versioning.
- CI and CD automation to ensure correctness on each push to `main` and to continuously publish new versions of evaluated models.

No emojis are used and no em dashes are used. All descriptions are technical and concise while retaining necessary depth.

---

## Directory Structure

```
ml_pipeline/
│
├── evaluation/                  # Evaluation scripts for RAG models
│   ├── rag_eval_metrics.py      # Computes semantic similarity and precision@k, exports model file
│   ├── bias_detection.py        # Measures inter company bias in model performance
│   ├── sensitivity_analysis.py  # Evaluates robustness to paraphrased queries
│   ├── unified_eval_summary.py  # Aggregates all metrics and logs to W&B
│   └── eval_results/            # Stores CSV, JSON, and plots
│
├── rag/
│   └── rag_query_utils.py       # Handles context retrieval from ChromaDB
│
├── tracking/
│   ├── exp_tracking.py          # W&B integration for experiment tracking
│   └── push_to_registry.py      # Local model registry management and versioning
│
├── utils/
│   ├── logger.py                # Centralized logger utility for all pipeline modules
│   ├── email_notifier.py        # Local SMTP email tester for notifications
│   └── __init__.py
│
├── eval_pipeline_runner.py      # Orchestrates all evaluation stages
└── __init__.py
```

Other relevant top level folders for ML and CI/CD:
```
models/                 # Exported model artifacts (.gguf or other)
models_registry/        # Versioned registry: <model_name>_vX with metadata.json
.github/workflows/      # GitHub Actions CI and CD workflows
wandb/                  # Local W&B run caches created during local runs
```

---

## Core Components

### RAG Retrieval Utilities

File: `ml_pipeline/rag/rag_query_utils.py`

Responsibilities:
- Open a persistent ChromaDB client against `data_pipeline/data/vector_db`.
- Apply an embedding function (SentenceTransformer all MiniLM L6 v2).
- Provide `retrieve_context(query, company, top_k)` which issues similarity search with optional exact or fuzzy company filtering.
- Returns list of top documents and associated metadatas. Downstream evaluators rely on these fields to compute metrics and to record sources.

Design notes:
- Retrieval is decoupled from evaluation to allow flexible testing of different search parameters and models without modifying evaluation scripts.
- Company filter resolution is tolerant to slight name mismatches, falling back to global search when no match is found.

### Evaluation Modules

1. `rag_eval_metrics.py`  
   - For each query in a curated list, retrieves top k documents and computes:
     - Semantic similarity between query embedding and concatenated context embedding.
     - Precision at k proxy: 1.0 when non empty retrieval is achieved for the query.  
   - Writes `eval_results/rag_eval_results.csv`.  
   - Exports a model file to `models/` to simulate or perform a real training export.  
   - Pushes model and metrics into the local registry via `push_to_registry`.  
   - Logs metrics and artifacts to W&B using `exp_tracking.log_metrics`.

2. `bias_detection.py`  
   - Groups `rag_eval_results.csv` by company and computes mean similarity, mean precision, count, and a center gap metric relative to the overall mean.  
   - Produces `eval_results/bias_report.csv`.  
   - Logs summary metrics to W&B as a separate run.

3. `sensitivity_analysis.py`  
   - Selects a base query and a set of paraphrases and compares the cosine similarity between the contexts retrieved for base and each variant.  
   - Produces `eval_results/sensitivity_report.csv`.  
   - Logs the mean context similarity and the number of variants as W&B metrics.

4. `unified_eval_summary.py`  
   - Aggregates RAG, Bias, and Sensitivity outputs into `unified_summary.json` and `unified_summary.csv`.  
   - Optionally generates a bar chart `unified_summary_plot.png`.  
   - Logs the unified metrics and visualization to W&B.

All evaluation scripts use the centralized logger in `utils/logger.py`. Each script emits a structured log with timestamps and module names and writes to both console and `ml_pipeline/logs/`.

### Experiment Tracking

File: `ml_pipeline/tracking/exp_tracking.py`

- Thin wrapper around W&B `wandb.init` with stage name and model name standardized.  
- Logs scalar metrics, attaches produced CSV or JSON artifacts, and handles reinit to ensure independent stages are captured as separate runs.  
- The CI job sets `WANDB_API_KEY`, `WANDB_ENTITY`, and `WANDB_PROJECT` to route runs into the correct space. For local testing the user can export those variables and run the pipeline from the shell.

### Local Model Registry

File: `ml_pipeline/tracking/push_to_registry.py`

- Creates a versioned folder under `models_registry/` named `<model_name>_v<N>`.  
- Copies the exported model artifact from `models/` into the version directory.  
- Writes `metadata.json` with model name, version, timestamp, and key metrics (for example mean semantic similarity and mean precision at k).  
- Ensures reproducibility by storing both bits and metadata locked to a version. When integrated with CI and CD this allows repeatable promotion of models.

### Evaluation Pipeline Runner

File: `ml_pipeline/eval_pipeline_runner.py`

- Orchestrates evaluation stages sequentially and ensures the project root is on `sys.path` when executed from different working directories.  
- Runs the following in order:
  1. `rag_eval_metrics.py`  
  2. `bias_detection.py`  
  3. `sensitivity_analysis.py`  
  4. `unified_eval_summary.py`  
- Emits a success or failure line per stage and checks expected artifacts to verify outputs.  
- Intended to be the single entry point for both local runs and CI.

---

## End to End Flow: ML Evaluation and Registry

Monospace diagram that mirrors the runtime order and the side effects. These are the exact ASCII diagrams requested, preserved for easy reading.

```
                     ┌─────────────────────────────┐
                     │   ml_pipeline/eval_runner   │
                     └──────────────┬──────────────┘
                                    │
        ┌───────────────────────────┴──────────────────────────┐
        │                  Evaluation Stages                   │
        │──────────────────────────────────────────────────────│
        │ RAG Eval → Bias Eval → Sensitivity Eval → Unified    │
        └──────┬─────────────┬─────────────┬─────────────┬──────┘
               │             │             │             │
               ▼             ▼             ▼             ▼
        push_to_registry   log_metrics   log_metrics   log_metrics
               │                               │
               ▼                               ▼
     local model registry             W&B experiment logs
               │
               ▼
       ┌──────────────────────────────┐
       │ deploy job (CD)              │
       │ downloads artifacts,         │
       │ runs push_to_registry again  │
       └──────────────┬───────────────┘
                      │
                      ▼
             final model_registry/
```

Interpretation:
- The runner executes four evaluation stages.  
- The RAG stage both logs metrics and exports a model artifact, then calls `push_to_registry` initially.  
- Bias and Sensitivity stages focus on metrics and W&B logging.  
- Unified stage aggregates results for gating and reporting.  
- The CD job later reuses artifacts and pushes a final version into `models_registry/` inside the runner environment used by GitHub Actions.

---

## CI and CD Workflows

The project uses a single workflow file that defines three jobs: `train-validate`, `deploy`, and `notify`. The workflow begins on push to `main` or through manual dispatch from the Actions tab. The `deploy` job depends on the successful completion of `train-validate`. The `notify` job always runs and reports the statuses and metrics by email.

### CI Job: Train and Validate

Key steps:
1. Checkout with Git LFS enabled so large artifacts tracked by LFS can be pulled.  
2. Install Python 3.12 and dependencies from `requirements.txt`.  
3. Set environment variables for `PYTHONPATH` and tokenizer parallelism.  
4. Run `ml_pipeline/eval_pipeline_runner.py`, which produces the CSVs, JSONs, plot, and exports a model file to `models/`.  
5. Gate the pipeline using `unified_summary.json` by checking `rag.mean_semantic_sim` against a threshold. The default threshold is 0.45 for demonstration.  
6. Upload artifacts named `eval-results` which include both `ml_pipeline/evaluation/eval_results/` and `models/` so the next job can download them.

Notes:
- W&B logging runs during RAG, Bias, Sensitivity, and Unified stages.  
- The model export in RAG stage creates `models/Llama-3.2-3B-Instruct-Q4_K_S.gguf` in the CI environment. This can be replaced by a genuine model trainer that saves weights.

### CD Job: Deploy to Registry

Key steps:
1. Checkout again with Git LFS to ensure compatibility.  
2. Reinstall dependencies.  
3. Download the artifact bundle `eval-results` from the CI job.  
4. Verify that both the model file and the unified summary are present.  
5. Load metrics from the summary and call `push_to_registry` to create a new version under `models_registry/`.  
6. Upload the entire `models_registry/` as a GitHub Actions artifact for inspection or consumption by downstream stages.

Notes:
- If you choose to store the registry in remote object storage, replace the final upload step with the appropriate uploader for GCS or S3.  
- This project uses a local on repository registry directory by design for portability.

### Notify Job: Email Summary

Key steps:
1. Runs after both CI and CD complete.  
2. Downloads `eval-results` if available and tries to parse `unified_summary.json`.  
3. Sends a Gmail SMTP email including job results, key metrics, and a link to the run using secrets `EMAIL_SENDER`, `EMAIL_PASSWORD`, and `EMAIL_RECEIVER`.

---

## Workflow Diagrams

The second end to end diagram showing triggers, artifacts, and dependencies. This exactly matches the requested ASCII diagram.

```
                          ┌────────────────────────────┐
                          │        GitHub Repo          │
                          │  (FrontShiftAI - main)      │
                          └────────────┬────────────────┘
                                       │
                        ┌──────────────┴──────────────┐
                        │   GitHub Actions Trigger    │
                        │   (push to main / manual)   │
                        └──────────────┬──────────────┘
                                       │
                          ▼──────────────────────────▼
                 ┌─────────────────────────────────────────┐
                 │         CI JOB: Train & Validate         │
                 │─────────────────────────────────────────│
                 │ 1) Checkout repo with Git LFS           │
                 │ 2) Install Python + dependencies         │
                 │ 3) Run eval_pipeline_runner.py           │
                 │     ├─ RAG Evaluation                    │
                 │     ├─ Bias Detection                    │
                 │     ├─ Sensitivity Analysis              │
                 │     ├─ Unified Eval Summary              │
                 │ 4) Save metrics → unified_summary.json   │
                 │ 5) Export model → models/.gguf           │
                 │ 6) Log results → Weights & Biases        │
                 │ 7) Upload artifacts to GitHub (v4)       │
                 └─────────────────────────────────────────┘
                                       │
                                       ▼
                     ┌──────────────────────────────────────┐
                     │  Artifacts Uploaded (eval-results)   │
                     │  ├─ ml_pipeline/evaluation/results   │
                     │  └─ models/Llama-3B-Instruct.gguf    │
                     └──────────────────────────────────────┘
                                       │
                                       ▼
                 ┌─────────────────────────────────────────┐
                 │        CD JOB: Deploy to Registry        │
                 │─────────────────────────────────────────│
                 │ 1) Download eval-results artifact        │
                 │ 2) Verify model + summary exist          │
                 │ 3) Load metrics (semantic_sim, P@K)      │
                 │ 4) Push model to local registry          │
                 │ 5) Upload model_registry/ as artifact    │
                 └─────────────────────────────────────────┘
                                       │
                                       ▼
                   ┌─────────────────────────────────────────┐
                   │      Model Registry / Version Store      │
                   │─────────────────────────────────────────│
                   │ stores .gguf model files                 │
                   │ includes metadata + metrics.json         │
                   │ versioned under commit hash              │
                   └─────────────────────────────────────────┘
                                       │
                                       ▼
           ┌────────────────────────────────────────────────────┐
           │         NOTIFY JOB: Email Notification              │
           │────────────────────────────────────────────────────│
           │ 1) Runs after both CI + CD (always)               │
           │ 2) Collects statuses from both jobs               │
           │ 3) Reads metrics from unified_summary.json         │
           │ 4) Sends formatted Gmail SMTP message              │
           │     with pipeline summary + metrics                │
           │ 5) Links back to GitHub Actions run               │
           └────────────────────────────────────────────────────┘
```

---

## Configuration and Environment

Weights and Biases
```
export WANDB_ENTITY=group9mlops-northeastern-university
export WANDB_PROJECT=FrontShiftAI
wandb login
```

Email Notification (local tester)
- File: `ml_pipeline/utils/email_notifier.py` expects `ml_pipeline/utils/email_config.json` with
  ```json
  {
    "sender": "group9mlops@gmail.com",
    "password": "app_password_here",
    "receiver": "group9mlops@gmail.com"
  }
  ```
- Test locally:
  ```bash
  python -m ml_pipeline.utils.email_notifier
  ```

Git LFS
- `.gitattributes` tracks large binary model artifacts under `models/`:
  ```
  models/* filter=lfs diff=lfs merge=lfs -text
  ```
- Install and verify locally:
  ```bash
  git lfs install
  git lfs track "models/*"
  git add .gitattributes
  git commit -m "Enable Git LFS for model artifacts"
  ```

---

## Usage: Running Locally

Activate your environment and run the evaluation pipeline runner:
```bash
python ml_pipeline/eval_pipeline_runner.py
```

Outputs will be written under `ml_pipeline/evaluation/eval_results/`:
```
rag_eval_results.csv
bias_report.csv
sensitivity_report.csv
unified_summary.json
unified_summary.csv
unified_summary_plot.png
```

A model file will be exported to `models/` and also pushed to `models_registry/` with a versioned subfolder containing `metadata.json`.

---

## Quality Gates and Rollback Strategy

Quality Gate in CI:
- After the unified summary is produced, the CI workflow checks `rag.mean_semantic_sim` against a threshold. The default threshold is 0.45. If below the threshold the workflow fails and the deploy job is skipped.

Rollback Procedure:
- Because the model registry is versioned, it is straightforward to roll back to a previous version. You can:
  1. Inspect `models_registry/` to select the last known good version.
  2. Update the deployment consumer or serve script to point to that version.
  3. Optionally tag the version in the repository for traceability.

Future Enhancements:
- Store `models_registry/` in remote object storage with immutable versioning.  
- Introduce an explicit promotion gate controlled by a code owner review in a protected branch before CD runs.

---

## Troubleshooting

1. `ModuleNotFoundError: No module named 'ml_pipeline'`  
   - Ensure `PYTHONPATH` includes the project root. The CI pipeline sets this automatically. Locally, run from repo root or export `PYTHONPATH=$(pwd)`.

2. W&B 403 Permission Error  
   - Verify `WANDB_API_KEY` is set for the account that can write to the target entity and project. Locally, run `wandb login` and confirm the active entity and project. In CI, store the API key in GitHub Secrets.

3. Gmail SMTP timeouts or authentication failures  
   - Use an App Password for Gmail. Make sure `EMAIL_SENDER`, `EMAIL_PASSWORD`, and `EMAIL_RECEIVER` are present in Secrets for GitHub Actions and match your local test configuration.

4. Missing artifacts in CD step  
   - Ensure the CI job uploads a single artifact name (here `eval-results`) that includes both the `eval_results` directory and the `models` directory. The CD job must use the same artifact name with `actions/download-artifact@v4`.

5. Model file not found during CD  
   - Confirm that `rag_eval_metrics.py` exported the model file into `models/`. Verify that the Upload Artifacts step included `models/` and that in CD the artifact is downloaded to repository root.

---

## Change Log and Evolution

Key points in the evolution of this pipeline:
- Introduced centralized logging via `utils/logger.py` and created a dedicated `logs/` folder.
- Implemented evaluation scripts for RAG, Bias, and Sensitivity with explicit CSV outputs for reproducibility.
- Added `unified_eval_summary.py` to calculate aggregate metrics and produce a single JSON used as the CI quality gate.
- Integrated W&B logging in each stage. All metrics and artifacts are now visible in the W&B project dashboards.
- Built a local model registry and added a push to registry step inside evaluation and CD. Versioning follows `<model_name>_v<N>` with a `metadata.json` containing metrics and timestamp.
- Implemented CI and CD workflows with artifact passing, Git LFS support, and Gmail SMTP notification job.
- Hardened the pipeline runner to ensure consistent `sys.path` initialization across environments and made all path calculations relative to the project root.

This README reflects the current state of the ML evaluation and CI/CD automation. It will be updated as the registry is moved to a remote store or as deployment targets are added.
