"""Helpers for loading ``rag.yaml`` configuration files."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

import logging

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "configs" / "rag.yaml"

logger = logging.getLogger(__name__)

DEFAULT_CONFIG: Dict[str, Any] = {
    "vector_store": {
        "local_path": str(PROJECT_ROOT / "data_pipeline" / "data" / "vector_db"),
        "remote_uri": None,
        "collection": "frontshift_handbooks",
        "embedding_model": "all-MiniLM-L6-v2",
        "max_documents": None,
    },
    "pipeline": {
        "retriever": {
            "name": "vector",
            "top_k": 5,
            "max_documents": None,
        },
        "reranker": {
            "enabled": False,
            "strategy": "two_stage",
            "rerank_k": None,
            "batch_size": 16,
        },
        "generation": {
            "template_key": "general_prompt_1",
            "stream": False,
            "streaming_overrides": {},
        },
    },
    "streaming": {
        "max_tokens": 1024,
        "temperature": 0.6,
        "top_p": 0.9,
        "repeat_penalty": 1.1,
        "stop": ["---", "Thank you"],
    },
}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if (
            key in merged
            and isinstance(merged[key], dict)
            and isinstance(value, dict)
        ):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


@lru_cache(maxsize=1)
def load_rag_config() -> Dict[str, Any]:
    """Return the parsed ``rag.yaml`` configuration (with defaults)."""

    config_path = Path(os.getenv("RAG_CONFIG_PATH", DEFAULT_CONFIG_PATH))
    data: Dict[str, Any] = {}
    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file) or {}
    merged = _deep_merge(DEFAULT_CONFIG, data)
    _validate_config(merged)
    return merged


def get_vector_store_config() -> Dict[str, Any]:
    """Shortcut to the ``vector_store`` section of ``rag.yaml``."""

    return load_rag_config().get("vector_store", {})


def get_streaming_config() -> Dict[str, Any]:
    """Shortcut to the ``streaming`` section of ``rag.yaml``."""

    return load_rag_config().get("streaming", {})


def get_generation_config() -> Dict[str, Any]:
    """Shortcut to the ``pipeline.generation`` section of ``rag.yaml``."""

    pipeline_cfg = load_rag_config().get("pipeline", {}) or {}
    return pipeline_cfg.get("generation", {}) or {}


def _validate_config(config: Dict[str, Any]) -> None:
    allowed_top_level = {"vector_store", "pipeline", "streaming"}
    unknown = set(config) - allowed_top_level
    if unknown:
        logger.warning("Unknown top-level RAG config keys: %s", ", ".join(sorted(unknown)))

    pipeline_cfg = config.get("pipeline")
    if pipeline_cfg is not None and not isinstance(pipeline_cfg, dict):
        raise ValueError("pipeline configuration must be a dictionary")
    vector_cfg = config.get("vector_store")
    if vector_cfg is not None and not isinstance(vector_cfg, dict):
        raise ValueError("vector_store configuration must be a dictionary")
    streaming_cfg = config.get("streaming")
    if streaming_cfg is not None and not isinstance(streaming_cfg, dict):
        raise ValueError("streaming configuration must be a dictionary")


__all__ = ["load_rag_config", "get_vector_store_config", "get_streaming_config"]
