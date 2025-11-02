"""
exp_tracking.py
------------------------------------
Weights & Biases (W&B) experiment tracking for FrontShiftAI.
Logs metrics, artifacts, and model versions for each evaluation stage.
"""

import wandb
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

PROJECT_NAME = "FrontShiftAI"
ENTITY = "group9mlops-northeastern-university"
BASE_DIR = Path(__file__).resolve().parents[2]

def setup_wandb(stage_name: str, model_name: str):
    run = wandb.init(
        project=PROJECT_NAME,
        entity=ENTITY,
        job_type=stage_name,
        name=f"{stage_name}_{model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        config={"model_name": model_name, "stage": stage_name},
        reinit=True
    )
    print(f"✅ W&B tracking started for stage: {stage_name}")
    return run

def log_metrics(stage_name: str, model_name: str, metrics: Dict, artifacts: Optional[Dict] = None):
    run = setup_wandb(stage_name, model_name)
    wandb.log(metrics)
    if artifacts:
        for name, path in artifacts.items():
            p = Path(path)
            if p.exists():
                art = wandb.Artifact(f"{name}_{model_name}", type="dataset")
                art.add_file(str(p))
                wandb.log_artifact(art)
                print(f"📂 Uploaded artifact: {p.name}")
    wandb.finish()
    print(f"📊 Logged {stage_name} metrics for {model_name}")
