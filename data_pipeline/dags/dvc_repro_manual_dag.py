"""
DAG: dvc_repro_manual_dag
Purpose: Manually trigger DVC pipeline (repro + push + local commit only)
Author: Krishna (FrontShiftAI)
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.standard.operators.bash import BashOperator

PROJECT_DIR = "/opt/airflow/project"

default_args = {
    "owner": "krishna",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

with DAG(
    dag_id="dvc_repro_manual_dag",
    description="Manually trigger DVC repro for the FrontShiftAI project.",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args=default_args,
    tags=["frontshiftai", "dvc", "manual"],
) as dag:

    run_dvc_pipeline = BashOperator(
        task_id="run_dvc_pipeline",
        bash_command=f"""
            cd {PROJECT_DIR}
            export PYENV_VERSION=frontshiftai
            echo "🚀 Running DVC pipeline manually..."

            # Step 1: Run pipeline
            dvc repro

            # Step 2: Push data artifacts to remote
            dvc push

            # Step 3: Commit updated lockfile (local only)
            git add dvc.lock
            git commit -m "Reproduce pipeline after new PDFs added" || echo "No changes to commit."

            echo "✅ DVC pipeline completed (local commit only)."
        """,
    )

    run_dvc_pipeline
