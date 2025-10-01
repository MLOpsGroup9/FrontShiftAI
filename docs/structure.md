GitHub Repo Structure for FrontShiftAI PLANNED 

```bash
FrontShiftAI/
│
├── data/                     # Raw and processed data
│   ├── raw/                  # Original PDFs (handbooks, FAQs)
│   ├── processed/             # Cleaned text, chunks
│   └── qna/                  # Final Q&A dataset (CSV, JSONL)
│
├── notebooks/                # Jupyter notebooks
│   ├── 01_text_extraction.ipynb
│   ├── 02_chunking_cleaning.ipynb
│   ├── 03_qna_generation.ipynb
│   ├── 04_embedding_experiments.ipynb
│   └── 05_eval_metrics.ipynb
│
├── src/                      # Core source code
│   ├── rag/                  # Retrieval-Augmented Generation
│   │   ├── ingest.py          # PDF → text ingestion
│   │   ├── chunking.py        # Semantic chunking
│   │   ├── embed.py           # Embeddings + vector DB indexing
│   │   ├── retriever.py       # Hybrid/dense retrieval
│   │   └── qa_pipeline.py     # RAG Q&A pipeline
│   │
│   ├── agents/               # Agentic orchestration
│   │   ├── tools/             # Tool wrappers (calendar, LMS, HRIS)
│   │   ├── memory.py          # Context + conversation memory
│   │   └── orchestrator.py    # Agent logic
│   │
│   ├── voice/                # Voice interaction
│   │   ├── stt.py             # Speech-to-text (Whisper/GCP STT)
│   │   ├── tts.py             # Text-to-speech (Coqui/GCP TTS)
│   │   └── voice_agent.py     # Voice-enabled agent wrapper
│   │
│   ├── api/                  # Backend API
│   │   ├── main.py            # FastAPI entrypoint
│   │   ├── routes/            # Endpoints for chat, RAG, agents
│   │   └── schemas.py         # Request/response schemas
│   │
│   └── utils/                 # Helpers
│       ├── config.py
│       ├── logging.py
│       └── evaluation.py
│
├── infra/                    # Deployment & infra
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── k8s/                   # Kubernetes manifests
│   ├── gcp/                   # Vertex AI / GCP configs
│   └── ci-cd/                 # GitHub Actions / Cloud Build
│
├── tests/                    # Unit & integration tests
│   ├── test_rag.py
│   ├── test_agents.py
│   ├── test_voice.py
│   └── test_api.py
│
├── docs/                     # Documentation
│   ├── Project_Scoping.md
│   ├── README_assets/         # Images/diagrams for docs
│   ├── system_architecture.png
│   └── deployment_flow.png
│
├── README.md                 # High-level overview
├── requirements.txt          # Python dependencies
├── environment.yml           # Conda environment (optional)
├── LICENSE
└── .gitignore
```


Updated Repo Structure (with Data Pipeline clear)
```bash
FrontShiftAI/
│
├── data/                     # Data storage
│   ├── raw/                  # Original PDFs (handbooks, FAQs)
│   ├── processed/             # Cleaned text, structured chunks
│   └── qna/                  # Final Q&A dataset (CSV, JSONL)
│
├── data_pipeline/            # 🚀 Data pipeline modules
│   ├── extract_text.py        # PDF → raw text
│   ├── clean_text.py          # Normalize (remove headers, dupes, artifacts)
│   ├── chunk_text.py          # Split into semantic chunks
│   ├── generate_qna.py        # Synthetic Q&A generation (optional)
│   ├── embed_index.py         # Embedding + vector DB indexing
│   └── pipeline_runner.py     # Orchestrates full ETL pipeline
│
├── notebooks/                # Jupyter notebooks for exploration
│   ├── 01_text_extraction.ipynb
│   ├── 02_chunking_cleaning.ipynb
│   ├── 03_qna_generation.ipynb
│   ├── 04_embedding_experiments.ipynb
│   └── 05_eval_metrics.ipynb
│
├── src/                      # Core application code
│   ├── rag/                  # Retrieval-Augmented Generation
│   ├── agents/               # Agentic orchestration
│   ├── voice/                # STT/TTS integrations
│   ├── api/                  # FastAPI backend
│   └── utils/                 # Shared helpers
│
├── infra/                    # Deployment & infra (Docker, GCP, K8s, CI/CD)
├── tests/                    # Unit & integration tests
├── docs/                     # Project_Scoping, diagrams, assets
├── README.md                 # High-level overview
├── requirements.txt
├── LICENSE
└── .gitignore
```



Extended Project Structure (with Fine-Tuning)
```bash
FrontShiftAI/
│
├── data/                         
│   ├── raw/                      # Original PDFs (handbooks, FAQs)
│   ├── processed/                 # Cleaned text, structured chunks
│   ├── qna/                       # Final Q&A dataset (JSONL/CSV)
│   │   ├── qa.jsonl               # 1k Q&A pairs (context + no-context)
│   │   ├── train.jsonl            # Training split
│   │   ├── val.jsonl              # Validation split
│   │   └── test.jsonl             # Test split
│
├── data_pipeline/                 # (Optional) ETL pipeline scripts
│   ├── extract_text.py
│   ├── clean_text.py
│   ├── chunk_text.py
│   ├── generate_qna.py
│   ├── embed_index.py
│   └── pipeline_runner.py
│
├── src/                          
│   ├── rag/                       # Retrieval-Augmented Generation
│   │   ├── embed.py               # Build Chroma index
│   │   ├── qa_pipeline.py         # RAG Q&A system
│   │   └── eval_rag.py            # Evaluate Recall@k, F1, hallucination
│   │
│   ├── finetune/                  # Fine-tuning module
│   │   ├── prepare_data.py        # Convert Q&A dataset into instruct format
│   │   ├── train_lora.py          # Fine-tune LLaMA-3 8B with LoRA/QLoRA
│   │   ├── evaluate_ft.py         # Evaluate fine-tuned model
│   │   └── inference_ft.py        # Run inference with fine-tuned model
│   │
│   ├── agents/                    # Agentic orchestration
│   │   ├── tools/                 # Calendar/LMS/HRIS tool wrappers
│   │   ├── orchestrator.py
│   │   └── memory.py
│   │
│   ├── voice/                     # Voice STT/TTS integration
│   │   ├── stt.py
│   │   ├── tts.py
│   │   └── voice_agent.py
│   │
│   ├── api/                       # Backend API
│   │   ├── main.py                # FastAPI entrypoint
│   │   └── routes/                # Endpoints (rag, agents, voice)
│   │
│   └── utils/                     
│       ├── config.py              # Model/DB settings
│       ├── logging.py
│       └── evaluation.py
│
├── infra/                         # Deployment & infra
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── k8s/                       # Kubernetes manifests
│   └── gcp/                       # Vertex AI / GKE configs
│
├── tests/                         # Unit & integration tests
│   ├── test_rag.py
│   ├── test_finetune.py
│   ├── test_agents.py              # Placeholder for agents
│   ├── test_voice.py               # Placeholder for voice
│   └── test_api.py
│
├── docs/                          # Documentation
│   ├── Project_Scoping.md
│   ├── README_assets/
│   └── diagrams/
│
├── models
├── README.md                      # High-level overview
├── requirements.txt               # Python deps (RAG + FT)
├── environment.yml                 # Conda env (optional)
└── LICENSE
```