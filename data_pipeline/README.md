# FrontShiftAI Data Pipeline

> End-to-end ingestion, OCR, cleansing, validation, and embedding of organisational policy documents, packaged for both local development and containerised deployment.

This README is the authoritative guide for cloning the project on a new machine, setting up all prerequisites, and running the pipeline without errors. It covers:

1. **Architecture overview** of the pipeline stages and services.
2. **Repository layout** so you can locate code, configs, and data.
3. **Prerequisites** (system packages, Python, Docker) for macOS, Linux, and Windows.
4. **Docker-first quickstart** – the recommended way to run the pipeline consistently.
5. **Local-only workflow** for development outside of Docker.
6. **Testing & validation** steps.
7. **Troubleshooting** common issues (ports, OCR, permissions).

---

## 1. Architecture Overview

The pipeline processes PDF handbooks into a searchable vector store in seven stages:

| Stage | Script | Purpose |
|-------|--------|---------|
| Download | `scripts/download_data.py` | Fetch PDFs from `data/url.json` into `data/raw/`. |
| OCR Parsing | `scripts/pdf_parser.py` | Extract text/tables with PyMuPDF + pdfplumber, fallback to Tesseract OCR. |
| Preprocess | `scripts/preprocess.py` | Normalize markdown, detect sections, emit cleaned JSON in `data/cleaned/`. |
| Chunking | `scripts/chunker.py` | Token-based segmentation, produce JSONL chunks in `data/chunked/`. |
| Validation | `scripts/validate_data.py` | Schema/quality checks, build reports in `data/validated/`. |
| Bias Analysis | `scripts/data_bias.py` | Optional analytics artefacts. |
| Vector Store | `scripts/store_in_chromadb.py` | Persist embeddings in `data/vector_db/`. |

Two orchestration layers ship with the repo:

- **`scripts/pipeline_runner.py`** runs every stage sequentially (ideal for local dev or ad-hoc runs).
- **Airflow DAGs** (`dags/data_pipeline_dag.py` and `dags/data_pipeline_VM_dag.py`) wrap each stage as a task and can be scheduled via Docker Compose.

---

## 2. Repository Layout

```
FrontShiftAI/
├── data_pipeline/
│   ├── config/                 # Airflow + project configuration files
│   ├── dags/                   # Airflow DAG definitions
│   ├── data/                   # Raw, processed, and vector store artefacts
│   ├── docker/                 # Dockerfiles for Airflow + VM API images
│   ├── docker-compose.yml      # Compose stack (moved inside data_pipeline/)
│   ├── docker-manage.sh        # Helper for docker compose workflow
│   ├── logs/                   # Runtime logs (created automatically)
│   ├── plugins/                # Airflow plugins (empty by default)
│   ├── requirements.txt        # Python dependencies for the pipeline
│   ├── scripts/                # Python scripts implementing each stage
│   ├── tests/                  # Pytest-based unit/integration tests
│   └── README.md               # (this file)
├── requirements.txt            # Root requirements (mirrors pipeline requirements)
└── ...                         # DVC files, docs, etc.
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
docker compose -f docker-compose.yml exec airflow-scheduler \
  python /opt/airflow/project/scripts/pipeline_runner.py
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
docker compose -f data_pipeline/docker-compose.yml exec airflow-scheduler \
  pytest /opt/airflow/project/tests
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

