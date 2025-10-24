![Python](https://img.shields.io/badge/Python-3.10+-blue)
![DVC](https://img.shields.io/badge/Data%20Version%20Control-DVC-orange)
![LangChain](https://img.shields.io/badge/LangChain-Enabled-success)
![ChromaDB](https://img.shields.io/badge/Vector%20DB-ChromaDB-green)
![Status](https://img.shields.io/badge/Status-In%20Development-yellow)

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

Deskless workers face limited access to HR systems due to **irregular schedules, lack of computer access, and fragmented communication**.  

These challenges lead to:  
- Lower benefits enrollment/utilization  
- Poor training adoption  
- High attrition and disengagement  

**Proposed Solution:**  
- **RAG core** → Retrieves grounded answers from HR docs and policies.  
- **Agentic layer (planned)** → Executes actions like scheduling, compliance checks, escalation.  
- **Voice interaction (planned)** → Enables hands-free access for frontline roles.  

The project includes an optional **Airflow DAG (`dvc_repro_manual_dag.py`)** located under `data_pipeline/airflow/dags/`.  
This DAG automatically triggers the DVC pipeline when new URLs are added to `data_pipeline/data/url.json`, or can be triggered manually through the Airflow UI.

---

## 2. Dataset Information

### 2.1 Dataset Card
| Attribute | Description |
|------------|-------------|
| **Name** | Deskless Worker Handbook RAG document dataset |
| **Size** | 20 public HR handbooks (PDFs) |
| **Sources** | Publicly available employee handbooks (healthcare, retail, logistics, hospitality, finance, construction, etc.) |
| **Formats** | PDF (retrieval embedding) |
| **Data Types** | Natural language questions, concise answers, metadata (source, industry, section) |

### 2.2 Example Sources
- Healthcare: [Crouse Medical Handbook (2019)](https://crousemed.com/media/1449/cmp-employee-handbook.pdf)  
- Retail: [Lunds & Byerlys Handbook (2019)](https://corporate.lundsandbyerlys.com/wp-content/uploads/2024/05/EmployeeHandbook_20190926.pdf)  
- Manufacturing: [BG Foods Handbook (2022)](https://bgfood.com/wp-content/uploads/2022/01/BG-Employee-Handbook-2022.pdf)  
- Construction: [TNT Construction Handbook (2018)](https://www.tntconstructionmn.com/wp-content/uploads/2018/05/TNT-Construction-Inc-Handbook_Final-2018.pdf)  
- Hospitality: [Alta Peruvian Lodge Handbook (2016)](https://www.altaperuvian.com/wp-content/uploads/2017/01/APL-Empl-Manual-Revised-12-22-16-fixed.pdf)  
- Finance: [Old National Bank Handbook](https://www.oldnational.com/globalassets/onb-site/onb-documents/onb-about-us/onb-team-member-handbook/team-member-handbook.pdf)  

### 2.3 Rights & Privacy
- **Source Material**: All handbooks are public PDFs.  
- **Usage**: Research/educational only.  
- **Privacy**: No personal data; only policy text.  
- **Compliance**: GDPR/CCPA principles respected.  

---

## 3. Data Planning and Splits

### 3.1 Preprocessing Steps
- Extract text and tables from HR and policy PDFs using LangChain’s `PyPDFLoader` and Camelot.  
- Clean and normalize text (remove headers, footers, duplicates, and formatting artifacts).  
- Split text into context-preserving chunks using `RecursiveCharacterTextSplitter` for efficient retrieval and embedding.  
- Store structured outputs (`combined_chunks.json`, `table_chunks.json`, and `cleaned_chunks.csv`) for downstream validation and vectorization.  
- Validate cleaned data using schema-based checks (Pydantic), language detection (langdetect), and deduplication.  
- Store fully validated chunks in `data/validated/` for downstream embedding.  

When new URLs are appended to `url.json`, the pipeline can be re-run automatically through the Airflow DAG, ensuring new documents are extracted, validated, and embedded without manual intervention.

---

## 4. Problems & Current Solutions

| Existing Systems | Limitations |
|------------------|--------------|
| **HCM Suites (Workday, SAP)** | Admin-focused, vendor-locked |
| **Enterprise Assistants (Oracle DA)** | Rigid, schema-bound |
| **LMS Microlearning (Docebo, Cornerstone)** | Static, non-queryable |
| **Generic Chatbots (Leena AI, Talla)** | FAQ-only, no grounding |
| **Self-Service Portals** | Desktop-centric, not conversational |
| **Slack/Teams** | Transient, non-retrievable |

---

## 5. Proposed Solution

- **RAG for grounded answers** (cited, accurate)  
- **Agentic orchestration** for HR workflows (scheduling, compliance, escalation)  
- **Personalization & memory** for context-aware Q&A  
- **System integration** with HRIS, LMS, calendars  
- **Safe fallback** when confidence is low  
- **Voice accessibility** for frontline workers  
- **Data validation pipeline** ensures only schema-compliant, English, deduplicated chunks reach embeddings.  
- **Automated run orchestrator** (`run_pipeline.py`) executes all stages sequentially and logs results for reproducibility.  

---

## 6. Deployment Infrastructure

- **Backend**: FastAPI on GKE  
- **RAG**: Hugging Face embeddings + ChromaDB (GKE)  
- **LLM**: LLaMA-3 8B (Vertex AI endpoint)  
- **Agents**: LangChain/LangGraph on GKE  
- **Voice**: Google Cloud STT/TTS  
- **Data**: GCS (docs), Cloud SQL (metadata), JSONL/CSV  
- **Monitoring**: Cloud Monitoring, Prometheus/Grafana, Vertex AI drift detection  
- **Local pipeline automation**: `run_pipeline.py` executes all stages sequentially with timestamped logs.  
- **Airflow orchestration**: Optional DAG (`dvc_repro_manual_dag.py`) automatically triggers the pipeline when new entries appear in `url.json`, or can be manually triggered from the Airflow UI (`localhost:8080`).  
- **Data versioning**: DVC integrated with `.dvc` tracking for `raw`, `extracted`, `cleaned`, `validated`, and `vector_db`.  

---

## 7. Monitoring Plan

- Track retrieval recall, hallucination, tool accuracy, fallback rate, WER, latency.  
- GCP Cloud Monitoring alerts + Grafana dashboards.  
- Future: drift detection, detailed audit logs.  
- Track data validation metrics (invalid chunk ratio, duplicate rate, missing schema fields).  
- Log pipeline runs with timestamps and stage statuses in `data_pipeline/logs/`.  

---

## 8. Repository Structure

```bash
FrontShiftAI/
├── data_pipeline/
│   ├── airflow/
│   │   └── dags/
│   │       └── dvc_repro_manual_dag.py
│   ├── data/
│   │   ├── raw/
│   │   ├── extracted/
│   │   ├── cleaned/
│   │   ├── validated/
│   │   └── vector_db/
│   ├── logs/
│   ├── scripts/
│   │   ├── data_extraction.py
│   │   ├── preprocess.py
│   │   ├── store_in_chromadb.py
│   │   ├── validate_data.py
│   │   ├── run_pipeline.py
│   │   └── test_rag_llama.py
│   ├── tests/
│   ├── utils/
│   │   └── logger.py
│   ├── airflow.cfg
│   ├── pytest.ini
│   └── README.md
│
├── src/
│   ├── agents/
│   ├── api/
│   ├── rag/
│   ├── utils/
│   └── voice/
│
├── docs/
│   └── structure.md
│
├── models/
│   └── Meta-Llama-3-8B-Instruct.Q4_K_M.gguf
│
├── logs/
├── .dvcignore
├── .gitignore
├── dvc.lock
├── dvc.yaml
├── environment.yml
├── License.md
├── Makefile
├── README.md
└── requirements.txt
```

---

## 9. End-to-End Pipeline Summary

| Stage | Script | Input | Output | Tools |
|--------|--------|--------|--------|--------|
| Extraction | `data_extraction.py` | PDFs (`data/raw/`) | `combined_chunks.json`, `table_chunks.json` | LangChain, Camelot |
| Preprocessing | `preprocess.py` | Extracted JSON | `cleaned_chunks.csv` | Pandas |
| Validation | `validate_data.py` | Cleaned CSV | Validated JSON + `validation_report.csv` | Pydantic, LangDetect |
| Embedding | `store_in_chromadb.py` | Validated JSON | ChromaDB Collection | SentenceTransformer |
| Test RAG | `test_rag_llama.py` | ChromaDB + Model | Interactive Q&A | LLaMA 3, Chroma |
| Orchestration | `run_pipeline.py` | — | Logs, Full Run | Python subprocess |
| Trigger (Airflow) | `dvc_repro_manual_dag.py` | `url.json` | Auto pipeline trigger | Airflow + DVC |

---

## 10. Cloning and Running the Project

```bash
# Clone repository
git clone https://github.com/MLOpsGroup9/FrontShiftAI.git
cd FrontShiftAI

# Create environment
conda create -n frontshiftai python=3.10 -y
conda activate frontshiftai
pip install -r requirements.txt

# Pull versioned data
dvc pull

# Run pipeline manually
python data_pipeline/scripts/run_pipeline.py

# OR reproduce via DVC
dvc repro

# (Optional) Trigger Airflow for automation
export AIRFLOW_HOME=./data_pipeline/airflow
airflow db init
airflow scheduler &
airflow webserver --port 8080 &
```

---

## 11. Success & Acceptance Criteria

TBD

---

## 12. License

This project is released under the **MIT License**.  
See `License.md` for full terms.

---

## 🔗 Repository

👉 [FrontShiftAI GitHub](https://github.com/MLOpsGroup9/FrontShiftAI)
