import json
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions
from tqdm import tqdm

# ------------------------------------------
# PATHS
# ------------------------------------------
DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "extracted"
CHUNKS_FILE = DATA_DIR / "combined_chunks.json"
CHROMA_DIR = Path(__file__).resolve().parents[1] / "data" / "vector_db"

# ------------------------------------------
# LOAD CHUNKS
# ------------------------------------------
with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
    chunks = json.load(f)

print(f"✅ Loaded {len(chunks)} chunks from {CHUNKS_FILE.name}")

# ------------------------------------------
# INITIALIZE CHROMADB CLIENT (PERSISTENT)
# ------------------------------------------
client = chromadb.PersistentClient(path=str(CHROMA_DIR))
collection_name = "frontshift_policies"

# Recreate or get existing collection
try:
    client.delete_collection(collection_name)
    print(f"🗑️  Existing collection '{collection_name}' deleted.")
except Exception:
    pass

embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

collection = client.create_collection(
    name=collection_name,
    embedding_function=embedding_fn
)
print(f"✅ Created collection '{collection_name}' in {CHROMA_DIR}")

# ------------------------------------------
# INSERT CHUNKS INTO CHROMADB
# ------------------------------------------
documents = []
metadatas = []
ids = []

for i, chunk in enumerate(tqdm(chunks, desc="Embedding and storing chunks")):
    text = chunk.get("text", "").strip()
    if not text:
        continue

    metadata = chunk.get("metadata", {})
    documents.append(text)
    metadatas.append(metadata)
    ids.append(f"chunk_{i}")

# Batch insert to speed up
collection.add(
    ids=ids,
    documents=documents,
    metadatas=metadatas
)

print(f"✅ Stored {len(documents)} chunks in ChromaDB collection '{collection_name}'")
print(f"📂 Persistent location: {CHROMA_DIR}")

# ------------------------------------------
# TEST RETRIEVAL
# ------------------------------------------
query = "What is the leave policy?"
results = collection.query(query_texts=[query], n_results=3)

print("\n🔍 Example query results:")
for doc, meta, dist in zip(
    results["documents"][0], results["metadatas"][0], results["distances"][0]
):
    print(f"- {meta.get('filename', 'unknown')} (score={dist:.4f})")
    print(doc[:200], "...\n")
