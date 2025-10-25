GitHub Repo Structure for FrontShiftAI PLANNED 

Extended Project Structure (with Fine-Tuning)
```bash
FrontShiftAI/
│
── data/                         
│   ├── raw/                      # Original PDFs (handbooks, FAQs)
│   ├── processed/                 # Cleaned text, structured chunks
│   ├── qna/                       # Final Q&A dataset (JSONL/CSV)
│   │   ├── qa.jsonl               # 1k Q&A pairs (context + no-context)
│   │   ├── train.jsonl            # Training split
│   │   ├── val.jsonl              # Validation split
│   │   └── test.jsonl             # Test split
│
├── data_pipeline/                 
│   ├── __init__.py
│   ├── download_data.py           # Download PDFs or text files
│   ├── extract_text.py            # Parse PDFs to raw text
│   ├── clean_text.py              # Normalize text (remove headers, whitespace)
│   ├── chunk_text.py              # Chunk text for embedding
│   ├── generate_qna_from_docs.py  # Hybrid Q&A extraction (no LLM)
│   ├── split_data.py              # Split contextual/non-contextual, train/val/test
│   ├── embed_index.py             # Build embeddings + Chroma index
│   ├── pipeline_runner.py         # Orchestrates full ETL pipeline
│   └── utils.py                   # Common helpers (save_jsonl, logging)
│
├── scripts/
│   └── generate_qna_from_pdfs.py 
│ 
├── dags/
│   └── frontshift_pipeline_dag.py  # Airflow DAG connecting all steps
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