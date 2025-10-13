import json
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions

def main():
    # Paths
    data_dir = Path(__file__).resolve().parents[1] / "data"
    extracted_path = data_dir / "extracted" / "combined_chunks.json"
    vector_db_path = data_dir / "vector_db"
    vector_db_path.mkdir(parents=True, exist_ok=True)

    # Load chunks
    with open(extracted_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    print(f"✅ Loaded {len(chunks)} chunks for embedding")

    # Initialize ChromaDB
    client = chromadb.PersistentClient(path=str(vector_db_path))
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

    collection_name = "frontshift_policies"
    if collection_name in [c.name for c in client.list_collections()]:
        print(f"🧹 Removing existing collection '{collection_name}' for a clean rebuild...")
        client.delete_collection(collection_name)

    collection = client.create_collection(name=collection_name, embedding_function=embedding_fn)

    # Prepare data for insertion
    documents = [chunk["text"] for chunk in chunks]
    metadatas = [chunk["metadata"] for chunk in chunks]
    ids = [f"{chunk['metadata']['filename']}_{chunk['metadata']['chunk_id']}" for chunk in chunks]

    # Add to Chroma
    print("⚙️ Adding chunks to ChromaDB...")
    collection.add(documents=documents, metadatas=metadatas, ids=ids)

    print(f"✅ Stored {len(documents)} chunks into ChromaDB collection '{collection_name}'")
    print(f"📦 Vector DB path: {vector_db_path}")

if __name__ == "__main__":
    main()
