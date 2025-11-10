# streamlit_app/core/preload.py
import chromadb
from chromadb.utils import embedding_functions
from llama_cpp import Llama
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data_pipeline" / "data"
CHROMA_DIR = DATA_DIR / "vector_db"
MODELS_DIR = PROJECT_ROOT / "models"
REGISTRY_DIR = PROJECT_ROOT / "models_registry"

# Primary model path (from registry)
REGISTRY_MODEL = None
if REGISTRY_DIR.exists():
    # Find latest version automatically
    versions = sorted(REGISTRY_DIR.glob("llama_3b_instruct_v*/Llama-*.gguf"))
    if versions:
        REGISTRY_MODEL = versions[-1]

# Fallback model path (inside /models/)
DEFAULT_MODEL = MODELS_DIR / "Llama-3.2-3B-Instruct-Q4_K_S.gguf"

# Choose which one to load
MODEL_PATH = REGISTRY_MODEL if REGISTRY_MODEL and REGISTRY_MODEL.exists() else DEFAULT_MODEL

if not MODEL_PATH.exists():
    raise FileNotFoundError(
        f"Model not found in registry or fallback path. Expected at:\n{DEFAULT_MODEL}"
    )

print(f"Loading model from: {MODEL_PATH}")

# Load LLaMA model
llm = Llama(
    model_path=str(MODEL_PATH),
    n_ctx=4096,
    n_threads=4,
    temperature=0.7,
    top_p=0.9,
    max_tokens=1024,
    verbose=False,
)
print("Model loaded successfully")

# Load ChromaDB
client = chromadb.PersistentClient(path=str(CHROMA_DIR))
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)
collection = client.get_collection("frontshift_handbooks", embedding_function=embedding_fn)
print(f"ChromaDB loaded with {collection.count()} chunks")

def get_model():
    return llm

def get_collection():
    return collection
