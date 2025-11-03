from pathlib import Path
import pandas as pd
import sys

# --- Ensure FrontShiftAI root is in sys.path ---
current_file = Path(__file__).resolve()
project_root = current_file.parents[2]  # /Users/sriks/Documents/Projects/FrontShiftAI
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from ml_pipeline.utils.logger import get_logger
from ml_pipeline.tracking.exp_tracking import log_metrics

# ✅ Initialize logger
logger = get_logger("bias_detection")

PROJECT_ROOT = project_root
EVAL_CSV = PROJECT_ROOT / "ml_pipeline" / "evaluation" / "eval_results" / "rag_eval_results.csv"
BIAS_CSV = PROJECT_ROOT / "ml_pipeline" / "evaluation" / "eval_results" / "bias_report.csv"

def main():
    logger.info("🎯 Starting bias detection analysis...")

    # Load evaluation results
    if not EVAL_CSV.exists():
        logger.error(f"❌ Evaluation file not found at {EVAL_CSV}")
        raise FileNotFoundError(f"Evaluation file not found: {EVAL_CSV}")

    df = pd.read_csv(EVAL_CSV)
    logger.info(f"📥 Loaded evaluation data: {len(df)} rows")

    if "company" not in df.columns:
        logger.error("Evaluation CSV missing 'company' column.")
        raise ValueError("evaluation CSV missing 'company' column")

    # Group by company and calculate metrics
    grp = df.groupby("company").agg(
        mean_sim=("semantic_sim", "mean"),
        mean_p_at_k=("precision_at_k", "mean"),
        n=("query", "count")
    ).reset_index()

    # Compute bias measure
    overall_sim = grp["mean_sim"].mean()
    grp["sim_gap_vs_mean"] = grp["mean_sim"] - overall_sim
    logger.info(f"📊 Overall mean similarity across companies: {overall_sim:.4f}")

    # Sort and save
    grp.sort_values("mean_sim", ascending=False, inplace=True)
    BIAS_CSV.parent.mkdir(parents=True, exist_ok=True)
    grp.to_csv(BIAS_CSV, index=False)

    logger.info(f"✅ Saved bias report to {BIAS_CSV}")
    logger.info(f"\n{grp}")
    print(f"✅ Bias report saved: {BIAS_CSV}")

    # --------------------------------------------------------
    # ✅ Log results to Weights & Biases (W&B)
    # --------------------------------------------------------
    metrics = {
        "avg_similarity": round(grp["mean_sim"].mean(), 4),
        "companies_evaluated": len(grp)
    }
    artifacts = {"bias_report": BIAS_CSV}

    log_metrics("Bias_Detection", "llama_3b_instruct", metrics, artifacts)
    logger.info(f"📊 Logged Bias Detection metrics to W&B: {metrics}")

if __name__ == "__main__":
    main()
