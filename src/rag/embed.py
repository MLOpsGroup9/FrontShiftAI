import json
import os
from tqdm import tqdm
import chromadb
from sentence_transformers import SentenceTransformer

DATA_PATH = "data/qna/qa.jsonl"
CHROMA_PATH = "data/chroma_db"

def build_chroma():
    # Load dataset
    with open(DATA_PATH, "r") as f:
        lines = [json.loads(l) for l in f]

    print(f"📦 Loaded {len(lines)} Q&A pairs from {DATA_PATH}")

    # Initialize embedding model
    embedder = SentenceTransformer("all-MiniLM-L6-v2")

    # Init Chroma
    client = chromadb.PersistentClient(path=CHROMA_PATH)

    # Drop old collection if exists
    try:
        client.delete_collection("handbook_qna")
    except Exception:
        pass

    collection = client.create_collection("handbook_qna")

    # Index Q&A data
    for i, item in enumerate(tqdm(lines, desc="Indexing")):
        q = item.get("instruction", "")
        a = item.get("output", "")
        ctx = item.get("context", "")

        # Combine question + context as retrievable text
        doc_text = q
        if ctx:
            doc_text += " | Context: " + ctx

        emb = embedder.encode(doc_text, convert_to_numpy=True).tolist()

        collection.add(
            documents=[doc_text],
            metadatas=[{"answer": a}],
            embeddings=[emb],
            ids=[f"q_{i}"]
        )

    print(f"✅ Indexed {len(lines)} documents into ChromaDB at {CHROMA_PATH}")

if __name__ == "__main__":
    build_chroma()
    