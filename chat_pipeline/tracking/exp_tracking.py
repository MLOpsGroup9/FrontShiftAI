"""Lightweight, defensive W&B experiment tracking helpers."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

try:  # Optional dependency at runtime
    import wandb  # type: ignore
except ImportError:  # pragma: no cover - optional
    wandb = None  # type: ignore


DEFAULT_PROJECT = os.getenv("WANDB_PROJECT", "FrontShiftAI")
DEFAULT_ENTITY = os.getenv("WANDB_ENTITY", "group9mlops-northeastern-university")


def _has_wandb() -> bool:
    if wandb is None:
        logger.info("wandb is not installed; skipping experiment tracking.")
        return False
    return True


def start_run(
    stage_name: str,
    model_name: Optional[str] = None,
    *,
    project: Optional[str] = None,
    entity: Optional[str] = None,
    config: Optional[Dict] = None,
    tags: Optional[list] = None,
    disabled: bool = False,
):
    """Start a W&B run defensively. Returns the run or ``None`` if disabled/unsupported."""

    if disabled or not _has_wandb():
        return None

    try:
        run = wandb.init(  # type: ignore[attr-defined]
            project=project or DEFAULT_PROJECT,
            entity=entity or DEFAULT_ENTITY,
            job_type=stage_name,
            name=f"{stage_name}_{model_name or 'run'}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            config=config or {"stage": stage_name, "model_name": model_name},
            reinit=True,
            tags=tags,
        )
        logger.info("Started W&B run for stage '%s'.", stage_name)
        return run
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Unable to start W&B run: %s", exc)
        return None


def log_metrics(run, metrics: Dict) -> None:
    """Log metrics to an active W&B run. No-op if run is None."""

    if not run or not _has_wandb():
        return
    try:
        wandb.log(metrics)  # type: ignore[attr-defined]
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to log metrics to W&B: %s", exc)


def log_artifacts(run, artifacts: Dict[str, Path], artifact_type: str = "dataset") -> None:
    """Upload artifacts if the run is active and files exist."""

    if not run or not _has_wandb():
        return

    for name, path in artifacts.items():
        p = Path(path)
        if not p.exists():
            logger.info("Skipping artifact %s (missing): %s", name, p)
            continue
        try:
            art = wandb.Artifact(f"{name}", type=artifact_type)  # type: ignore[attr-defined]
            art.add_file(str(p))
            run.log_artifact(art)  # type: ignore[attr-defined]
            logger.info("Uploaded artifact: %s", p)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to upload artifact %s: %s", name, exc)


def finish_run(run) -> None:
    if not run or not _has_wandb():
        return
    try:
        run.finish()  # type: ignore[attr-defined]
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to finish W&B run: %s", exc)


def log_stage(
    stage_name: str,
    model_name: str,
    metrics: Dict,
    *,
    artifacts: Optional[Dict[str, Path]] = None,
    project: Optional[str] = None,
    entity: Optional[str] = None,
    config: Optional[Dict] = None,
    tags: Optional[list] = None,
    disabled: bool = False,
) -> None:
    """Convenience one-shot logger for a stage."""

    run = start_run(
        stage_name=stage_name,
        model_name=model_name,
        project=project,
        entity=entity,
        config=config,
        tags=tags,
        disabled=disabled,
    )
    log_metrics(run, metrics)
    if artifacts:
        log_artifacts(run, artifacts)
    finish_run(run)


__all__ = ["start_run", "log_metrics", "log_artifacts", "finish_run", "log_stage"]
