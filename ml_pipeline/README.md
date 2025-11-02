# FrontShiftAI – Machine Learning and Evaluation Pipeline

## Overview

The Machine Learning (ML) pipeline in FrontShiftAI is designed to evaluate, track, and register retrieval-augmented generation (RAG) models used for answering human resources (HR) policy-related queries. It operates downstream of the data ingestion and embedding stages, consuming processed handbook data from the ChromaDB vector store.

This pipeline focuses on model evaluation, bias and sensitivity analysis, model versioning, and experiment tracking using Weights & Biases (W&B). All components have been modularized under the `ml_pipeline/` directory for clarity, reproducibility, and extensibility.

---

## Directory Structure

```
ml_pipeline/
│
├── evaluation/                  # Evaluation scripts for RAG models
│   ├── rag_eval_metrics.py      # Computes semantic similarity and precision@k
│   ├── bias_detection.py        # Measures inter-company bias in model performance
│   ├── sensitivity_analysis.py  # Evaluates robustness to paraphrased queries
│   ├── unified_eval_summary.py  # Aggregates all metrics and logs to W&B
│   └── eval_results/            # Stores CSV and JSON outputs of all evaluations
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
│   └── __init__.py
│
├── eval_pipeline_runner.py      # Orchestrator for executing all evaluation stages
└── __init__.py
```

---

## 1. RAG Evaluation

**Script:** `rag_eval_metrics.py`

This module evaluates how well the model retrieves and interprets contextual information from company handbooks. It calculates two primary metrics:

1. **Semantic Similarity:** Measures the cosine similarity between the question embedding and the retrieved context embedding.
2. **Precision@k:** Indicates the fraction of relevant context chunks retrieved within the top-k results.

### Key Inputs
- `ml_pipeline/rag/rag_query_utils.py`: Retrieves top-k handbook chunks for a given query.
- `all-MiniLM-L6-v2`: Sentence embedding model for similarity computation.

### Outputs
- `rag_eval_results.csv`: Contains evaluation records for each query.
- Example columns:
  - `query`
  - `company`
  - `semantic_sim`
  - `precision_at_k`
  - `num_docs`
  - `top_filenames`

### Model Registry Integration
Upon completion, the evaluated model (for example, `llama_3b_instruct`) is automatically registered to the local model registry under `models_registry/`. A corresponding `metadata.json` file logs version, timestamp, and performance metrics.

---

## 2. Bias Detection

**Script:** `bias_detection.py`

This module quantifies performance disparities across different companies or document sources. It computes per-company averages for semantic similarity and precision, identifying any bias or imbalance.

### Steps
1. Aggregates evaluation results by company.
2. Computes mean similarity and precision values.
3. Calculates the deviation of each company’s mean from the overall mean.
4. Exports findings to `bias_report.csv`.

### Outputs
- `bias_report.csv` summarizing per-company metrics:
  - `mean_sim`
  - `mean_p_at_k`
  - `sim_gap_vs_mean`
  - `n` (number of queries per company)

### W&B Tracking
The metrics are logged as a separate W&B run under the `Bias_Detection` stage. Artifacts and summaries are uploaded for experiment tracking.

---

## 3. Sensitivity Analysis

**Script:** `sensitivity_analysis.py`

This module evaluates the robustness of the retrieval mechanism against paraphrased queries. It ensures that semantically equivalent questions retrieve similar context chunks.

### Steps
1. Selects a base query (e.g., "how many sick leaves do I get").
2. Defines a set of paraphrased variants.
3. Retrieves top-k documents for each variant.
4. Computes the average cosine similarity between base and variant contexts.

### Outputs
- `sensitivity_report.csv` containing columns:
  - `base_query`
  - `variant_query`
  - `context_similarity`
  - `context_length`

### W&B Tracking
The mean context similarity and number of variants are logged as part of the `Sensitivity_Analysis` stage.

---

## 4. Unified Evaluation Summary

**Script:** `unified_eval_summary.py`

This module consolidates results from all previous evaluation stages (RAG, Bias, Sensitivity) into a single summary report. It provides both tabular and visual insights.

### Steps
1. Reads results from `rag_eval_results.csv`, `bias_report.csv`, and `sensitivity_report.csv`.
2. Computes aggregate metrics:
   - Mean semantic similarity
   - Mean precision@k
   - Mean bias-adjusted similarity
   - Mean context similarity
