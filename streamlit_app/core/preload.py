# streamlit_app/core/preload.py
import chromadb
from chromadb.utils import embedding_functions
from llama_cpp import Llama
from pathlib import Path


PROJECT_ROOT = Path("/Users/sriks/Documents/Projects/FrontShiftAI")
DATA_DIR = PROJECT_ROOT / "data_pipeline" / "data"
CHROMA_DIR = DATA_DIR / "vector_db"
MODEL_PATH = PROJECT_ROOT / "models" / "Meta-Llama-3-8B-Instruct.Q4_K_M.gguf"


print("🦙 Preloading LLaMA model and ChromaDB...")

# Load LLaMA model globally
llm = Llama(
    model_path=str(MODEL_PATH),
    n_ctx=4096,
    n_threads=4,
    temperature=0.9,
    top_p=0.9,
    max_tokens=1024,
    verbose=False,
)
print("✅ LLaMA model loaded successfully")

# Load ChromaDB collection
client = chromadb.PersistentClient(path=str(CHROMA_DIR))
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)
collection = client.get_collection("frontshift_handbooks", embedding_function=embedding_fn)
print(f"✅ ChromaDB loaded with {collection.count()} chunks")


def get_model():
    return llm

def get_collection():
    return collection
