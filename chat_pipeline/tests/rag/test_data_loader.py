import json
from pathlib import Path

import pytest

chromadb = pytest.importorskip("chromadb")

from chat_pipeline.rag import data_loader


def test_resolve_path_handles_relative(monkeypatch, tmp_path):
    relative = "foo/bar"
    monkeypatch.setattr(data_loader, "PROJECT_ROOT", tmp_path)
    result = data_loader._resolve_path(relative, tmp_path)
    assert result == tmp_path / relative


def test_to_optional_int_parsing():
    assert data_loader._to_optional_int("10") == 10
    assert data_loader._to_optional_int("") is None
    assert data_loader._to_optional_int("abc") is None


def test_load_company_index_reads_names(monkeypatch, tmp_path):
    idx_file = tmp_path / "companies.json"
    idx_file.write_text(json.dumps({"companies": ["Acme Co", "Beta Inc"]}), encoding="utf-8")
    monkeypatch.setattr(data_loader, "COMPANY_INDEX_PATH", idx_file)
    data_loader._load_company_index.cache_clear()

    index = data_loader._load_company_index()

    assert index["acme co"] == "Acme Co"
    assert index["beta inc"] == "Beta Inc"
