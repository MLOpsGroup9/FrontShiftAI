# FrontShiftAI Data Pipeline

This repository contains the data pipeline component of the FrontShiftAI project. The pipeline focuses on document ingestion, preprocessing, validation, and vector storage for a Retrieval-Augmented Generation (RAG) system. The current implementation covers all stages up to embedding and storage. Airflow DAG orchestration will be integrated in a later stage.

## 1. Project Overview

The data pipeline automates the following steps:

1. Document extraction from policy and HR PDF files.
2. Text and table parsing using LangChain and Camelot.
3. Cleaning, normalization, and schema validation.
4. Data versioning and reproducibility with DVC.
5. Embedding generation and vector storage in ChromaDB.
6. Centralized logging and basic testing for reliability.

## 2. Directory Structure

```
FrontShiftAI/
├── data_pipeline/
│   ├── dags/                     # Airflow DAGs (to be implemented)
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
        ├── run_pipeline.py
│   │   └── test_rag_llama.py
│   ├── tests/                    # Unit and integration tests
│   │   ├── test_data_extraction.py
│   │   ├── test_preprocess.py
│   │   └── test_pipeline_integration.py
│   ├── utils/                    # Logger and helper functions
│   │   └── logger.py
│   ├── dvc.yaml                  # DVC pipeline configuration
│   ├── __init__.py
│   └── README.md

```

## 3. Environment Setup

```
conda create -n frontshiftai python=3.10
conda activate frontshiftai
pip install -r requirements.txt
```

All necessary dependencies for LangChain, ChromaDB, Great Expectations, DVC, and supporting tools are listed in `requirements.txt` and `environment.yml`.

## 4. Pipeline Execution

The pipeline is tracked and reproduced using Data Version Control (DVC). Each stage can be executed individually or through the full workflow.

```
dvc repro
```

This command executes the defined stages:
1. Data extraction  
2. Preprocessing  
3. Validation  
4. Vector storage  

If new PDFs are added to `data/raw/`, DVC automatically detects changes and re-runs the dependent stages.

## 5. Components and Functionality

### a. Data Extraction
- Extracts text and tables from PDF documents.
- Uses LangChain’s `PyPDFLoader` and Camelot for structured parsing.
- Splits text into context-preserving chunks using `RecursiveCharacterTextSplitter`.
- Outputs `combined_chunks.json` and `table_chunks.json` to `data/extracted/`.

### b. Preprocessing
- Cleans and normalizes extracted text.
- Consolidates data into a structured DataFrame.
- Outputs `cleaned_chunks.csv` to `data/cleaned/`.

### c. Data Validation
- Validates cleaned chunks against a defined schema (`PolicyChunk`) using **Pydantic**.
- Checks for:
  - Non-empty text fields
  - Minimum word count (default: 30 words)
  - English language content (via `langdetect`)
  - JSON schema consistency across all records
- Automatically cleans minor formatting artifacts (bullets, line breaks).
- Generates a validation summary report at `logs/validation_report.csv`.
- Outputs fully validated JSON files to `data/validated/`.
- Deduplicates valid chunks before embedding.

This ensures that only clean, language-verified, schema-compliant text is passed to the embedding and retrieval stages.

✅ 2. Add a new section — “Pipeline Runner (Automation)”

Append after the “Reproducibility” section, since it ties into automation.

### d. Vector Storage
- Embeds cleaned text chunks using SentenceTransformer embeddings.
- Stores embeddings and metadata into a persistent ChromaDB instance at `data/vector_db/`.
- Supports subsequent retrieval for RAG applications.

### e. Logging and Error Handling
- Uses a centralized logger located in `data_pipeline/utils/logger.py`.
- Logs to both console and `logs/pipeline.log`.
- Handles missing data, failed table extractions, and malformed inputs gracefully.
- Logs are timestamped and categorized by severity level.

### f. Testing
- Unit tests validate the extraction, preprocessing, and integration stages.
- `pytest` is included in requirements for automated test execution.

### g. Reproducibility and Data Versioning
- DVC tracks all data directories (`raw`, `extracted`, `cleaned`, `vector_db`).
- `.dvc` files manage data versioning without committing large binaries to Git.
- Pipeline stages are defined declaratively in `dvc.yaml`.
- A local DVC remote (`../dvc_storage`) is configured for versioned data storage.

### h. Planned Extensions
- Airflow DAGs will orchestrate the pipeline in future releases.
- Slack or email alerting will be integrated for anomaly detection and failure notifications.
- Model retraining and drift detection will be added to the monitoring layer.

## 6. Reproducibility

The project ensures full reproducibility through:
- Deterministic pipeline stages managed by DVC.
- Environment files (`requirements.txt`, `environment.yml`) specifying exact dependencies.
- Modular code organization with explicit inputs and outputs for each step.

Reproduction steps on a new machine:

```
git clone <repository-url>
cd FrontShiftAI
conda env create -f environment.yml
conda activate frontshiftai
dvc pull
dvc repro
```

## 7. Code Style and Modularity

The code follows PEP 8 standards and modular programming practices. Each script contains a clearly defined `main()` function and is independently executable. Shared functionality (logging, utilities) is placed in the `utils` module. The pipeline can be extended or modified with minimal coupling between stages.

## 8. Error Handling and Logging

Comprehensive error handling ensures robustness against missing data, file corruption, or extraction failures. Logging captures:
- Data ingestion progress
- Extraction and validation warnings
- Exceptions and recovery attempts

All logs are stored in `logs/pipeline.log` for debugging and audit purposes.

## 9. License

This project is released under the MIT License. See `License.md` for details.


## 10. Automated Pipeline Runner

For local automation without Airflow, the pipeline includes a standalone orchestrator script:


### Functionality:
- Sequentially executes all stages:
  1. `data_extraction.py`
  2. `preprocess.py`
  3. `validate_data.py`
  4. `store_in_chromadb.py`
- Stops immediately if any stage fails.
- Logs all console output to a timestamped file under `logs/`, e.g.:
- Each stage can be run independently for debugging, while `run_pipeline.py` serves as a lightweight alternative to Airflow DAG orchestration.

This script provides full reproducibility for local experiments without needing a cloud scheduler or CI/CD triggers.


## 11. Known Issues and Troubleshooting

**1. `ModuleNotFoundError: No module named 'data_pipeline'`**
- Add this snippet to the top of each script:
  ```python
  import sys, os
  sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from langchain.document_loaders import PyPDFLoader >> from langchain_community.document_loaders import PyPDFLoader





## Bias Detection Summary:
The current FrontShiftAI RAG pipeline processes organizational policy documents without demographic attributes or decision-making components. Hence, no bias analysis across user subgroups applies at this stage.
Future extensions (e.g., user feedback-based fine-tuning or Q&A classification) will integrate Fairlearn or TFMA for bias detection and fairness evaluation across demographic slices.


