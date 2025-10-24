# FrontShiftAI Data Pipeline

> **FrontShiftAI** is a modular, data-centric pipeline for processing and embedding organizational policy documents into a ChromaDB vector store.  
> It automates ingestion, extraction, validation, and embedding using Python and DVC, with optional Airflow orchestration for automated triggers.

This repository contains the data pipeline component of the FrontShiftAI project. The pipeline focuses on document ingestion, preprocessing, validation, and vector storage for a Retrieval-Augmented Generation (RAG) system. The current implementation covers all stages up to embedding and storage.  
An **optional Airflow DAG (`dvc_repro_manual_dag.py`)** is included, which can be triggered manually or automatically when new URLs are added to `data_pipeline/data/url.json`.

---

## 1. Project Overview

The data pipeline automates the following steps:

1. Document extraction from policy and HR PDF files.
2. Text and table parsing using LangChain and Camelot.
3. Cleaning, normalization, and schema validation.
4. Data versioning and reproducibility with DVC.
5. Embedding generation and vector storage in ChromaDB.
6. Centralized logging and basic testing for reliability.
7. Optional Airflow orchestration for automation.

---

## 2. Directory Structure

```
FrontShiftAI/
├── data_pipeline/
│   ├── airflow/                  # Airflow DAGs for manual/auto pipeline triggers
│   │   └── dags/
│   │       └── dvc_repro_manual_dag.py   # Triggers DVC repro + push when url.json changes
│   ├── data/
│   │   ├── raw/                  # Source PDF documents
│   │   ├── extracted/            # Extracted text and tables
│   │   ├── cleaned/              # Normalized text chunks
│   │   ├── validated/ 
│   │   └── vector_db/            # ChromaDB persistent storage
│   ├── logs/                     # Pipeline log files
│   ├── scripts/                  # Modular pipeline scripts
│   │   ├── data_extraction.py
│   │   ├── preprocess.py
│   │   ├── validate_data.py
│   │   ├── store_in_chromadb.py
│   │   └── run_pipeline.py
│   ├── tests/                    # Unit and integration tests
│   ├── utils/                    # Logger and helper functions
│   │   └── logger.py
│   ├── dvc.yaml                  # DVC pipeline configuration
│   ├── __init__.py
│   └── README.md
├── requirements.txt
└── environment.yml
```

---

## 3. Environment Setup

```bash
# Create and activate environment
conda create -n frontshiftai python=3.10
conda activate frontshiftai

# Install dependencies
pip install -r requirements.txt
```

---

## 4. Quick Start for New Users (Cloning the Repo)

```bash
# Clone the repository
git clone https://github.com/MLOpsGroup9/FrontShiftAI.git
cd FrontShiftAI

# Setup environment
conda activate frontshiftai  # or use pyenv activate frontshiftai
pip install -r requirements.txt

# Pull data from DVC remote
dvc pull

# Run the full pipeline
dvc repro
```

To test individual stages:
```bash
python data_pipeline/scripts/data_extraction.py
python data_pipeline/scripts/preprocess.py
python data_pipeline/scripts/validate_data.py
python data_pipeline/scripts/store_in_chromadb.py
```

---

## 5. Automated Pipeline Runner

The pipeline includes a standalone orchestrator script (`run_pipeline.py`) for **local automation**.

### Run locally without Airflow

```bash
python data_pipeline/scripts/run_pipeline.py
```

**Functionality:**
- Sequentially executes all core stages:
  1. `data_extraction.py`
  2. `preprocess.py`
  3. `validate_data.py`
  4. `store_in_chromadb.py`
- Stops immediately if any stage fails.
- Logs output to `data_pipeline/logs/pipeline_<timestamp>.log`.

**Example log:**
```
2025-10-24 14:33:15 INFO - Extracted 12 PDFs successfully.
2025-10-24 14:34:02 INFO - Preprocessed 4,830 text chunks.
2025-10-24 14:35:22 INFO - Validated 4,700 chunks (130 dropped).
2025-10-24 14:36:05 INFO - Stored 4,700 embeddings in ChromaDB.
```

