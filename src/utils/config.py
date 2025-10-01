import os

# Path to your GGUF model
MODEL_PATH = os.getenv(
    "LLAMA_MODEL",
    "models/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf"
)

# ChromaDB directory
CHROMA_DIR = "chroma_store"

# Context length for retrieval
N_CTX = 2048

# Embedding dimension (LLaMA-3, adjust if needed)
EMBED_DIM = 1024
