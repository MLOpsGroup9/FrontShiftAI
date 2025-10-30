from pathlib import Path
from typing import List, Tuple, Dict
import chromadb
from chromadb.utils import embedding_functions

PROJECT_ROOT = Path("/Users/sriks/Documents/Projects/FrontShiftAI")
CHROMA_DIR = PROJECT_ROOT / "data_pipeline" / "data" / "vector_db"
COLLECTION_NAME = "frontshift_handbooks"

def get_collection():
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    emb = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    return client.get_collection(COLLECTION_NAME, embedding_function=emb)

def resolve_company_filter(collection, company_name: str) -> Dict:
    if not company_name:
        return {}
    try:
        name = company_name.strip().lower()
        metas = collection.peek()["metadatas"]
        matches = [m["company"] for m in metas if name in m.get("company", "").lower()]
        if matches:
            return {"where": {"company": matches[0]}}
    except Exception:
        pass
    return {}

def retrieve_context(query: str, company_name: str = None, top_k: int = 4) -> Tuple[List[str], List[dict]]:
    col = get_collection()
    args = {"query_texts": [query], "n_results": top_k}
    args.update(resolve_company_filter(col, company_name))
    res = col.query(**args)
    return res["documents"][0], res["metadatas"][0]
