import pandas as pd
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions


def main():
    # --- Directory setup ---
    project_root = Path(__file__).resolve().parents[1]
    data_dir = project_root / "data"
    cleaned_path = data_dir / "cleaned" / "cleaned_chunks.csv"
    vector_db_path = data_dir / "vector_db"
    vector_db_path.mkdir(parents=True, exist_ok=True)

    # --- Load cleaned chunks ---
    if not cleaned_path.exists():
        raise FileNotFoundError(f"❌ {cleaned_path} not found. Run preprocess.py first.")

    df = pd.read_csv(cleaned_path)
    print(f"✅ Loaded {len(df)} cleaned chunks for embedding")

    # --- Initialize ChromaDB ---
    client = chromadb.PersistentClient(path=str(vector_db_path))
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )

    collection_name = "frontshift_policies"

    # Remove existing collection if rebuilding
    existing_collections = [c.name for c in client.list_collections()]
    if collection_name in existing_collections:
        print(f"🧹 Removing existing collection '{collection_name}' for a clean rebuild...")
        client.delete_collection(name=collection_name)

    collection = client.create_collection(
        name=collection_name, embedding_function=embedding_fn
    )

    # --- Prepare data for insertion ---
    documents = df["text"].tolist()
    metadatas = df[["filename", "company", "chunk_id"]].to_dict(orient="records")
    ids = [f"{row['filename']}_{row['chunk_id']}" for _, row in df.iterrows()]

    # --- Add to Chroma ---
    print("⚙️ Adding chunks to ChromaDB...")
    collection.add(documents=documents, metadatas=metadatas, ids=ids)

    print(f"✅ Stored {len(documents)} chunks into ChromaDB collection '{collection_name}'")
    print(f"📦 Vector DB saved at: {vector_db_path}")


if __name__ == "__main__":
    main()
