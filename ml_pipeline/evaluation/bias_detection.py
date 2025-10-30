from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path("/Users/sriks/Documents/Projects/FrontShiftAI")
EVAL_CSV = PROJECT_ROOT / "ml_pipeline" / "evaluation" / "eval_results" / "rag_eval_results.csv"
BIAS_CSV = PROJECT_ROOT / "ml_pipeline" / "evaluation" / "eval_results" / "bias_report.csv"

def main():
    df = pd.read_csv(EVAL_CSV)
    if "company" not in df.columns:
        raise ValueError("evaluation CSV missing 'company' column")

    grp = df.groupby("company").agg(
        mean_sim=("semantic_sim", "mean"),
        mean_p_at_k=("precision_at_k", "mean"),
        n=("query", "count")
    ).reset_index()

    overall_sim = grp["mean_sim"].mean()
    grp["sim_gap_vs_mean"] = grp["mean_sim"] - overall_sim

    grp.sort_values("mean_sim", ascending=False, inplace=True)
    grp.to_csv(BIAS_CSV, index=False)
    print(f"✅ Saved bias report to {BIAS_CSV}")

if __name__ == "__main__":
    main()
