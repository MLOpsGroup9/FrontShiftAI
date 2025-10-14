from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from pathlib import Path
import sys

# -------------------------------------------------------------------
# Ensure Airflow can find the scripts folder (inside data_pipeline)
# -------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
sys.path.append(str(SCRIPTS_DIR))

# Import the main functions from your scripts
from data_extraction import main as extract_main
from preprocess import main as preprocess_main


def check_system_health():
    """Ensure all required folders exist before running pipeline."""
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

# -------------------------------------------------------------------
# Define DAG
# -------------------------------------------------------------------
with DAG(
    dag_id="data_pipeline_dag",
    default_args=default_args,
    description="End-to-end data pipeline: health check → extraction → preprocessing → tests",
    start_date=datetime(2025, 10, 12),
    schedule=None,  # Manual trigger only (Airflow 2.10+ syntax)
    catchup=False,
    tags=["mlops", "data-pipeline", "manual"],
    
) as dag:

    # 1️⃣ Health Check Task
    health_check = PythonOperator(
        task_id="health_check",
        python_callable=check_system_health,
    )

    # 2️⃣ Data Extraction Task
    extract_data = PythonOperator(
        task_id="extract_data",
        python_callable=extract_main,
    )

    # 3️⃣ Data Preprocessing Task
    preprocess_data = PythonOperator(
        task_id="preprocess_data",
        python_callable=preprocess_main,
    )

    # 4️⃣ Run Tests Task
    run_tests = BashOperator(
        task_id="run_tests",
        bash_command=f"pytest -v {PROJECT_ROOT}/tests/ > {PROJECT_ROOT}/logs/pipeline_test_log.txt 2>&1",
    )

    # Define task dependencies
    health_check >> extract_data >> preprocess_data >> run_tests
