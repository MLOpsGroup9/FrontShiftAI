from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from pathlib import Path
import os, sys

# -------------------------------------------------------------------
# Ensure Airflow can find the scripts folder
# -------------------------------------------------------------------
DAG_DIR = Path(os.getenv("AIRFLOW_HOME", Path(__file__).resolve().parents[1]))
PROJECT_ROOT = Path(DAG_DIR)
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
sys.path.append(str(SCRIPTS_DIR))

from data_extraction import main as extract_main
from preprocess import main as preprocess_main

def check_system_health():
    base = PROJECT_ROOT
    folders = [
        base / "data" / "raw",
        base / "data" / "extracted",
        base / "data" / "cleaned",
        base / "logs",
    ]
    for folder in folders:
        folder.mkdir(parents=True, exist_ok=True)
    print("✅ Health check passed — all directories are ready.")
    return True


default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=3),
}

with DAG(
    dag_id="data_pipeline_dag",
    default_args=default_args,
    description="End-to-end data pipeline: health check → extraction → preprocessing → tests",
    start_date=datetime(2025, 10, 12),
    schedule=None,  # ✅ correct syntax
    catchup=False,
    tags=["mlops", "data-pipeline", "manual"],
) as dag:

    health_check = PythonOperator(
        task_id="health_check",
        python_callable=check_system_health,
    )

    extract_data = PythonOperator(
        task_id="extract_data",
        python_callable=extract_main,
    )

    preprocess_data = PythonOperator(
        task_id="preprocess_data",
        python_callable=preprocess_main,
    )

    run_tests = BashOperator(
        task_id="run_tests",
        bash_command=f"pytest -v {PROJECT_ROOT}/tests/ > {PROJECT_ROOT}/logs/pipeline_test_log.txt 2>&1",
    )

    health_check >> extract_data >> preprocess_data >> run_tests
