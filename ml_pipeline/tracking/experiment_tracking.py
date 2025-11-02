"""
exp_tracking.py
------------------------------------
Central MLflow tracking setup for FrontShiftAI.

Handles:
- MLflow initialization (local)
- Experiment creation
- Logging metrics, parameters, and artifacts for each evaluation run
"""

import mlflow
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

BASE_DIR = Path(__file__).resolve().parents[2]  # /FrontShiftAI
MLRUNS_DIR = BASE_DIR / "mlruns"
MLRUNS_DIR.mkdir(parents=True, exist_ok=True)

def setup_mlflow(experiment_name: str = "FrontShiftAI_Evaluation"):
    """Initialize MLflow tracking in local mode."""
    tracking_uri = f"file://{MLRUNS_DIR}"
    mlflow.set_tracking_uri(tracking_uri)

    # Create or set experiment
    exp = mlflow.get_experiment_by_name(experiment_name)
    if exp is None:
        exp_id = mlflow.create_experiment(experiment_name)
    else:
        exp_id = exp.experiment_id

    mlflow.set_experiment(experiment_name)
    print(f"✅ MLflow ready at {tracking_uri} | Experiment: {experiment_name} (id={exp_id})")
    return exp_id

def log_run(stage_name: str, model_name: str, metrics: Dict, artifacts: Optional[Dict] = None):
    """Log metrics and artifacts for a given pipeline stage."""
    with mlflow.start_run(run_name=f"{stage_name}_{model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
        mlflow.log_params({"stage": stage_name, "model": model_name})
        mlflow.log_metrics(metrics)
        if artifacts:
            for name, path in artifacts.items():
                p = Path(path)
                if p.exists():
                    mlflow.log_artifact(str(p), artifact_path=name)
        print(f"📊 Logged {stage_name} metrics and artifacts for {model_name}")
