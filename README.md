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
- **Comprehensive Monitoring**: Full-stack observability with W&B and GCP Alerts  

An optional Airflow DAG (`dvc_repro_manual_dag.py`) in `data_pipeline/dags/` can automatically trigger the pipeline when new URLs are added to `data_pipeline/data/url.json`, or it can be triggered manually via the Airflow UI.

---

## 2. System Architecture & Data Flow

### 2.1 High-Level Overview

The system follows a microservices-based architecture deployed on Google Cloud Platform (Cloud Run), consisting of three main pillars:
1.  **Frontend (React)**: User interface for employees and admins.
2.  **Backend (FastAPI)**: Central API gateway, agent orchestration, and business logic.
3.  **Data Pipeline (Python/Airflow)**: Asynchronous processing of handbook PDFs into vector embeddings.

### 2.2 Request Flow

1.  **User Interaction**: A user sends a message via the Frontend (e.g., "What is the PTO policy?").
2.  **API Gateway**: The request hits the Backend API (`/api/chat/message`).
3.  **Unified Agent Router**: The system analyzes the intent using an LLM to route the request:
    *   **RAG Agent**: For policy questions (uses ChromaDB).
    *   **PTO Agent**: For time-off requests (uses SQL Database).
    *   **HR Ticket Agent**: For support tickets (uses SQL Database).
4.  **Response Generation**: The selected agent processes the request and generates a response, which is sent back to the Frontend.

### 2.3 RAG & Fallback Mechanism

When a user asks a question that requires external knowledge:
1.  **Vector Search**: The RAG Agent searches the **ChromaDB** vector store for relevant handbook chunks.
2.  **Context Construction**: Retrieved chunks are combined with the user's query.
3.  **LLM Generation**: The LLM generates an answer based *only* on the provided context.
4.  **Automatic Fallback**: If the RAG Agent finds no relevant information:
    *   The system automatically triggers the **Website Extraction Agent**.
    *   It searches the company's public website (via Brave Search API) for operational details (e.g., office hours, phone numbers).
    *   This ensures users get an answer even if it's not in the handbook.

### 2.4 Background Processing (Company Ingestion)

When a new company is added via the Admin Dashboard:
1.  **API Request**: Admin submits company details and handbook URL.
2.  **Task Queue**: The Backend pushes a task to **Redis**.
3.  **Celery Worker**: A background worker picks up the task.
4.  **Data Pipeline Execution**:
    *   Downloads the PDF.
    *   Extracts text and tables.
    *   Chunks and validates data.
    *   Generates embeddings.
    *   Updates the ChromaDB vector store.
5.  **Completion**: The company is now live, and its employees can start using the RAG system immediately.

---

## 3. Monitoring & Observability

The system includes a robust monitoring layer using **Google Cloud Monitoring** and **Weights & Biases (W&B)** to track system health and business metrics.

### Key Metrics Tracked:
*   **Infrastructure**: Cloud Run CPU/Memory, Request counts, Latency.
*   **Application**: API endpoint performance, specific Agent execution times.
*   **Business**: PTO requests created/approved, HR tickets resolved.
*   **Alerts**: Automated emails for high error rates (>10/min) or latency spikes (>3s).

---

## 4. Automated Data Pipeline Overview

The data pipeline is fully modular, test-driven, and reproducible. Each stage is independently testable using `pytest`. The pipeline supports ingestion, preprocessing, validation, and embedding of HR policy documents.

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

## 5. Dataset Information

### 5.1 Dataset Card

| Attribute | Description |
|------------|-------------|
| **Name** | Deskless Worker Handbook RAG Dataset |
| **Size** | 20 public HR handbooks |
| **Sources** | Employee handbooks from multiple industries |
| **Formats** | PDF, JSONL, CSV |
| **Data Types** | Policy text, metadata, extracted tables |

### 5.2 Example Sources
- Healthcare: [Crouse Medical Handbook (2019)](https://crousemed.com/media/1449/cmp-employee-handbook.pdf)  
- Retail: [Lunds & Byerlys Handbook (2019)](https://corporate.lundsandbyerlys.com/wp-content/uploads/2024/05/EmployeeHandbook_20190926.pdf)  
- Manufacturing: [BG Foods Handbook (2022)](https://bgfood.com/wp-content/uploads/2022/01/BG-Employee-Handbook-2022.pdf)  
- Construction: [TNT Construction Handbook (2018)](https://www.tntconstructionmn.com/wp-content/uploads/2018/05/TNT-Construction-Inc-Handbook_Final-2018.pdf)  
- Finance: [Old National Bank Handbook](https://www.oldnational.com/globalassets/onb-site/onb-documents/onb-about-us/onb-team-member-handbook/team-member-handbook.pdf)  

### 5.3 Rights and Privacy
All handbooks are publicly available and used solely for educational and research purposes. No personal or sensitive data is included.

---

## 6. Repository Structure

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
├── backend/                                      # FastAPI Backend Application
│   ├── agents/                                   # AI Agents (PTO, HR Ticket, Website Extraction)
│   ├── api/                                      # API Routes
│   ├── db/                                       # Database Models & Connection
│   ├── jobs/                                     # Background Workers (Celery)
│   ├── services/                                 # Business Logic
│   └── main.py                                   # App Entry Point
│
├── frontend/                                     # React Frontend Application
│   ├── src/
│   │   ├── components/                           # UI Components
│   │   ├── services/                             # API Client
│   │   └── App.jsx                               # Main Component
│   └── vite.config.js                            # Build Config
│
├── deployment/                                   # Deployment Documentation & Scripts
│   ├── README.md                                 # Deployment Guide
│   └── todo.md                                   # Project Status & Todo
│
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

```

---

## 7. Running the Pipeline

```bash
# Clone the repository
git clone https://github.com/MLOpsGroup9/FrontShiftAI.git
cd FrontShiftAI

# Set up environment
conda create -n frontshiftai python=3.12 -y
conda activate frontshiftai
pip install -r requirements.txt

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

## 8. Testing and Continuous Integration

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

## 9. License

This project is released under the MIT License.  
See `License.md` for details.

---

## 10. Repository

https://github.com/MLOpsGroup9/FrontShiftAI
