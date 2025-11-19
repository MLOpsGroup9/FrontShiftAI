<<<<<<< HEAD

=======
>>>>>>> f4be250ff65f7a0c0977bc35eae49f0207aa0faa
![Python](https://img.shields.io/badge/Python-3.12+-blue)
![DVC](https://img.shields.io/badge/Data%20Version%20Control-DVC-orange)
![Pytest](https://img.shields.io/badge/Tests-Passed-green)
![Coverage](https://img.shields.io/badge/Coverage-100%25-success)
![ChromaDB](https://img.shields.io/badge/Vector%20DB-ChromaDB-green)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)

# FrontShiftAI: AI Copilot for Deskless Workers

**Team Members**  
- Harshitkumar Brahmbhatt  
- Krishna Venkatesh  
- Raghav Gali  
- Rishi Raj Kuleri  
- Sujitha Godishala  
- Swathi Baba Eswarappa  

---

## 1. Introduction

Deskless workers often have limited access to HR systems because of irregular schedules, lack of computer access, and fragmented communication channels. These challenges reduce employee engagement and lead to lower utilization of benefits, poor training adoption, and higher attrition.  

**FrontShiftAI** is designed to address these issues through a context-aware AI copilot that provides retrieval-augmented responses and integrates with existing HR systems.  

Key components include:  
- Retrieval-Augmented Generation (RAG) core for document-grounded answers  
- An agentic orchestration layer for HR workflow automation (in development)  
- Voice-based interaction features for hands-free accessibility (in development)  

<<<<<<< HEAD
The platform integrates a fully automated **data pipeline**, an **evaluation and registry pipeline**, and a **Streamlit-based AI interface**, all orchestrated through CI/CD workflows.
=======
An optional Airflow DAG (`dvc_repro_manual_dag.py`) in `data_pipeline/dags/` can automatically trigger the pipeline when new URLs are added to `data_pipeline/data/url.json`, or it can be triggered manually via the Airflow UI.
>>>>>>> f4be250ff65f7a0c0977bc35eae49f0207aa0faa

---

## 2. Automated Data Pipeline Overview

<<<<<<< HEAD
The data pipeline is modular, test-driven, and reproducible. Each stage is independently testable using `pytest`. The pipeline supports ingestion, preprocessing, validation, and embedding of HR policy documents.
=======
The data pipeline is fully modular, test-driven, and reproducible. Each stage is independently testable using `pytest`. The pipeline supports ingestion, preprocessing, validation, and embedding of HR policy documents.
>>>>>>> f4be250ff65f7a0c0977bc35eae49f0207aa0faa

| Stage | Script | Functionality |
|--------|--------|----------------|
| Download | `download_data.py` | Fetches and stores PDFs defined in `url.json` |
| Extraction | `pdf_parser.py` | Extracts structured text and tables from PDFs |
| Preprocessing | `preprocess.py` | Cleans and normalizes extracted text |
| Chunking | `chunker.py` | Splits cleaned text into semantically coherent chunks |
| Validation | `validate_data.py` | Applies schema checks, deduplication, and language filtering |
| Embedding | `store_in_chromadb.py` | Converts validated chunks into vector embeddings stored in ChromaDB |
| Bias Analysis | `data_bias.py` | Performs bias and diversity checks on processed content |

All components pass unit and integration tests under `data_pipeline/tests/` using the following command:

```bash
pytest -v --disable-warnings
```

---

## 3. Dataset Information
<<<<<<< HEAD
=======

### 3.1 Dataset Card
>>>>>>> f4be250ff65f7a0c0977bc35eae49f0207aa0faa

| Attribute | Description |
|------------|-------------|
| **Name** | Deskless Worker Handbook RAG Dataset |
| **Size** | 20 public HR handbooks |
| **Sources** | Employee handbooks from multiple industries |
| **Formats** | PDF, JSONL, CSV |
| **Data Types** | Policy text, metadata, extracted tables |

<<<<<<< HEAD
Example sources include healthcare, retail, manufacturing, construction, and finance company handbooks.

=======
### 3.2 Example Sources
- Healthcare: [Crouse Medical Handbook (2019)](https://crousemed.com/media/1449/cmp-employee-handbook.pdf)  
- Retail: [Lunds & Byerlys Handbook (2019)](https://corporate.lundsandbyerlys.com/wp-content/uploads/2024/05/EmployeeHandbook_20190926.pdf)  
- Manufacturing: [BG Foods Handbook (2022)](https://bgfood.com/wp-content/uploads/2022/01/BG-Employee-Handbook-2022.pdf)  
- Construction: [TNT Construction Handbook (2018)](https://www.tntconstructionmn.com/wp-content/uploads/2018/05/TNT-Construction-Inc-Handbook_Final-2018.pdf)  
- Finance: [Old National Bank Handbook](https://www.oldnational.com/globalassets/onb-site/onb-documents/onb-about-us/onb-team-member-handbook/team-member-handbook.pdf)  

### 3.3 Rights and Privacy
>>>>>>> f4be250ff65f7a0c0977bc35eae49f0207aa0faa
All handbooks are publicly available and used solely for educational and research purposes. No personal or sensitive data is included.

---

<<<<<<< HEAD
## 4. Repository Structure (Updated)

```bash
FrontShiftAI/
│
├── data_pipeline/               # Data ingestion, validation, embedding, bias analysis
│
├── ml_pipeline/                 # Model evaluation, experiment tracking, and registry management
│   ├── evaluation/              # Evaluation modules for RAG, bias, and sensitivity
│   ├── tracking/                # W&B and registry integration
│   ├── utils/                   # Logging and helper utilities
│   ├── eval_pipeline_runner.py  # Orchestrates all evaluation stages
│   └── __init__.py
│
├── models/                      # Temporary model export (from CI/CD)
├── models_registry/             # Versioned model registry with metadata.json
├── wandb/                       # W&B run cache for experiment tracking
│
├── streamlit_app/               # Streamlit interface for RAG and HR chatbot
│   ├── core/
│   │   └── preload.py           # Loads latest model from models_registry and ChromaDB
│   ├── pages/
│   │   ├── admin_admins.py
│   │   ├── admin_companies.py
│   │   ├── admin_users.py
│   │   └── user_chat.py
│   ├── utils/
│   │   ├── auth_utils.py
│   │   └── db_utils.py
│   └── app.py
│
├── .github/
│   └── workflows/
│       └── ci_cd_pipeline.yml   # Unified GitHub Actions pipeline for CI/CD and notifications
│
├── logs/                        # Global logs
├── requirements.txt
├── README.md
└── .env
=======
## 4. Repository Structure

```bash
FrontShiftAI/
├── data_pipeline/
│   ├── airflow/
│   │   ├── dags/
│   │   │   ├── data_pipeline_dag.py              # Main Airflow DAG orchestrating all stages
│   │   │   ├── data_pipeline_VM_dag.py           # Vision model pipeline (future integration)
│   │   │   └── dvc_repro_manual_dag.py           # Lightweight DAG that triggers DVC repro
│   │   ├── airflow.cfg                           # Airflow runtime configuration
│   │   └── README.md                             # Airflow usage and DAG details
│   │
│   ├── config/                                   # Environment and runtime configuration files
│   │   ├── pipeline_config.yaml                  # Config file specifying pipeline stage parameters
│   │   ├── chromadb_settings.yaml                # ChromaDB collection and embedding configuration
│   │   ├── logging_config.yaml                   # Logging format and level configuration
│   │   └── .env.example                          # Example environment file for local use
│   │
│   ├── data/                                     # Data artifacts (auto-created by pipeline)
│   │   ├── url.json                              # Input list of URLs for PDF downloads
│   │   ├── raw/                                  # Source PDF documents (downloaded)
│   │   ├── extracted/                            # Parsed text and table JSON from PDFs
│   │   ├── cleaned/                              # Normalized text data pre-validation
│   │   ├── chunked/                              # Tokenized chunks (JSONL) with metadata
│   │   ├── validated/                            # Final validated chunks + reports (CSV/JSON)
│   │   ├── vector_db/                            # ChromaDB persistent vector database
│   │   ├── bias_reports/                         # Optional bias analysis metrics and plots
│   │   └── tmp/                                  # Temporary working directory for DVC runs
│   │
│   ├── docker/                                   # Docker build assets
│   │   ├── Dockerfile.airflow                    # Airflow scheduler + webserver image
│   │   ├── Dockerfile.vm_api                     # VM API or OCR microservice
│   │   ├── Dockerfile.worker                     # Optional Celery worker image
│   │   └── entrypoint.sh                         # Common startup script for containers
│   │
│   ├── logs/                                     # Pipeline execution logs (auto-generated)
│   │   ├── pipeline_run_YYYYMMDD_HHMM.log        # Run-by-run logs with timestamps
│   │   ├── preprocessing/                        # Logs for text cleaning stage
│   │   ├── validation/                           # Logs for data validation stage
│   │   ├── chromadb/                             # Logs for embedding and storage
│   │   ├── bias_analysis/                        # Logs for bias computation
│   │   └── scheduler/                            # Airflow scheduler logs
│   │
│   ├── plugins/                                  # Airflow custom plugins (optional, can be empty)
│   │   └── __init__.py
│   │
│   ├── scripts/                                  # Core pipeline scripts
│   │   ├── chunker.py                            # Converts cleaned text into semantically meaningful chunks
│   │   ├── data_bias.py                          # Performs bias/fairness analysis (optional)
│   │   ├── download_data.py                      # Fetches all PDFs listed in `url.json`
│   │   ├── pdf_parser.py                         # Extracts text/tables using PyMuPDF, pdfplumber, or Tesseract OCR
│   │   ├── pipeline_runner.py                    # Sequential orchestrator for local/manual runs
│   │   ├── preprocess.py                         # Cleans, deduplicates, and normalizes extracted text
│   │   ├── store_in_chromadb.py                  # Embeds validated text chunks and stores them in ChromaDB
│   │   ├── validate_data.py                      # Validates text chunks, generates quality reports
│   │   ├── VM_api.py                             # Flask/FastAPI app exposing vision/OCR endpoints
│   │   ├── test_rag_llama.py                     # Local test harness for RAG with LLaMA models
│   │   ├── report_generator.py                   # Optional script for summarizing pipeline runs
│   │   └── utils.py                              # Helper utilities for shared functionality
│   │
│   ├── tests/                                    # Pytest-based test suite
│   │   ├── test_download_data.py
│   │   ├── test_pdf_parser.py
│   │   ├── test_preprocess.py
│   │   ├── test_chunker.py
│   │   ├── test_validate_data.py
│   │   ├── test_store_in_chromadb.py
│   │   ├── test_data_bias.py
│   │   └── conftest.py                           # Pytest fixtures and shared setup
│   │
│   ├── utils/                                    # Shared helper modules
│   │   ├── logger.py                             # Custom logger setup for all scripts
│   │   ├── file_ops.py                           # File utilities (safe I/O, hash functions, cleanup)
│   │   ├── validators.py                         # Schema and language validation helpers
│   │   └── constants.py                          # Global constants and paths used across modules
│   │
│   ├── docker-compose.yml                        # Full Docker Compose stack definition
│   ├── docker-manage.sh                          # CLI utility to build/start/stop/clean containers
│   ├── dvc.yaml                                  # DVC stage configuration (extract, preprocess, validate, embed)
│   ├── .env                                      # Environment variables for Docker and Airflow
│   ├── pytest.ini                                # Pytest configuration (markers, logging)
│   ├── requirements.txt                          # Python dependencies
│   └── README.md                                 # Detailed Data Pipeline documentation (this file)
│
├── src/                                          # Future core source modules (e.g., API, agents, RAG)
│   ├── agents/
│   ├── api/
│   ├── rag/
│   ├── utils/
│   └── voice/
│
├── docs/                                         # Documentation and design assets
│   ├── architecture_diagram.png
│   ├── data_flow.md
│   └── structure.md
│
├── models/                                       # Local model weights
│   └── Meta-Llama-3-8B-Instruct.Q4_K_M.gguf
│
├── logs/                                         # Root-level logs (high-level system events)
│
├── .dvcignore                                   # Ignore patterns for DVC
├── .gitignore                                   # Ignore patterns for Git
├── dvc.lock                                     # Auto-generated DVC pipeline state
├── environment.yml                              # Conda environment specification
├── Makefile                                     # Make targets for quick automation
├── License.md                                   # Project license (MIT)
└── requirements.txt                             # Root-level dependency list

>>>>>>> f4be250ff65f7a0c0977bc35eae49f0207aa0faa
```

---

<<<<<<< HEAD
## 5. ML Evaluation and Model Registry Pipeline

### Purpose
The `ml_pipeline/` folder implements an automated model evaluation and versioning system that ensures all models undergo the following processes before being registered.

| Stage | Script | Description |
|--------|---------|-------------|
| RAG Evaluation | `rag_eval_metrics.py` | Tests retrieval and contextual understanding using similarity and precision metrics |
| Bias Detection | `bias_detection.py` | Detects variations in model performance across companies |
| Sensitivity Analysis | `sensitivity_analysis.py` | Checks model robustness to paraphrased queries |
| Unified Summary | `unified_eval_summary.py` | Aggregates metrics and logs to Weights & Biases |
| Model Registry | `push_to_registry.py` | Creates versioned folders under `models_registry/` with metadata and model artifacts |

### Outputs
- `ml_pipeline/evaluation/eval_results/*.csv` and `.json`
- `models/Llama-3.2-3B-Instruct-Q4_K_S.gguf` (temporary)
- `models_registry/llama_3b_instruct_vN/` with `metadata.json` and model weights

Example metadata file:
```json
{
    "model_name": "llama_3b_instruct",
    "version": "v7",
    "timestamp": "2025-11-03T09:25:57",
    "metrics": {
        "mean_semantic_sim": 0.5425,
        "mean_precision_at_k": 1.0
    }
}
```

---

## 6. CI/CD Pipeline (In Review)

The project includes a CI/CD system for automated evaluation, quality gates, and deployment.

**Status:** Implemented but not yet active (awaiting configuration)

**Location:** `ml_pipeline/ci_cd/`

**Documentation:** See `ml_pipeline/ci_cd/README.md` for details

**Activation:** After GitHub Secrets configuration and merge to main branch

---

## 6.1 CI/CD Workflow (GitHub Actions)

A unified CI/CD pipeline automates training, validation, model registry updates, and notifications.  
The workflow runs on every push to `main` or via manual dispatch.

**Note:** Workflows are currently configured to only trigger on the `main` branch. They will not run automatically on feature branches.

### Workflow Stages

```
                          ┌────────────────────────────┐
                          │        GitHub Repo          │
                          │  (FrontShiftAI - main)      │
                          └────────────┬────────────────┘
                                       │
                          ▼──────────────────────────▼
                 ┌─────────────────────────────────────────┐
                 │         CI JOB: Train & Validate         │
                 │─────────────────────────────────────────│
                 │ Checkout repo with Git LFS               │
                 │ Install Python + dependencies            │
                 │ Run eval_pipeline_runner.py              │
                 │ Compute RAG, Bias, Sensitivity metrics   │
                 │ Generate unified_summary.json            │
                 │ Export model and log to W&B              │
                 │ Upload artifacts to GitHub               │
                 └─────────────────────────────────────────┘
                                       │
                                       ▼
                 ┌─────────────────────────────────────────┐
                 │        CD JOB: Deploy to Registry        │
                 │─────────────────────────────────────────│
                 │ Download artifacts                      │
                 │ Verify summary and model files           │
                 │ Push to local model registry             │
                 │ Upload models_registry/ as artifact      │
                 └─────────────────────────────────────────┘
                                       │
                                       ▼
           ┌────────────────────────────────────────────────────┐
           │         NOTIFY JOB: Email Notification              │
           │────────────────────────────────────────────────────│
           │ Runs after both CI + CD                            │
           │ Sends Gmail SMTP message with results              │
           │ Includes unified metrics and status summary        │
           └────────────────────────────────────────────────────┘
```

### Notifications
Email notifications are automatically sent using Gmail SMTP credentials stored in GitHub Secrets:
- `EMAIL_SENDER`
- `EMAIL_PASSWORD`
- `EMAIL_RECEIVER`

These contain build results, mean semantic similarity, precision@k, and model registry version.

---

## 7. Streamlit Application Integration

The Streamlit app dynamically loads the **latest registered model** and ChromaDB collection.  
The preload script now automatically detects the latest version from `models_registry/`:

```python
# streamlit_app/core/preload.py

def get_latest_model_path():
    versions = sorted(MODELS_DIR.glob("llama_3b_instruct_v*"), reverse=True)
    latest = versions[0]
    model_file = next(latest.glob("*.gguf"), None)
    return model_file
```

This ensures that whenever CI/CD registers a new model, the Streamlit application automatically uses it without manual updates.

---

## 8. Running the Pipelines
=======
## 5. Running the Pipeline
>>>>>>> f4be250ff65f7a0c0977bc35eae49f0207aa0faa

```bash
# Clone the repository
git clone https://github.com/MLOpsGroup9/FrontShiftAI.git
cd FrontShiftAI

<<<<<<< HEAD
# Environment setup
=======
# Set up environment
>>>>>>> f4be250ff65f7a0c0977bc35eae49f0207aa0faa
conda create -n frontshiftai python=3.12 -y
conda activate frontshiftai
pip install -r requirements.txt

<<<<<<< HEAD
# Run data pipeline
dvc repro

# Run model evaluation
python ml_pipeline/eval_pipeline_runner.py

# Launch Streamlit interface
streamlit run streamlit_app/app.py
```

---

## 9. Testing and Validation

Run all pipeline and ML evaluation tests:

```bash
pytest -v --disable-warnings
```

To verify coverage:

```bash
pytest --cov=data_pipeline --cov=ml_pipeline --cov-report=term-missing
```

---

## 10. License

This project is released under the MIT License.  
See `License.md` for details.

---

## 11. Repository

=======
# Pull versioned data
dvc pull

# Run the pipeline manually
python data_pipeline/scripts/pipeline_runner.py

# Or reproduce via DVC
dvc repro

# Optional: Trigger using Airflow
export AIRFLOW_HOME=./data_pipeline/airflow
airflow db init
airflow scheduler &
airflow webserver --port 8080 &
```

All logs and reports are stored under `data_pipeline/logs/`, and validation metrics are written to `validation_report.csv`.

---

## 6. Testing and Continuous Integration

All pipeline stages are validated through automated tests.  
Run the full test suite:

```bash
pytest -v --disable-warnings
```

To view code coverage:

```bash
pytest --cov=data_pipeline.scripts --cov-report=term-missing
```

Example CI configuration (GitHub Actions):

```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: pytest -v --disable-warnings
```

---

## 7. License

This project is released under the MIT License.  
See `License.md` for details.

---

## 8. Repository

>>>>>>> f4be250ff65f7a0c0977bc35eae49f0207aa0faa
https://github.com/MLOpsGroup9/FrontShiftAI
