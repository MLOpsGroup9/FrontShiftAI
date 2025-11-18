import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict

from chat_pipeline.utils.logger import setup_logging

logger = logging.getLogger(__name__)

# --- PATH CONFIG ---
BASE_DIR = Path(__file__).resolve().parents[2]  # /FrontShiftAI
MODEL_SOURCE_DIR = BASE_DIR / "models"
REGISTRY_DIR = BASE_DIR / "models_registry"
REGISTRY_DIR.mkdir(parents=True, exist_ok=True)  # ensure registry exists

def get_next_version(model_name: str) -> str:
    """Find the next available version folder (v1, v2, etc.)."""
    versions = []
    for d in REGISTRY_DIR.glob(f"{model_name}_v*"):
        if d.is_dir():
            try:
                versions.append(int(d.name.split("_v")[-1]))
            except ValueError:
                continue
    next_ver = max(versions, default=0) + 1
    return f"v{next_ver}"

def push_to_registry(model_name: str, model_file: str, metrics: Dict):
    """
    Save model file and its evaluation metrics in a versioned registry folder.
    """
    version = get_next_version(model_name)
    dest_dir = REGISTRY_DIR / f"{model_name}_{version}"
    dest_dir.mkdir(parents=True, exist_ok=True)

    # --- Copy model file from /models ---
    src_path = MODEL_SOURCE_DIR / model_file
    if not src_path.exists():
        raise FileNotFoundError(f"Model file not found: {src_path}")
    shutil.copy2(src_path, dest_dir / src_path.name)  # preserves metadata (mtime, etc.)

    # --- Save metadata JSON ---
    metadata = {
        "model_name": model_name,
        "version": version,
        "timestamp": datetime.now().isoformat(),
        "metrics": metrics,
        "artifact_path": str(dest_dir / src_path.name),
    }

    with open(dest_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=4)

    logger.info("Model '%s' registered as %s", model_name, version)
    logger.info("Saved to: %s", dest_dir)
    return metadata

if __name__ == "__main__":
    setup_logging()
    # Manual test
    model_name = "llama_3b_instruct"
    model_file = "Llama-3.2-3B-Instruct-Q4_K_S.gguf"
    metrics = {"mean_semantic_sim": 0.5425, "mean_precision_at_k": 1.0}
    push_to_registry(model_name, model_file, metrics)
