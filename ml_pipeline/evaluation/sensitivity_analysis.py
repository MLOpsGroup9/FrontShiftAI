import sys
from pathlib import Path
import pandas as pd
from sentence_transformers import SentenceTransformer, util

# --- Project setup ---
current_file = Path(__file__).resolve()
project_root = current_file.parents[2]  # /Users/sriks/Documents/Projects/FrontShiftAI
sys.path.append(str(project_root))

from ml_pipeline.utils.logger import get_logger
from ml_pipeline.rag.rag_query_utils import retrieve_context

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

    # --- Base query context ---
    base_docs, _ = retrieve_context(BASE, COMPANY, top_k=4)
    base_ctx = " ".join(base_docs) if base_docs else ""
    base_emb = model.encode(base_ctx, convert_to_tensor=True) if base_ctx else None
    logger.info(f"Base query: '{BASE}' | Context length: {len(base_ctx)}")

    # --- Paraphrase comparisons ---
    for p in PARAPhrases:
        logger.info(f"Comparing variant: '{p}'")
        docs, _ = retrieve_context(p, COMPANY, top_k=4)
        ctx = " ".join(docs) if docs else ""
        if base_emb is not None and ctx:
            emb = model.encode(ctx, convert_to_tensor=True)
            sim = util.cos_sim(base_emb, emb).item()
        else:
            sim = 0.0

        logger.info(f"Context similarity ({BASE} ↔ {p}): {round(float(sim), 4)}")
        rows.append({
            "base_query": BASE,
            "variant_query": p,
            "context_similarity": round(float(sim), 4),
            "context_length": len(ctx)
        })

    # --- Save report ---
    df = pd.DataFrame(rows)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_CSV, index=False)
    logger.info(f"✅ Saved sensitivity report to {OUT_CSV}")
    logger.info(f"\n{df}")

    print(f"✅ Sensitivity analysis completed. Results saved at {OUT_CSV}")

if __name__ == "__main__":
    main()
