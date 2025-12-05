from sentence_transformers import SentenceTransformer
import os

def download_model():
    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    print(f"Downloading model: {model_name}")
    # This will download and cache the model in ~/.cache/huggingface
    model = SentenceTransformer(model_name)
    print("Model downloaded successfully")

if __name__ == "__main__":
    download_model()