3. Saves results to both `.csv` and `.json` files.
4. Generates a visualization (`unified_summary_plot.png`) showing comparative metric performance.

### Outputs
- `unified_summary.json`
- `unified_summary.csv`
- `unified_summary_plot.png`

### W&B Tracking
Logs unified metrics and uploads the visualization to W&B as the `Unified_Evaluation_Visualization` stage.

---

## 5. Model Registry

**Script:** `tracking/push_to_registry.py`

The model registry manages versioned storage of all evaluated models. Each model is stored in a versioned subdirectory (e.g., `llama_3b_instruct_v1`, `llama_3b_instruct_v2`) under `models_registry/`.

### Key Features
- Automatically determines the next available version number.
- Copies model artifacts (e.g., `.gguf` files) into the registry.
- Saves `metadata.json` with metrics, timestamp, and version info.

### Example Metadata
```json
{
    "model_name": "llama_3b_instruct",
    "version": "v7",
    "timestamp": "2025-11-02T14:55:37",
    "metrics": {
        "mean_semantic_sim": 0.5425,
        "mean_precision_at_k": 1.0
    }
}
```

---

## 6. Experiment Tracking (Weights & Biases)

**Script:** `tracking/exp_tracking.py`

The pipeline uses **Weights & Biases (W&B)** for experiment tracking and visualization. Each stage of the evaluation (RAG Evaluation, Bias Detection, Sensitivity Analysis, Unified Evaluation) is recorded as a separate W&B run.

### Configuration
Environment variables:
```bash
export WANDB_ENTITY=group9mlops
export WANDB_PROJECT=FrontShiftAI
wandb login
```

### Logging Details
Each stage logs:
- Scalar metrics (mean similarity, precision, bias, sensitivity)
- CSV and JSON artifacts
- Model name and version metadata
- Visualizations for unified summary

W&B automatically provides experiment comparisons, historical charts, and metric tracking across model versions.

---

## 7. Evaluation Pipeline Runner

**Script:** `eval_pipeline_runner.py`

This orchestrator automates the sequential execution of all evaluation stages. It handles logging, timing, subprocess management, and result verification.

### Workflow
1. Executes each stage (RAG Evaluation → Bias Detection → Sensitivity Analysis → Unified Summary).
2. Logs duration, success, and errors for each stage.
3. Checks for expected output files after each run.
4. Produces a final log summary in the console and `ml_pipeline/logs/`.

### Example Output
```
🚀 Starting stage: RAG Evaluation
✅ RAG Evaluation completed successfully in 12.4s | Output: rag_eval_results.csv
🚀 Starting stage: Bias Detection
✅ Bias Detection completed successfully in 4.2s | Output: bias_report.csv
🚀 Starting stage: Sensitivity Analysis
✅ Sensitivity Analysis completed successfully in 9.1s | Output: sensitivity_report.csv
🚀 Starting stage: Unified Evaluation Summary
✅ Unified Summary logged to W&B | Output: unified_summary.json
🏁 Pipeline run complete.
```

---

## 8. Logging and Utilities

**Script:** `utils/logger.py`

A centralized logger is used across all modules to ensure consistent, timestamped logging in both console and file output. 

### Features
- Standardized log format `[timestamp | level | module | message]`
- Separate log files per module (e.g., `rag_eval_metrics.log`, `bias_detection.log`)
- Integrated with both evaluation scripts and the pipeline runner

---

## 9. Results Directory

All outputs are stored under:

```
ml_pipeline/evaluation/eval_results/
│
├── rag_eval_results.csv
├── bias_report.csv
├── sensitivity_report.csv
├── unified_summary.csv
├── unified_summary.json
└── unified_summary_plot.png
```

Each file represents a distinct analytical layer of model evaluation and is version-tracked via Git and W&B.

---

## 10. Summary

The ML pipeline in FrontShiftAI provides a modular, reproducible, and interpretable framework for evaluating RAG-based HR assistants. It integrates retrieval, evaluation, and tracking components to ensure models can be continuously assessed and versioned with traceable performance records.

Key strengths:
- Clear separation of evaluation and tracking logic
- Full integration with W&B for transparency
- Local model versioning for offline reproducibility
- Unified metric summaries for performance monitoring

This architecture enables scalable and auditable experimentation across multiple model versions, companies, and query distributions.
