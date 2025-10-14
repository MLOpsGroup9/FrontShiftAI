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
        cleaned_path = data_dir / "cleaned" / "cleaned_chunks.csv"
        vector_db_path = data_dir / "vector_db"
        vector_db_path.mkdir(parents=True, exist_ok=True)

        # --- Load cleaned data ---
        if not cleaned_path.exists():
            msg = f"{cleaned_path} not found. Run preprocess.py first."
            logger.error(msg)
            raise FileNotFoundError(msg)

        df = pd.read_csv(cleaned_path)
        logger.info(f"Loaded {len(df)} cleaned chunks for embedding.")

        # --- Initialize ChromaDB ---
        client = chromadb.PersistentClient(path=str(vector_db_path))
        embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )

        collection_name = "frontshift_policies"

        # Remove existing collection if rebuilding
        existing_collections = [c.name for c in client.list_collections()]
        if collection_name in existing_collections:
            logger.warning(f"Removing existing collection '{collection_name}' for rebuild.")
            client.delete_collection(name=collection_name)

        collection = client.create_collection(
            name=collection_name, embedding_function=embedding_fn
        )

        # --- Prepare data for insertion ---
        documents = df["text"].tolist()
        metadatas = df[["filename", "company", "chunk_id"]].to_dict(orient="records")
        ids = [f"{row['filename']}_{row['chunk_id']}" for _, row in df.iterrows()]

        # --- Sanity check before embedding ---
        if len(documents) == 0:
            logger.warning("No documents to embed. Check cleaned_chunks.csv contents.")
        elif len(documents) < 10:
            logger.warning(f"Only {len(documents)} chunks detected. Possible incomplete extraction.")

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
