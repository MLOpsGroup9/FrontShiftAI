"""
Lightweight DAG that verifies the vision-model API is reachable.
The service itself runs outside of Airflow (e.g., via Docker Compose);
this dag simply provides a manual health check.
"""

from __future__ import annotations

import os
from datetime import datetime

import requests
from airflow import DAG
from airflow.sensors.python import PythonSensor


def _vision_api_base_url() -> str:
    default_url = "http://vm-api:8000"
    env_url = os.getenv("VISION_MODEL_API_URL", default_url)
    if env_url.startswith("http://0.0.0.0") or env_url.startswith("http://::"):
        return default_url
    return env_url.rstrip("/")


def _healthcheck() -> bool:
    base_url = _vision_api_base_url()
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        response.raise_for_status()
        return True
    except requests.RequestException:
        return False


default_args = {
    "owner": "Raghav G",
    "start_date": datetime(2025, 1, 1),
    "retries": 0,
}

with DAG(
    dag_id="vm_api_healthcheck",
    default_args=default_args,
    description="Ad-hoc health check for the external vision model API.",
    schedule=None,
    catchup=False,
    max_active_runs=1,
) as dag:
    PythonSensor(
        task_id="ensure_vm_api_available",
        python_callable=_healthcheck,
        poke_interval=int(os.getenv("VM_API_POLL_INTERVAL", "5")),
        timeout=int(os.getenv("VM_API_STARTUP_TIMEOUT", "120")),
        mode="reschedule",
    )
