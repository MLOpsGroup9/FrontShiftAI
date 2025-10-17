import os

# ========== Paths ==========
# Data directories
RAW_DATA_DIR = "data/raw"
EXTRACTED_DATA_DIR = "data/extracted"
CLEANED_DATA_DIR = "data/cleaned"
VALIDATED_DATA_DIR = "data/validated"
QNA_DATA_DIR = "data/qna"
VECTOR_DB_DIR = "data/vector_db"
LOGS_DIR = "logs"

# Model path
MODEL_PATH = os.getenv(
    "LLAMA_MODEL",
    "models/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
)

# ========== ChromaDB Settings ==========
CHROMA_DIR = VECTOR_DB_DIR
COLLECTION_CHUNKS = "handbook_chunks"
COLLECTION_QNA = "handbook_qna"

# ========== Pipeline Parameters ==========
# Chunking settings
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# Embedding model
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Context length for retrieval
N_CTX = 4096

# Number of threads for LLM
N_THREADS = 4

# Retrieval settings
TOP_K_RESULTS = 3
