# FrontShiftAI Data Pipeline (The "Librarian")

> End-to-end ingestion, OCR, cleansing, validation, and embedding of organisational policy documents, packaged for both local development and containerised deployment.

This is the system responsible for reading thousands of PDF pages, organizing them, and "indexing" them so the Chat Agents can find answers instantly.

This README covers:
1.  **Architecture overview**
2.  **Prerequisites** (Docker recommended)
3.  **Quickstart**

---

## 1. Architecture Overview

The pipeline processes PDF handbooks into a searchable vector store in seven stages:

| Stage | Script | Purpose |
|-------|--------|---------|
| Download | `scripts/download_data.py` | Fetch PDFs from `data/url.json` into `data/raw/`. |
| OCR Parsing | `scripts/pdf_parser.py` | Extract text/tables (Tesseract + PyMuPDF). |
| Preprocess | `scripts/preprocess.py` | Clean and normalize text. |
| Chunking | `scripts/chunker.py` | Break text into "bite-sized" pieces for the AI. |
| Validation | `scripts/validate_data.py` | Quality checks (remove junk). |
| Bias Analysis | `scripts/data_bias.py` | Ensure fairness in the data. |
| Vector Store | `scripts/store_in_chromadb.py` | Save to ChromaDB (the "Library"). |

Two orchestration layers ship with the repo:
- **`scripts/pipeline_runner.py`** runs every stage sequentially (ideal for local dev).
- **Airflow DAGs** (`dags/data_pipeline_dag.py`) for production scheduling.

---

## 2. Repository Layout

See the [Root README](../README.md) for the high-level project structure.

```bash
data_pipeline/
├── dags/                  # Airflow scheduling logic
├── data/
│   ├── raw/              # Original PDFs
│   ├── validated/        # Cleaned chunks
│   └── vector_db/        # The final "database" used by the Chat bot
│   ├── logs/
│   │   ├── bias_analysis/
│   │   ├── download_data_log/
│   │   ├── preprocessing/
│   │   ├── validation/
│   │   └── pipeline_run_*.log
│   ├── scripts/
│   │   ├── chunker.py
│   │   ├── data_bias.py
│   │   ├── download_data.py
│   │   ├── pdf_parser.py
│   │   ├── pipeline_runner.py
│   │   ├── preprocess.py
│   │   ├── store_in_chromadb.py
│   │   ├── validate_data.py
│   │   ├── test_rag_llama.py
│   │   └── VM_api.py
│   ├── tests/
│   └── utils/
│       └── logger.py
│
├── docs/
├── models/
├── src/
├── Makefile
├── dvc.yaml
├── requirements.txt
└── README.md

```

Path-sensitive tooling (Docker, scripts) assumes this layout. Do **not** rename or move subdirectories unless you update the associated configuration.

---

## 3. Prerequisites

### Hardware / OS

- macOS Ventura or later (Apple Silicon and Intel tested)
- Ubuntu 22.04 LTS or similar Debian-based distro
- Windows 11 with WSL2 and Docker Desktop
- ≥ 4 CPU cores, ≥ 8 GB RAM, ≥ 15 GB free disk

### Packages & Tools

