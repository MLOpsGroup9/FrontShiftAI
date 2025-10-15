import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))


import pandas as pd
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions
from data_pipeline.utils.logger import get_logger

logger = get_logger(__name__)

def main():
    logger.info("Starting embedding and ChromaDB storage pipeline...")

    try:
        # --- Directory setup ---
        project_root = Path(__file__).resolve().parents[1]  # data_pipeline/
        data_dir = project_root / "data"

        # 👇 Change input path from cleaned → validated
        validated_dir = data_dir / "validated"
        vector_db_path = data_dir / "vector_db"
        vector_db_path.mkdir(parents=True, exist_ok=True)

        # --- Load validated data ---
        validated_files = list(validated_dir.glob("*.json"))
        if not validated_files:
            msg = f"No validated handbook files found in {validated_dir}. Run validate_data.py first."
            logger.error(msg)
            raise FileNotFoundError(msg)

        # Combine all validated chunks
        all_chunks = []
        for file_path in validated_files:
            df = pd.read_json(file_path)
            all_chunks.append(df)
        df = pd.concat(all_chunks, ignore_index=True)
        logger.info(f"Loaded {len(df)} validated chunks for embedding.")

        # --- Initialize ChromaDB ---
        client = chromadb.PersistentClient(path=str(vector_db_path))
        embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )

        # 👇 Rename collection to match new dataset type
        collection_name = "frontshift_handbooks"

        # Remove existing collection if rebuilding
        existing_collections = [c.name for c in client.list_collections()]
        if collection_name in existing_collections:
            logger.warning(f"Removing existing collection '{collection_name}' for rebuild.")
            client.delete_collection(name=collection_name)

        collection = client.create_collection(
            name=collection_name, embedding_function=embedding_fn
        )

        # --- Prepare data for insertion ---
        documents = df["policy_text"].tolist() if "policy_text" in df.columns else df["text"].tolist()
        metadatas = df[["filename", "company", "chunk_id"]].to_dict(orient="records") \
            if {"filename", "company", "chunk_id"}.issubset(df.columns) else [{} for _ in range(len(df))]
        ids = [f"chunk_{i}" for i in range(len(df))]

        # --- Sanity check before embedding ---
        if len(documents) == 0:
            logger.warning("No documents to embed. Check validated_handbooks contents.")
        elif len(documents) < 10:
            logger.warning(f"Only {len(documents)} chunks detected. Possible incomplete validation output.")

        # --- Add to Chroma ---
        logger.info(f"Adding {len(documents)} chunks to ChromaDB...")
        collection.add(documents=documents, metadatas=metadatas, ids=ids)

        logger.info(f"Stored {len(documents)} chunks into ChromaDB collection '{collection_name}'.")
        logger.info(f"Vector DB saved at: {vector_db_path}")

    except Exception as e:
        logger.error(f"Error during embedding/storage stage: {e}", exc_info=True)
        raise

    logger.info("Embedding pipeline completed successfully.")


if __name__ == "__main__":
    main()
