"""Production-grade model registry writer for LLM-based RAG models.

Stores only lightweight artifacts and metadata – never the model weights.
Intended for use with a versioned registry directory that can later be
synced to remote storage (e.g., GCS bucket).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT", Path(__file__).resolve().parents[2]))
REGISTRY_DIR = Path(os.getenv("MODEL_REGISTRY_DIR", PROJECT_ROOT / "models_registry"))


def _ensure_registry_dir() -> Path:
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    return REGISTRY_DIR


def _compute_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Model file not found for hashing: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _next_version(model_name: str, registry: Path) -> str:
    existing = []
    prefix = f"{model_name}_v"
    for entry in registry.glob(f"{prefix}*"):
        if entry.is_dir() and entry.name.startswith(prefix):
            try:
                existing.append(int(entry.name.split("_v")[-1]))
            except ValueError:
                continue
    return f"v{max(existing, default=0) + 1}"


def get_next_version(model_name: str) -> str:
    """Public helper to compute the next version for a given model."""

    registry = _ensure_registry_dir()
    return _next_version(model_name, registry)


def _copy_artifact(src: Path, dest_dir: Path) -> Optional[str]:
    if not src or not src.exists():
        return None
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    dest.write_bytes(src.read_bytes())
    return dest.name


def _write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def _update_latest_symlink(registry: Path, version_dir: Path) -> None:
    latest = registry / "latest"
    try:
        if latest.exists() or latest.is_symlink():
            latest.unlink()
        latest.symlink_to(version_dir.name)
    except OSError:
        # Fallback for filesystems that don’t support symlinks: write a text file.
        latest.write_text(str(version_dir), encoding="utf-8")


def push_to_registry(
    model_name: str,
    model_path: Optional[str],
    pipeline_config: Dict,
    evaluation_metrics: Dict,
    artifacts: Dict[str, str],
) -> Dict:
    """Register a new RAG model version with lightweight artifacts only.

    Parameters
    ----------
    model_name:
        Logical name of the model (used for versioned folder naming).
    model_path:
        Optional path or URI to the model weights. If it exists locally we compute a
        SHA256 checksum; otherwise the raw value is stored for reference only.
    pipeline_config:
        Dict describing the pipeline configuration to persist.
    evaluation_metrics:
        Dict containing evaluation scores (expects groundedness, answer_relevance,
        factual_correctness, latency_avg_ms keys).
    artifacts:
        Mapping of artifact labels to file paths to copy (e.g.,
        {"eval_summary": "/path/to/summary.json", "bias_report": "/path/to/bias.json"}).
    """

    registry = _ensure_registry_dir()

    version = _next_version(model_name, registry)
    version_dir = registry / f"{model_name}_{version}"
    version_dir.mkdir(parents=True, exist_ok=True)

    model_reference = {"path": None, "sha256": None}
    if model_path:
        raw_path = model_path.strip()
        model_reference["path"] = raw_path
        model_file = Path(raw_path).expanduser()
        if model_file.exists():
            resolved = str(model_file.resolve())
            model_reference["path"] = resolved
            model_reference["sha256"] = _compute_sha256(model_file)
        else:
            logger.warning(
                "Model path '%s' does not exist locally; metadata will record the raw reference without checksum.",
                raw_path,
            )
    else:
        logger.warning("No model path provided; registry entry will omit model_reference details.")

    # Copy allowed artifacts.
    copied_artifacts: Dict[str, str] = {}
    for key, path_str in (artifacts or {}).items():
        if not path_str:
            continue
        src = Path(path_str).expanduser().resolve()
        copied_name = _copy_artifact(src, version_dir)
        if copied_name:
            copied_artifacts[key] = copied_name

    # Persist pipeline_config as an artifact if provided.
    pipeline_config_path = None
    if pipeline_config:
        pipeline_config_path = version_dir / "pipeline_config.json"
        _write_json(pipeline_config_path, pipeline_config)
        copied_artifacts["pipeline_config"] = pipeline_config_path.name

    metadata = {
        "model_name": model_name,
        "version": version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model_reference": model_reference,
        "pipeline_config": pipeline_config or {},
        "evaluation": {
            "groundedness": evaluation_metrics.get("groundedness"),
            "answer_relevance": evaluation_metrics.get("answer_relevance"),
            "factual_correctness": evaluation_metrics.get("factual_correctness"),
            "latency_avg_ms": evaluation_metrics.get("latency_avg_ms"),
        },
        "artifacts": {
            "eval_summary": copied_artifacts.get("eval_summary"),
            "bias_report": copied_artifacts.get("bias_report"),
            "pipeline_config": copied_artifacts.get("pipeline_config"),
        },
        "previous_version": None,
    }

    # Find previous version (if any).
    prev_versions = sorted(
        [d for d in registry.glob(f"{model_name}_v*") if d.is_dir() and d.name != version_dir.name]
    )
    if prev_versions:
        prev = prev_versions[-1].name.split("_v")[-1]
        metadata["previous_version"] = f"v{prev}"

    metadata_path = version_dir / "metadata.json"
    _write_json(metadata_path, metadata)
    _update_latest_symlink(registry, version_dir)

    logger.info("Registered model '%s' as %s in %s", model_name, version, registry)
    return metadata


__all__ = ["push_to_registry"]
