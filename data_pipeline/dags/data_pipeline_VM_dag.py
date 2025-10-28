from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

import requests
from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from airflow.providers.standard.sensors.python import PythonSensor

PROJECT_ROOT = Path(__file__).resolve().parents[1]  # Go up to /opt/airflow
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Add the data_pipeline directory to Python path
DATA_PIPELINE_ROOT = PROJECT_ROOT / "project"  # This is /opt/airflow/project
if str(DATA_PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_ROOT))

from scripts.download_data import (  # noqa: E402
    RAW_DATA_DIR as DOWNLOAD_RAW_DIR,
    URLS_PATH,
    download_pdf,
)
from scripts.pdf_parser import (  # noqa: E402
    PROCESSED_PDF_DIR,
    RAW_PDF_DIR,
    convert_pdf_to_md,
)
from scripts.preprocess import (  # noqa: E402
    CLEANED_DATA_DIR,
    EXTRACTED_DATA_DIR,
    TextPreprocessor,
)
from scripts.chunker import (  # noqa: E402
    CHUNKED_DATA_DIR,
    ChunkGenerator,
)
from scripts.validate_data import (  # noqa: E402
    REPORTS_DIR,
    VALIDATED_DIR,
    validate_all_chunks,
)
from scripts.data_bias import run_bias_analysis  # noqa: E402
from scripts.store_in_chromadb import main as store_embeddings  # noqa: E402


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
# Use the project directory which is mounted at /opt/airflow/project
LOG_DIR = DATA_PIPELINE_ROOT / "logs" / "dag"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("data_pipeline_split_dag")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler(LOG_DIR / "data_pipeline_split.log", encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(file_handler)
    # Keep console logging out of the DAG parser output to avoid noise.
    logger.propagate = False


def _format_minutes(seconds: float) -> float:
    """Convert seconds to minutes rounded to two decimals."""
    return round(seconds / 60, 2)


def _stage_result(duration: float, payload: Optional[Dict] = None) -> Dict:
    """Shape a JSON-serialisable result for XCom."""
    data: Dict[str, object] = {
        "duration_seconds": round(duration, 2),
        "duration_minutes": _format_minutes(duration),
    }
    if payload:
        data["details"] = payload
    return data


def run_download_stage() -> Dict:
    """Download PDFs defined in url.json into the raw data directory."""
    start = time.perf_counter()
    if not URLS_PATH.exists():
        raise FileNotFoundError(f"URL manifest not found at {URLS_PATH}")

    logger.info("Starting download stage. Saving PDFs to %s", DOWNLOAD_RAW_DIR)
    download_pdf(URLS_PATH, DOWNLOAD_RAW_DIR)
    elapsed = time.perf_counter() - start
    logger.info("Completed download stage in %s minutes", _format_minutes(elapsed))

    pdf_count = len(list(DOWNLOAD_RAW_DIR.glob("*.pdf")))
    return _stage_result(elapsed, {"pdf_count": pdf_count, "output_dir": str(DOWNLOAD_RAW_DIR)})


def run_pdf_parser_stage() -> Dict:
    """Convert all PDFs in the raw directory to markdown files."""
    start = time.perf_counter()
    pdf_files = sorted(RAW_PDF_DIR.glob("*.pdf"))
    logger.info("Starting PDF parser stage. %s PDFs detected in %s", len(pdf_files), RAW_PDF_DIR)

    processed = 0
    for pdf_path in pdf_files:
        convert_pdf_to_md(str(pdf_path))
        processed += 1

    elapsed = time.perf_counter() - start
    logger.info(
        "Completed PDF parser stage in %s minutes (processed %s files)",
        _format_minutes(elapsed),
        processed,
    )
    return _stage_result(
        elapsed,
        {
            "processed_pdfs": processed,
            "output_dir": str(PROCESSED_PDF_DIR),
        },
    )


def run_preprocess_stage() -> Dict:
    """Clean markdown files and produce normalised JSON documents."""
    start = time.perf_counter()
    logger.info("Starting preprocessing stage. Input directory: %s", EXTRACTED_DATA_DIR)

    preprocessor = TextPreprocessor(input_dir=str(EXTRACTED_DATA_DIR), output_dir=str(CLEANED_DATA_DIR))
    stats = preprocessor.process_all()

    elapsed = time.perf_counter() - start
    logger.info(
        "Completed preprocessing stage in %s minutes (processed %s documents)",
        _format_minutes(elapsed),
        stats.get("total_docs", 0),
    )
    return _stage_result(elapsed, stats)


def run_chunker_stage() -> Dict:
    """Chunk cleaned JSON documents to JSONL format for embeddings."""
    start = time.perf_counter()
    logger.info("Starting chunker stage. Input directory: %s", CLEANED_DATA_DIR)

    generator = ChunkGenerator(input_dir=str(CLEANED_DATA_DIR), output_dir=str(CHUNKED_DATA_DIR))
    stats = generator.process_all()

    elapsed = time.perf_counter() - start
    logger.info(
        "Completed chunker stage in %s minutes (total chunks %s)",
        _format_minutes(elapsed),
        stats.get("total_chunks", 0),
    )
    return _stage_result(elapsed, stats)


def run_validation_stage() -> Dict:
    """Validate the produced chunks and emit reports."""
    start = time.perf_counter()
    logger.info("Starting validation stage. Chunk directory: %s", CHUNKED_DATA_DIR)

    validate_all_chunks()
    summary_path = REPORTS_DIR / "validation_summary.json"
    summary: Dict[str, object] = {}
    if summary_path.exists():
        try:
            summary_data = json.loads(summary_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning("Validation summary JSON is malformed: %s", summary_path)
            summary_data = {}
        summary = {"summary_path": str(summary_path), **summary_data}

    elapsed = time.perf_counter() - start
    logger.info("Completed validation stage in %s minutes", _format_minutes(elapsed))
    return _stage_result(
        elapsed,
        {
            "reports_dir": str(REPORTS_DIR),
            "validated_dir": str(VALIDATED_DIR),
            "summary": summary,
        },
    )


def run_bias_stage() -> Dict:
    """Generate bias analysis artefacts."""
    start = time.perf_counter()
    logger.info("Starting data bias stage.")
    output_dir = run_bias_analysis()
    elapsed = time.perf_counter() - start
    logger.info("Completed data bias stage in %s minutes", _format_minutes(elapsed))
    return _stage_result(
        elapsed,
        {"bias_analysis_dir": str(output_dir) if output_dir else None},
    )


def run_embedding_stage() -> Dict:
    """Persist validated chunks into ChromaDB."""
    start = time.perf_counter()
    logger.info("Starting embedding stage (ChromaDB ingest).")
    store_embeddings()
    elapsed = time.perf_counter() - start
    logger.info("Completed embedding stage in %s minutes", _format_minutes(elapsed))
    return _stage_result(elapsed)


def _vm_api_base_url() -> str:
    default_url = "http://vm-api:8000"
    env_url = os.getenv("VISION_MODEL_API_URL", default_url)
    if env_url.startswith("http://0.0.0.0") or env_url.startswith("http://::"):
        return default_url
    return env_url.rstrip("/")


def wait_for_vm_api_callable() -> bool:
    base_url = _vm_api_base_url()
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        response.raise_for_status()
        payload = response.json()
        logger.info(
            "Vision model API healthy at %s (device=%s)",
            base_url,
            payload.get("device", "unknown"),
        )
        return True
    except requests.RequestException as exc:
        logger.info("Vision model API not ready at %s: %s", base_url, exc)
        return False


# ---------------------------------------------------------------------------
# DAG definition
# ---------------------------------------------------------------------------
default_args = {
    "owner": "Raghav G",
    "start_date": datetime(2025, 1, 15),
    "retries": 0,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="data_pipeline_split",
    default_args=default_args,
    description="Split data pipeline DAG with per-stage instrumentation.",
    schedule=None,
    catchup=False,
) as dag:
    ensure_vm_api_ready = PythonSensor(
        task_id="ensure_vm_api_ready",
        python_callable=wait_for_vm_api_callable,
        poke_interval=int(os.getenv("VM_API_POLL_INTERVAL", "5")),
        timeout=int(os.getenv("VM_API_STARTUP_TIMEOUT", "600")),
        mode="reschedule",
    )

    download_data_task = PythonOperator(
        task_id="download_data",
        python_callable=run_download_stage,
    )

    pdf_parser_task = PythonOperator(
        task_id="pdf_parser",
        python_callable=run_pdf_parser_stage,
    )

    preprocess_task = PythonOperator(
        task_id="preprocess",
        python_callable=run_preprocess_stage,
    )

    chunker_task = PythonOperator(
        task_id="chunker",
        python_callable=run_chunker_stage,
    )

    validate_data_task = PythonOperator(
        task_id="validate_data",
        python_callable=run_validation_stage,
    )

    data_bias_task = PythonOperator(
        task_id="data_bias",
        python_callable=run_bias_stage,
    )

    store_in_chromadb_task = PythonOperator(
        task_id="store_in_chromadb",
        python_callable=run_embedding_stage,
    )

    ensure_vm_api_ready >> download_data_task >> pdf_parser_task >> preprocess_task >> chunker_task
    chunker_task >> validate_data_task >> data_bias_task >> store_in_chromadb_task


if __name__ == "__main__":
    dag.test()
