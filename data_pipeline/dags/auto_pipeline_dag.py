from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.sensors.filesystem import FileSensor
from airflow.utils.dates import days_ago
import os

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")

# --- Default settings ---
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "retries": 1,
}

# --- DAG Definition ---
with DAG(
    dag_id="auto_pipeline_dag",
    default_args=default_args,
    description="Automatically run pipeline when new PDF appears in raw folder",
    schedule_interval="@hourly",   # checks every hour (can adjust)
    start_date=days_ago(1),
    catchup=False,
    tags=["frontshiftai", "automation"],
) as dag:

    # --- 1. Sensor: watch for new files in raw/ ---
    wait_for_new_pdf = FileSensor(
        task_id="wait_for_new_pdf",
        fs_conn_id="fs_default",
        filepath="data/raw",  # relative to Airflow home or use full path
        poke_interval=60,      # check every 60 seconds
        timeout=60 * 60 * 6,   # 6 hours max wait
        mode="poke",
    )

    # --- 2. Run the main pipeline script ---
    run_pipeline = BashOperator(
        task_id="run_pipeline",
        bash_command=f"python {os.path.join(SCRIPTS_DIR, 'run_pipeline.py')}",
    )

    # --- 3. Run DVC repro for version tracking ---
    run_dvc_repro = BashOperator(
        task_id="run_dvc_repro",
        bash_command=f"cd {BASE_DIR} && dvc repro",
    )

    # --- Task order ---
    wait_for_new_pdf >> run_pipeline >> run_dvc_repro
