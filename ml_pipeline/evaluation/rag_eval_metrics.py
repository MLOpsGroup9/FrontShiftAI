import sys
from pathlib import Path
import pandas as pd
from sentence_transformers import SentenceTransformer, util

current_file = Path(__file__).resolve()
project_root = current_file.parents[2]  # /Users/sriks/Documents/Projects/FrontShiftAI
sys.path.append(str(project_root))

from ml_pipeline.rag.rag_query_utils import retrieve_context

PROJECT_ROOT = Path("/Users/sriks/Documents/Projects/FrontShiftAI")
OUT_CSV = PROJECT_ROOT / "ml_pipeline" / "evaluation" / "eval_results" / "rag_eval_results.csv"

EVAL_QUERIES = [
    {"q": "how many sick leaves do I get", "company": "Crouse Medical Practice"},
    {"q": "what is bereavement leave policy", "company": "Crouse Medical Practice"},
    {"q": "how to apply for FMLA", "company": "Crouse Medical Practice"},
]

def main():
    print("🧠 Starting RAG evaluation...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    rows = []

    for item in EVAL_QUERIES:
        q = item["q"]
        company = item.get("company")
        print(f"🔍 Evaluating query: '{q}' | company: {company}")

        docs, metas = retrieve_context(q, company, top_k=4)
        context = " ".join(docs) if docs else ""

        if context:
            sim = util.cos_sim(
                model.encode(q, convert_to_tensor=True),
                model.encode(context, convert_to_tensor=True)
            ).item()
            precision_at_k = 1.0 if len(docs) > 0 else 0.0
        else:
            sim = 0.0
            precision_at_k = 0.0

        rows.append({
            "query": q,
            "company": company or "",
            "k": 4,
            "semantic_sim": round(float(sim), 4),
            "precision_at_k": precision_at_k,
            "num_docs": len(docs),
            "top_filenames": ";".join({m.get("filename", "") for m in metas}) if metas else ""
        })

    df = pd.DataFrame(rows)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_CSV, index=False)
    print(f"✅ Saved evaluation results to {OUT_CSV}")
    print(df)

if __name__ == "__main__":
    main()
