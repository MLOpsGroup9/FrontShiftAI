# Docker Setup Guide

This document walks you through running the FrontShiftAI data pipeline with Docker Compose. The stack now lives inside the `data_pipeline/` directory, so all paths below are relative to that folder unless stated otherwise.

---

## 1. Prerequisites

- Docker Desktop ≥ 4.15 (or Docker Engine with Compose v2) installed and running.
- Allocated resources: ≥ 4 CPUs, ≥ 4 GB RAM, ≥ 15 GB free disk.
- Git and Python 3.12+ (for local development or testing inside containers).
- Tesseract OCR installed on the host if you plan to run the pipeline outside Docker (optional for container-only usage).

Check Docker is functioning:

```bash
docker --version
docker compose version
```

---

## 2. Quick Start (Recommended Flow)

From the repository root:

```bash
cd data_pipeline
./docker-manage.sh check      # verifies Docker/Compose availability and creates directories
./docker-manage.sh build      # builds Airflow + VM API images
./docker-manage.sh start      # launches all services in the background
```

Confirm containers are running:

```bash
docker compose -f docker-compose.yml ps
```

Access the key services:

| Service | URL | Default credentials / notes |
|---------|-----|-----------------------------|
| Airflow Web UI | http://localhost:8080 | `airflow / airflow` (configurable in `.env`) |
| VM API (vision model service) | http://localhost:8000/health | Returns JSON health payload |
| Flower (Celery monitoring) | http://localhost:5555 | Only available when `flower` profile is enabled |

---

## 3. Services Overview

### Core Airflow components
- `airflow-apiserver`: Web UI and REST API.
- `airflow-scheduler`: Schedules DAG runs.
- `airflow-worker`: Executes tasks via Celery.
- `airflow-dag-processor`: Parses DAG files asynchronously.
- `airflow-triggerer`: Handles deferrable tasks.
- `airflow-init`: One-shot container that initializes the Airflow metadata database and admin account.

### Supporting services
- `postgres`: Airflow metadata database (PostgreSQL 16).
- `redis`: Celery message broker.
- `vm-api`: Vision model endpoint (currently staged; OCR work is handled in `pdf_parser.py` until integration is complete).

All services mount host directories so outputs (logs, data, config) persist on your filesystem under `data_pipeline/`.

---

## 4. Management Commands

### Helper script (`docker-manage.sh`)

```bash
./docker-manage.sh check        # Dependency check + directory creation
./docker-manage.sh build        # Build images
./docker-manage.sh start        # Start services
./docker-manage.sh stop         # Stop services (containers remain)
./docker-manage.sh restart      # Stop then start
./docker-manage.sh logs         # Tail all logs
./docker-manage.sh logs <svc>   # Tail logs for a specific service
./docker-manage.sh status       # Show container status
./docker-manage.sh cleanup      # Stop and remove containers, networks, volumes
```

### Direct Compose usage

```bash
docker compose -f docker-compose.yml up -d
docker compose -f docker-compose.yml down
docker compose -f docker-compose.yml logs -f airflow-scheduler
docker compose -f docker-compose.yml exec airflow-scheduler bash
```

You can also call Compose from the project root by specifying the file path explicitly.

---

## 5. Pipeline Execution

### Using Airflow

1. Visit http://localhost:8080 and log in.
2. Enable the `Data_Pipeline` DAG.
3. Trigger a run and monitor task logs.
4. (Optional) The `data_pipeline_VM_dag.py` DAG is scaffolded for future vision-model integration; keep it disabled until the VM API stabilizes.

### Command-line (inside the scheduler container)

```bash
docker compose -f docker-compose.yml exec airflow-scheduler \
  python /opt/airflow/project/scripts/pipeline_runner.py
```

This runs all stages sequentially and writes logs to `data_pipeline/logs/`.

---

## 6. Development Workflow

- Update Python dependencies in `data_pipeline/requirements.txt` (Airflow image) or `data_pipeline/docker/vm_api/requirements.txt` (vision image), then run `./docker-manage.sh build`.
- Use `docker compose exec <service> bash` to inspect containers or run tests.
  ```bash
  docker compose -f docker-compose.yml exec airflow-scheduler pytest /opt/airflow/project/tests
  ```
- Host paths mounted into containers:

  | Host path | Container mount |
  |-----------|-----------------|
  | `data_pipeline/dags` | `/opt/airflow/dags` |
  | `data_pipeline/logs` | `/opt/airflow/logs` |
  | `data_pipeline/config` | `/opt/airflow/config` |
  | `data_pipeline/plugins` | `/opt/airflow/plugins` |
  | `data_pipeline/` | `/opt/airflow/project` (entire project tree) |
  | `data_pipeline/` | `/app/data_pipeline` inside `vm-api` |

---

## 7. Troubleshooting

| Issue | Diagnosis | Fix |
|-------|-----------|-----|
| Port collision on 8080/8000 | Another process is bound to the port | `./docker-manage.sh stop`, kill the process (`lsof -i :8080`), rerun `start` |
| `airflow-init` exits with errors | Database or permission issue | Check logs `./docker-manage.sh logs airflow-init`; ensure directories exist and are writable |
| DAG import timeout | Heavy imports at module scope | Use the lazy-import pattern shown in `dags/data_pipeline_dag.py` |
| VM API unhealthy | Dependency or runtime error | `./docker-manage.sh logs vm-api`; rebuild image |
| Tesseract warnings in logs | OCR binary not found inside container | Bundled inside the image; only matters if running locally outside Docker |
| Containers stuck in “Created” | Insufficient resources | Increase Docker Desktop memory/CPU |

For a hard reset:

```bash
./docker-manage.sh cleanup
docker system prune --volumes  # optional, removes all unused Docker resources
```

---

## 8. Production Considerations

This stack is tuned for local development. Before production use:

- Externalise Airflow metadata (managed Postgres), Redis, and object storage.
- Secure credentials (use Docker secrets or env managers).
- Enable TLS for web services.
- Set up monitoring/alerting (Prometheus, Grafana, ELK, etc.).
- Apply resource limits and scale workers accordingly.
- Use multi-stage builds and separate networks for isolation.

---

## 9. Support

If you encounter issues:

1. Check container status: `./docker-manage.sh status`
2. Inspect logs: `./docker-manage.sh logs <service>`
3. Verify `.env` values (they are loaded via `data_pipeline/docker-compose.yml`)
4. Consult the main README (`data_pipeline/README.md`) for replication and troubleshooting steps
5. Reach out to maintainers with reproduction steps and relevant logs

With these instructions you should be able to spin up, operate, and debug the Docker-based pipeline reliably across machines. Happy building!