---

## 6. Airflow DAG (Optional Orchestration)

An optional **Apache Airflow DAG** (`dvc_repro_manual_dag.py`) is provided for automation.

### Purpose
- Automates the DVC pipeline when new URLs are added to `data_pipeline/data/url.json`.
- Can also be triggered manually from the Airflow web UI.

### Behavior
1. Detects changes in `url.json`.
2. Executes:
   ```bash
   dvc repro
   dvc push
   git add dvc.lock
   git commit -m "Reproduce pipeline after new URLs added"
   ```
3. Logs progress within the Airflow UI.

### Setup

```bash
export AIRFLOW_HOME=/Users/sriks/Documents/Projects/FrontShiftAI/data_pipeline/airflow
airflow db init

# Create user
airflow users create --username krishna --firstname Krishna --lastname FrontShiftAI --role Admin --email krishna@frontshiftai.com --password airflow

# Start Airflow services
airflow scheduler &
airflow webserver --port 8080 &
```

Access the UI at [http://localhost:8080](http://localhost:8080)  
and trigger the DAG: **`dvc_repro_manual_dag`**

---

## 7. Reproducibility and DVC Setup

The project ensures reproducibility via deterministic DVC stages.

```bash
# Add and configure DVC remote storage
dvc remote add -d local_storage ../dvc_storage

# Reproduce pipeline
dvc repro
```

All stages are declared in `dvc.yaml`.

---

## 8. Troubleshooting

### Import Errors
If you see:
```
ModuleNotFoundError: No module named 'data_pipeline'
```
Add this to the top of your script:
```python
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
```

### LangChain Import Change
If you’re using LangChain >= 0.1.0, replace:
```python
from langchain.document_loaders import PyPDFLoader
```
with:
```python
from langchain_community.document_loaders import PyPDFLoader
```

---

## 9. Bias and Fairness (Appendix)

The current FrontShiftAI pipeline processes organizational policy documents that contain no demographic or decision-making data.  
Hence, no bias analysis across subgroups applies at this stage.  
Future modules (e.g., Q&A systems or user feedback-based fine-tuning) will integrate **Fairlearn** or **TFMA** for fairness evaluation.

---

## 10. License

This project is released under the **MIT License**.  
See `License.md` for details.

---

## 11. Commands Reference Summary

| Purpose | Command |
|----------|----------|
| **Setup Environment** | `conda create -n frontshiftai python=3.10` |
| **Activate Env** | `conda activate frontshiftai` |
| **Install Dependencies** | `pip install -r requirements.txt` |
| **Pull Versioned Data** | `dvc pull` |
| **Run Full Pipeline** | `dvc repro` |
| **Run Manually** | `python data_pipeline/scripts/run_pipeline.py` |
| **Trigger via Airflow** | `airflow dags trigger dvc_repro_manual_dag` |
| **Start Webserver** | `airflow webserver --port 8080` |
| **Start Scheduler** | `airflow scheduler` |
| **Commit Lockfile** | `git add dvc.lock && git commit -m "Reproduce pipeline"` |

---

## 12. When Others Clone This Repo

Steps for any collaborator or new user:

```bash
git clone https://github.com/MLOpsGroup9/FrontShiftAI.git
cd FrontShiftAI

# Create environment
conda create -n frontshiftai python=3.10
conda activate frontshiftai
pip install -r requirements.txt

# Pull versioned data and reproduce pipeline
dvc pull
dvc repro

# (Optional) Trigger pipeline automatically when url.json changes
export AIRFLOW_HOME=./data_pipeline/airflow
airflow db init
airflow scheduler &
airflow webserver --port 8080 &
```

---

## 13. Contributing

Contributions are welcome!  
1. Fork the repo  
2. Create a branch (`feature/new-component`)  
3. Submit a Pull Request  

---
