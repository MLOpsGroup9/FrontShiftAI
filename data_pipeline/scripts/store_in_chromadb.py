"""
Embedding and ChromaDB storage pipeline.
Reads validated chunks from data/validated/valid_chunks.jsonl
and stores embeddings into data/vector_db/.
"""

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import json
import pandas as pd
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions
from data_pipeline.utils.logger import get_logger

logger = get_logger(__name__)

def main():
    logger.info("🚀 Starting embedding and ChromaDB storage pipeline...")

    try:
        # --- Directory setup ---
        project_root = Path(__file__).resolve().parents[1]  # data_pipeline/
        data_dir = project_root / "data"

        # Input: validated chunks file
        valid_chunks_path = data_dir / "validated" / "valid_chunks.jsonl"
        if not valid_chunks_path.exists():
            msg = f"Validated chunks file not found: {valid_chunks_path}. Run validate_data.py first."
            logger.error(msg)
            raise FileNotFoundError(msg)

        # Output: ChromaDB vector storage
        vector_db_path = data_dir / "vector_db"
        vector_db_path.mkdir(parents=True, exist_ok=True)

        # --- Load validated chunks ---
        logger.info(f"📥 Loading validated chunks from: {valid_chunks_path}")
        all_chunks = []
        with open(valid_chunks_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    record = json.loads(line)
                    meta = record.get("metadata", {})
                    all_chunks.append({
                        "text": record.get("text", ""),
                        "company": meta.get("company", "Unknown"),
                        "chunk_id": meta.get("chunk_id", ""),
                        "filename": meta.get("doc_id", ""),
                        "section": meta.get("section_title", ""),
                        "hash": meta.get("hash_64", "")
                    })
                except json.JSONDecodeError:
                    logger.warning("⚠️ Skipping invalid JSON line in valid_chunks.jsonl")

        df = pd.DataFrame(all_chunks)
        logger.info(f"✅ Loaded {len(df)} valid chunks for embedding.")

        if df.empty:
            raise ValueError("No valid chunks found in file. Check validation output.")

        # --- Initialize ChromaDB ---
        client = chromadb.PersistentClient(path=str(vector_db_path))
        embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )

        collection_name = "frontshift_handbooks"
        existing_collections = [c.name for c in client.list_collections()]

        # Clean rebuild
        if collection_name in existing_collections:
            logger.warning(f"🧹 Removing existing collection '{collection_name}' for rebuild.")
            client.delete_collection(name=collection_name)

        collection = client.create_collection(
            name=collection_name,
            embedding_function=embedding_fn
        )

        # --- Prepare data ---
        documents = df["text"].tolist()
        metadatas = df[["filename", "company", "chunk_id", "section"]].to_dict(orient="records")
        ids = [f"chunk_{i}" for i in range(len(df))]

        # --- Sanity checks ---
        if len(documents) == 0:
            logger.warning("No documents to embed. Check valid_chunks.jsonl contents.")
        elif len(documents) < 10:
            logger.warning(f"Only {len(documents)} chunks detected. Possible small dataset.")

        # --- Add to ChromaDB ---
        logger.info(f"🧠 Adding {len(documents)} chunks to ChromaDB collection '{collection_name}'...")
        collection.add(documents=documents, metadatas=metadatas, ids=ids)

        logger.info(f"💾 Stored {len(documents)} embeddings in collection '{collection_name}'.")
        logger.info(f"📂 Vector DB saved at: {vector_db_path}")

    except Exception as e:
        logger.error(f"❌ Error during embedding/storage stage: {e}", exc_info=True)
        raise

    logger.info("✅ Embedding pipeline completed successfully.")


if __name__ == "__main__":
    main()
