import sys
from pathlib import Path
import pandas as pd
from sentence_transformers import SentenceTransformer, util

# --- Ensure project root in sys.path ---
current_file = Path(__file__).resolve()
project_root = current_file.parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from ml_pipeline.rag.rag_query_utils import retrieve_context
from ml_pipeline.utils.logger import get_logger
from ml_pipeline.tracking.exp_tracking import log_metrics

# ✅ Initialize logger
logger = get_logger("sensitivity_analysis")

PROJECT_ROOT = project_root
OUT_CSV = PROJECT_ROOT / "ml_pipeline" / "evaluation" / "eval_results" / "sensitivity_report.csv"

BASE = "how many sick leaves do I get"
PARAPhrases = [
    "what is the sick leave policy",
    "how many days of sick leave are allowed",
    "sick leave entitlement"
]

COMPANY = "Crouse Medical Practice"

def main():
    logger.info(f"🧩 Running sensitivity analysis for company: {COMPANY}")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    rows = []

    base_docs, _ = retrieve_context(BASE, COMPANY, top_k=4)
    base_ctx = " ".join(base_docs) if base_docs else ""
    base_emb = model.encode(base_ctx, convert_to_tensor=True) if base_ctx else None
    logger.info(f"Base query: '{BASE}' | Context length: {len(base_ctx)}")

    for p in PARAPhrases:
        logger.info(f"Comparing variant: '{p}'")
        docs, _ = retrieve_context(p, COMPANY, top_k=4)
        ctx = " ".join(docs) if docs else ""
        if base_emb is not None and ctx:
            emb = model.encode(ctx, convert_to_tensor=True)
            sim = util.cos_sim(base_emb, emb).item()
        else:
            sim = 0.0
        rows.append({
            "base_query": BASE,
            "variant_query": p,
            "context_similarity": round(float(sim), 4),
            "context_length": len(ctx)
        })
        logger.info(f"Context similarity ({BASE} ↔ {p}): {sim:.3f}")

    # Save CSV
    df = pd.DataFrame(rows)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_CSV, index=False)
    logger.info(f"✅ Saved sensitivity report to {OUT_CSV}")
    logger.info(f"\n{df}")

    print(f"✅ Sensitivity analysis completed. Results saved at {OUT_CSV}")

    # --------------------------------------------------------
    # ✅ Log metrics + artifact to W&B
    # --------------------------------------------------------
    avg_ctx_sim = round(df["context_similarity"].mean(), 4)
    metrics = {"mean_context_similarity": avg_ctx_sim}
    artifacts = {"sensitivity_report": OUT_CSV}

    log_metrics("Sensitivity_Analysis", "llama_3b_instruct", metrics, artifacts)
    logger.info(f"📊 Logged sensitivity analysis metrics to W&B: {metrics}")

if __name__ == "__main__":
    main()
