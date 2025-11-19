# Generation backends
GENERATION_BACKEND=mercury          # options: local | hf | mercury | auto
LLAMA_MODEL_PATH=chat_pipeline/models/Llama-3.2-3B-Instruct-Q4_K_M.gguf
LLAMA_N_GPU_LAYERS=-1               # -1 = full offload if llama-cpp is GPU-enabled
HF_MODEL_NAME=Qwen/Qwen2.5-1.5B-Instruct
HF_API_TOKEN=hf_your_token_here
INCEPTION_API_KEY=sk_mercury_key_here
INCEPTION_API_BASE=https://api.inceptionlabs.ai/v1
MERCURY_MODEL=mercury

# Judge (eval) backends
OPENAI_API_KEY=sk_openai_key_here    # for gpt-4o-mini judge
JUDGE_MODEL=Qwen/Qwen2.5-3B-Instruct # fallback judge
# (INCEPTION_API_KEY/BASE and MERCURY_MODEL reused if you want Mercury as judge fallback)

# Vector store / data
CHROMA_DIR=data_pipeline/data/vector_db
CHROMA_REMOTE_URI=gs://your-bucket/vector_db   # or leave blank if local
CHROMA_COLLECTION=frontshift_handbooks

# Model registry
MODEL_REGISTRY_DIR=models_registry

# Logging
LOG_LEVEL=INFO
CHAT_PIPELINE_LOG_DIR=logs

# Tracking
WANDB_API_KEY=your_wandb_key_here
WANDB_PROJECT=FrontShiftAI
WANDB_ENTITY=your_wandb_entity_here

# Email (notifications)
EMAIL_SENDER=alerts@example.com
EMAIL_PASSWORD=app_password_here
EMAIL_RECEIVER=alerts@example.com

# Misc
TOKENIZERS_PARALLELISM=false
PYTHONPATH=/abs/path/to/Final_Project
