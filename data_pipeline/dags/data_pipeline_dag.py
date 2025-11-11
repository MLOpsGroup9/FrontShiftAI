import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DATA_PIPELINE_ROOT = PROJECT_ROOT / "project"
if str(DATA_PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_PIPELINE_ROOT))


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
LOG_DIR = DATA_PIPELINE_ROOT / "logs" / "dag"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("data_pipeline_dag")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler(LOG_DIR / "data_pipeline.log", encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.propagate = False


# ---------------------------------------------------------------------------
# Task callables with lazy imports
# ---------------------------------------------------------------------------
def run_download_stage() -> Dict[str, object]:
    from scripts.download_data import (  # noqa: WPS433 - deferred import
        RAW_DATA_DIR as download_raw_dir,
        URLS_PATH,
        download_pdf,
    )

    if not URLS_PATH.exists():
        raise FileNotFoundError(f"URL manifest not found at {URLS_PATH}")

    logger.info("Starting download stage. Saving PDFs to %s", download_raw_dir)
    download_pdf(URLS_PATH, download_raw_dir)

    pdf_count = len(list(download_raw_dir.glob("*.pdf")))
    logger.info("Download stage complete. %s files present.", pdf_count)
    return {"pdf_count": pdf_count, "output_dir": str(download_raw_dir)}


def run_pdf_parser_stage() -> Dict[str, object]:
    from scripts.pdf_parser import (  # noqa: WPS433 - deferred import
        PROCESSED_PDF_DIR,
        RAW_PDF_DIR,
        convert_pdf_to_md,
    )

    pdf_files = sorted(RAW_PDF_DIR.glob("*.pdf"))
    logger.info("Starting OCR parser stage for %s PDFs.", len(pdf_files))

    processed = 0
    for pdf_path in pdf_files:
        convert_pdf_to_md(str(pdf_path))
        processed += 1

    logger.info("PDF parser stage complete. Markdown saved to %s", PROCESSED_PDF_DIR)
    return {"processed_pdfs": processed, "output_dir": str(PROCESSED_PDF_DIR)}


def run_preprocess_stage() -> Dict[str, object]:
    from scripts.preprocess import (  # noqa: WPS433 - deferred import
        CLEANED_DATA_DIR,
        EXTRACTED_DATA_DIR,
        TextPreprocessor,
    )

    logger.info("Starting preprocessing stage. Input: %s", EXTRACTED_DATA_DIR)
    preprocessor = TextPreprocessor(
        input_dir=str(EXTRACTED_DATA_DIR),
        output_dir=str(CLEANED_DATA_DIR),
    )
    stats = preprocessor.process_all()
    logger.info("Preprocessing stage complete with stats: %s", stats)
    return stats


def run_chunker_stage() -> Dict[str, object]:
    from scripts.chunker import (  # noqa: WPS433 - deferred import
        CHUNKED_DATA_DIR,
        CLEANED_DATA_DIR,
        ChunkGenerator,
    )

    logger.info("Starting chunker stage. Input: %s", CLEANED_DATA_DIR)
    generator = ChunkGenerator(
        input_dir=str(CLEANED_DATA_DIR),
        output_dir=str(CHUNKED_DATA_DIR),
    )
    stats = generator.process_all()
    logger.info("Chunker stage complete with stats: %s", stats)
    return stats


def run_validation_stage() -> Dict[str, object]:
    from scripts.validate_data import (  # noqa: WPS433 - deferred import
        REPORTS_DIR,
        VALIDATED_DIR,
        validate_all_chunks,
    )

    logger.info("Starting validation stage. Input directory: %s", VALIDATED_DIR.parent)
    validate_all_chunks()
    summary_path = REPORTS_DIR / "validation_summary.json"
    summary: Dict[str, object] = {}
    if summary_path.exists():
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning("Validation summary JSON malformed: %s", summary_path)
    logger.info("Validation stage complete.")
    return {
        "reports_dir": str(REPORTS_DIR),
        "validated_dir": str(VALIDATED_DIR),
        "summary": summary,
    }


def run_bias_stage() -> Optional[str]:
    from scripts.data_bias import run_bias_analysis  # noqa: WPS433 - deferred import

    logger.info("Starting data bias stage.")
    output_dir = run_bias_analysis()
    logger.info("Data bias stage complete. Output: %s", output_dir)
    return str(output_dir) if output_dir else None


def run_embedding_stage() -> None:
    from scripts.store_in_chromadb import (  # noqa: WPS433 - deferred import
        main as store_embeddings,
    )

    logger.info("Starting embedding stage.")
    store_embeddings()
    logger.info("Embedding stage complete.")


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
    dag_id="Data_Pipeline",
    default_args=default_args,
    description="Data Pipeline DAG for FrontShiftAI with OCR parser",
    schedule=None,
    catchup=False,
) as dag:
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

    download_data_task >> pdf_parser_task >> preprocess_task >> chunker_task
    chunker_task >> validate_data_task >> data_bias_task >> store_in_chromadb_task


if __name__ == "__main__":
    dag.test()
