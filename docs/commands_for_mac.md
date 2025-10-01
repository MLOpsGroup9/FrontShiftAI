1. Create & Manage Conda/Pyenv Environment

# list all environments
conda env list        # if using conda
pyenv versions        # if using pyenv + venv

# activate your project env
conda activate frontshiftai
# OR
pyenv activate frontshiftai


2. Install Dependencies

# install from requirements.txt
pip install -r requirements.txt

# install llama-cpp with Metal support (for MacBook GPU)
CMAKE_ARGS="-DLLAMA_METAL=on" pip install llama-cpp-python --force-reinstall --upgrade

# install langchain-community (required for integrations)
pip install langchain-community


3. Authenticate Hugging Face

huggingface-cli logout
huggingface-cli login --token YOUR_HF_TOKEN

# check
huggingface-cli whoami


4. Download Model (LLaMA-3 8B Q4_K_M GGUF)
mkdir -p models

# with huggingface-cli
huggingface-cli download QuantFactory/Meta-Llama-3-8B-Instruct-GGUF \
  Meta-Llama-3-8B-Instruct.Q4_K_M.gguf \
  --local-dir models/

# OR with curl
export HF_TOKEN=YOUR_HF_TOKEN
curl -L -H "Authorization: Bearer $HF_TOKEN" \
  https://huggingface.co/QuantFactory/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf \
  -o models/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf


5. Prepare Data
  data/qna/qa.jsonl

head -n 5 data/qna/qa.jsonl


6. Build Embeddings (Index into Chroma)

# always run from repo root!
python -m src.rag.embed


7. Run Q&A Pipeline