| Component | Purpose | macOS | Ubuntu/Debian | Windows (WSL2) |
|-----------|---------|-------|---------------|----------------|
| Python 3.12 | Local dev/tests | `brew install python@3.12` | `sudo apt install python3.12 python3.12-venv` | Use `pyenv` or official installer inside WSL |
| pip | Package install | Bundled with Python | `sudo apt install python3-pip` | Bundled |
| Tesseract OCR | PDF OCR fallback | `brew install tesseract` | `sudo apt install tesseract-ocr` | `sudo apt install tesseract-ocr` inside WSL |
| Poppler utils (optional but recommended for pdfplumber) | PDF parsing | `brew install poppler` | `sudo apt install poppler-utils` | `sudo apt install poppler-utils` inside WSL |
| Docker Desktop | Container runtime | [Download](https://www.docker.com/products/docker-desktop/) | `sudo apt install docker.io docker-compose-plugin` | Docker Desktop for Windows |
| Git | Source control | `brew install git` | `sudo apt install git` | Included |

### Python Dependencies

All Python packages are pinned in `data_pipeline/requirements.txt`. You’ll install them later either inside Docker or into a virtual environment.

---

## 4. Docker-First Quickstart (Recommended)

Docker ensures consistent environments across machines. All paths below are relative to the repository root unless noted.

### 4.1 Clone and Prepare

```bash
git clone https://github.com/MLOpsGroup9/FrontShiftAI.git
cd FrontShiftAI
```

Review and customise `data_pipeline/.env` if needed (e.g. change Airflow credentials or ports). Defaults work for most cases.

### 4.2 Start the Stack

```bash
cd data_pipeline
./docker-manage.sh check            # verifies Docker/Compose availability
./docker-manage.sh build            # builds Airflow + VM API images
./docker-manage.sh start            # starts all services in the background
```

To confirm:

```bash
docker compose -f docker-compose.yml ps
```

### 4.3 Services & Ports

| Service | URL | Notes |
|---------|-----|-------|
| Airflow Web UI | http://localhost:8080 | Login with `airflow / airflow` (configurable in `.env`). |
| VM API (vision model service\*) | http://localhost:8000/health | Returns JSON health payload. |
| Flower (Celery monitoring) | http://localhost:5555 | Only available when `flower` profile is enabled. |

Volumes mount the host `data_pipeline/` subtree into the containers, so outputs appear on your filesystem.

\*The vision model endpoint is currently incubating. A separate DAG (`data_pipeline_VM_dag.py`) is scaffolded to invoke the future vision-powered pipeline once the VM API is stabilised. For now, all OCR work is handled inside `scripts/pdf_parser.py`, and the vision DAG remains disabled until the integration completes.

### 4.4 Running the Pipeline via Docker

**Through Airflow UI**  
1. Open http://localhost:8080.  
2. Enable and trigger the `Data_Pipeline` DAG.  
3. Watch task logs in the Airflow UI.

**From the terminal**  

```bash
docker compose -f docker-compose.yml exec airflow-scheduler   python /opt/airflow/project/scripts/pipeline_runner.py
```

This executes the same stages in order and logs to `data_pipeline/logs/`.

### 4.5 Stopping / Cleaning Up

```bash
./docker-manage.sh stop        # stop containers, keep volumes
./docker-manage.sh cleanup     # stop containers and remove volumes/networks
```

If you ever need to free ports or reset everything, run cleanup followed by start.

---

## 5. Local Development Without Docker (Optional)

You might prefer to run scripts directly for debugging or when Docker is unavailable.

### 5.1 Create Virtual Environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r data_pipeline/requirements.txt
```

### 5.2 Configure Environment

1. Install Tesseract (see prerequisites).
2. Ensure it’s on your PATH (`which tesseract` or `where tesseract`).
3. Copy `.env` if you want local defaults:
   ```bash
   cp data_pipeline/.env .env.local  # optional adjustments
   export $(grep -v '^#' .env.local | xargs)  # Linux/macOS
   ```
4. Add the project root to `PYTHONPATH`:
   ```bash
   export PYTHONPATH="$PWD/data_pipeline:$PYTHONPATH"
   ```

### 5.3 Run the Pipeline

```bash
python data_pipeline/scripts/pipeline_runner.py
```

To execute individual stages:

```bash
python data_pipeline/scripts/download_data.py
python data_pipeline/scripts/pdf_parser.py
# ...and so on
```

Outputs are written in-place under `data_pipeline/data/`.

---

## 6. Testing & Validation

Run automated tests before pushing changes or after cloning to another machine.

### Local Environment

```bash
pytest data_pipeline/tests
```

### Inside Docker

```bash
docker compose -f data_pipeline/docker-compose.yml exec airflow-scheduler   pytest /opt/airflow/project/tests
```

For a quick sanity check on static analysis:

```bash
python -m compileall data_pipeline/scripts data_pipeline/dags
```

---

## 7. Replicating on a New Machine (Checklist)

1. Install prerequisites (Docker Desktop, Python 3.12, Tesseract).
2. Clone the repository.
3. Copy `data_pipeline/.env` if you need custom values (otherwise defaults are pre-populated).
4. Run `./docker-manage.sh build` and `./docker-manage.sh start` from inside `data_pipeline/`.
5. Verify the Airflow UI opens on http://localhost:8080.
6. Update `data_pipeline/data/url.json` with your organisation’s documents.
7. Trigger the `Data_Pipeline` DAG (UI) or `pipeline_runner.py` (CLI).
8. Confirm new artefacts appear in `data_pipeline/data/validated/` and embeddings in `data_pipeline/data/vector_db/`.
9. Run `pytest data_pipeline/tests` (either locally or via Docker) to ensure everything passes.
10. Commit `.env` changes only if you intend to share them; otherwise keep secrets local.

Following these steps ensures the code runs without errors on any colleague’s machine.

---

## 8. Troubleshooting

| Symptom | Likely Cause | Resolution |
|---------|--------------|-----------|
| `Bind for 0.0.0.0:8080 failed` | Port already in use (old containers or another service). | `./docker-manage.sh stop`, kill conflicting process (`lsof -i :8080`), then retry. |
| `ModuleNotFoundError: data_pipeline` | `PYTHONPATH` not set when running locally. | `export PYTHONPATH="$PWD/data_pipeline:$PYTHONPATH"` before running scripts. |
| `Tesseract executable not detected` | OCR package missing. | Install Tesseract and ensure it’s in PATH, or set `TESSERACT_CMD` in `.env`. |
| `docker compose up` hangs on build | Insufficient resources or stale build context. | Increase Docker memory to ≥4 GB, run `./docker-manage.sh cleanup` then `build`. |
| Airflow DAG import timeout | Custom DAG imports heavy libraries at module load. | Follow the provided DAG (lazy imports) pattern; ensure no new heavy imports at top level. |
| VM API returns 500 | Missing ML dependencies or incompatible GPU libs. | Rebuild image (`./docker-manage.sh build`), inspect logs `./docker-manage.sh logs vm-api`. |

For deeper debugging, attach to containers:

```bash
docker compose -f data_pipeline/docker-compose.yml exec airflow-scheduler bash
docker compose -f data_pipeline/docker-compose.yml logs -f airflow-worker
```

---

## 9. Contributing Guidelines (Optional but Recommended)

- Adhere to PEP 8; keep new dependencies in `data_pipeline/requirements.txt`.
- Add tests for new modules in `data_pipeline/tests/`.
- Run `pytest` and the pipeline locally before raising PRs.
- Document new environment variables in this README and in `.env`.

---

## 10. Support

If you encounter issues not covered here:

1. Check container logs (`./docker-manage.sh logs <service>`).
2. Confirm prerequisites (Docker, Tesseract, Python) are installed.
3. Review recent commits or undo local changes affecting configs.
4. Consult `data_pipeline/DOCKER_SETUP.md` for additional Docker-specific tips.
5. Raise an issue or reach out to the project maintainers with steps to reproduce.

---

## 11. Logging and Data Outputs

All stages in the pipeline emit structured logs and save intermediate files under `data_pipeline/data/`.

| Folder | Contents | Generated by |
|---------|-----------|--------------|
| `data/raw/` | Original downloaded PDFs | `download_data.py` |
| `data/extracted/` | Parsed text and table JSON | `pdf_parser.py` |
| `data/cleaned/` | Clean, normalized text before chunking | `preprocess.py` |
| `data/chunked/` | JSONL chunks with metadata | `chunker.py` |
| `data/validated/` | Final valid and invalid chunks with reports | `validate_data.py` |
| `data/vector_db/` | ChromaDB persistent store | `store_in_chromadb.py` |

Logs for each stage are timestamped and stored under `data_pipeline/logs/`. A new log file is generated on every pipeline run.

Example snippet:
```
2025-10-28 09:15:41,207 - data_pipeline.scripts.preprocess - INFO - Cleaned 4825 chunks (25 skipped due to empty content)
```

---

## 12. Testing and Continuous Integration

The pipeline is fully testable both locally and within Docker. Unit tests cover validation, extraction, preprocessing, and embedding logic, while integration tests simulate the complete pipeline on temporary directories.

**Local testing:**
```bash
pytest -v --disable-warnings
```

**CI Workflow Example (`.github/workflows/test.yml`):**
```yaml
name: FrontShiftAI Data Pipeline CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r data_pipeline/requirements.txt
      - run: pytest -v --disable-warnings
```

This configuration ensures all new commits are tested automatically before merging.

---

## 13. Monitoring and Metrics

You can track validation and pipeline performance metrics directly from the generated reports or through optional integrations.

**Metrics generated automatically:**
- Chunk count, token count, language validity
- Validation summary (`validation_summary.json`)
- Invalid chunk percentage
- Embedding success rate (Chroma collection stats)

For long-running deployments, Airflow can be integrated with Prometheus and Grafana to monitor:
- DAG success/failure rates  
- Average stage runtime  
- Resource utilization of OCR and embedding steps

---

## 14. Extending the Pipeline

To extend functionality:
1. Create a new script under `data_pipeline/scripts/` (e.g., `classify_sections.py`).
2. Add it to the DVC stages in `data_pipeline/dvc.yaml` or as a task in your Airflow DAG.
3. Import the logger from `utils/logger.py` for consistent log formatting.
4. Add corresponding tests under `data_pipeline/tests/`.

**Example (simplified):**
```python
from utils.logger import get_logger
logger = get_logger(__name__)

def main():
    logger.info("Running section classification...")
    # your logic here

if __name__ == "__main__":
    main()
```

After adding, you can run:
```bash
dvc repro
```
to automatically include it in the full run.

---

## 15. Future Enhancements

- Integration with Vertex AI for model serving and drift detection  
- Support for multilingual OCR using Tesseract language packs  
- Auto-scheduling via GitHub Actions or GCP Cloud Composer  
- Data validation dashboards with Streamlit or EvidentlyAI  
- Deployment-ready container images published to Docker Hub  

---

## 16. License and Attribution

This project is distributed under the MIT License.  
All included PDF samples are public and used for research or educational purposes.  
Attribution to original handbook publishers is retained through metadata fields in extracted chunks.
