"""
Combine RAG, Bias, and Sensitivity evaluation results
into one unified summary and log to Weights & Biases.
"""

import pandas as pd
from pathlib import Path
import json
import matplotlib.pyplot as plt
import sys

# --- Ensure project root is in sys.path ---
current_file = Path(__file__).resolve()
project_root = current_file.parents[2]  # /Users/sriks/Documents/Projects/FrontShiftAI
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from ml_pipeline.tracking.exp_tracking import log_metrics
from ml_pipeline.utils.logger import get_logger

# --- Paths ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = PROJECT_ROOT / "ml_pipeline" / "evaluation" / "eval_results"
OUT_JSON = EVAL_DIR / "unified_summary.json"
OUT_CSV = EVAL_DIR / "unified_summary.csv"

# --- Logger ---
logger = get_logger("unified_eval_summary")

def main():
    logger.info("📊 Generating unified evaluation summary...")

    rag_path = EVAL_DIR / "rag_eval_results.csv"
    bias_path = EVAL_DIR / "bias_report.csv"
    sens_path = EVAL_DIR / "sensitivity_report.csv"

    # --- Load results ---
    rag = pd.read_csv(rag_path)
    bias = pd.read_csv(bias_path)
    sens = pd.read_csv(sens_path)

    # --- Compute summaries ---
    rag_metrics = {
        "mean_semantic_sim": round(rag["semantic_sim"].mean(), 4),
        "mean_precision_at_k": round(rag["precision_at_k"].mean(), 4)
    }

    bias_metrics = {
        "avg_similarity": round(bias["mean_sim"].mean(), 4),
        "companies_evaluated": len(bias)
    }

    sens_metrics = {
        "mean_context_similarity": round(sens["context_similarity"].mean(), 4),
        "num_variants": len(sens)
    }

    summary = {
        "rag": rag_metrics,
        "bias": bias_metrics,
        "sensitivity": sens_metrics
    }

    # --- Save locally ---
    OUT_JSON.write_text(json.dumps(summary, indent=4))
    pd.DataFrame([
        {**rag_metrics, **bias_metrics, **sens_metrics}
    ]).to_csv(OUT_CSV, index=False)

    logger.info(f"✅ Unified summary saved: {OUT_JSON}")

    # --- Log to W&B ---
    artifacts = {"unified_summary": OUT_JSON}
    log_metrics("Unified_Evaluation", "llama_3b_instruct", summary, artifacts)
    logger.info("✅ Unified evaluation metrics logged to W&B")

    # --- Optional Visualization ---
    plt.figure(figsize=(6, 4))
    metrics_names = ["Mean Semantic Sim", "Mean Precision@K", "Mean Context Sim"]
    values = [
        summary["rag"]["mean_semantic_sim"],
        summary["rag"]["mean_precision_at_k"],
        summary["sensitivity"]["mean_context_similarity"],
    ]
    plt.bar(metrics_names, values)
    plt.title("FrontShiftAI Evaluation Summary")
    plt.ylabel("Score")
    plt.ylim(0, 1)
    chart_path = EVAL_DIR / "unified_summary_plot.png"
    plt.tight_layout()
    plt.savefig(chart_path)
    plt.close()
    logger.info(f"📊 Saved unified summary plot at {chart_path}")

    # Log the plot to W&B
    artifacts["summary_plot"] = chart_path
    log_metrics("Unified_Evaluation_Visualization", "llama_3b_instruct", summary, artifacts)
    logger.info("✅ Uploaded unified visualization to W&B")

if __name__ == "__main__":
    main()
