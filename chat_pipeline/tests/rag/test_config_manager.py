import os
from pathlib import Path

import yaml

from chat_pipeline.rag import config_manager


def _write_config(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "rag.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def test_load_rag_config_merges_defaults(monkeypatch, tmp_path):
    overrides = {
        "pipeline": {
            "retriever": {"top_k": 42},
        },
        "vector_store": {"collection": "custom"},
    }
    config_path = _write_config(tmp_path, overrides)
    monkeypatch.setenv("RAG_CONFIG_PATH", str(config_path))
    config_manager.load_rag_config.cache_clear()

    loaded = config_manager.load_rag_config()

    assert loaded["pipeline"]["retriever"]["top_k"] == 42
    # Should still include defaults that were not overridden.
    assert "streaming" in loaded
    assert loaded["vector_store"]["collection"] == "custom"


def test_get_vector_store_config_returns_section(monkeypatch, tmp_path):
    overrides = {"vector_store": {"max_documents": 99}}
    config_path = _write_config(tmp_path, overrides)
    monkeypatch.setenv("RAG_CONFIG_PATH", str(config_path))
    config_manager.load_rag_config.cache_clear()

    section = config_manager.get_vector_store_config()

    assert section["max_documents"] == 99
    # Ensure we inherit defaults for missing keys.
    assert "collection" in section
