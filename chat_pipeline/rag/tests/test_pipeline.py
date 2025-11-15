from types import SimpleNamespace

import pytest

from rag import pipeline


def test_call_component_filters_kwargs():
    def component(a: int) -> int:
        return a

    result = pipeline._call_component(component, a=3, b=4)
    assert result == 3


def test_deep_merge_handles_nested():
    base = {"a": {"b": 1}, "c": 2}
    override = {"a": {"b": 5}, "d": 9}
    merged = pipeline._deep_merge(base, override)

    assert merged["a"]["b"] == 5
    assert merged["c"] == 2
    assert merged["d"] == 9
    assert base["a"]["b"] == 1  # original untouched


def test_rag_pipeline_cache(monkeypatch):
    sample_config = {
        "retriever": {"name": "vector", "top_k": 1},
        "reranker": {"enabled": False, "strategy": "two_stage"},
        "generation": {"stream": False, "template_key": None, "streaming_overrides": {}},
    }
    monkeypatch.setattr(pipeline, "load_pipeline_config", lambda overrides=None: sample_config)

    call_count = {"generation": 0, "retrieval": 0}

    def fake_generation(**kwargs):
        call_count["generation"] += 1
        return "answer", [{"id": 1}]

    def fake_execute(self, query, company_name, settings):
        call_count["retrieval"] += 1
        return ["doc"], [{"id": 1}]

    monkeypatch.setattr(pipeline, "generation", fake_generation)
    monkeypatch.setattr(pipeline.RAGPipeline, "_validate_components", lambda *args, **kwargs: None)
    monkeypatch.setattr(pipeline.RAGPipeline, "_execute_retrieval", fake_execute)

    rag = pipeline.RAGPipeline(cache_size=8)
    result1 = rag.run("hello")
    result2 = rag.run("hello")

    assert result1.answer == "answer"
    assert result2.answer == "answer"
    assert call_count["generation"] == 1  # second call served from cache


def test_filter_by_company(monkeypatch):
    sample_config = {
        "retriever": {"name": "vector", "top_k": 1},
        "reranker": {"enabled": False},
        "generation": {"stream": False, "template_key": None, "streaming_overrides": {}},
    }
    monkeypatch.setattr(pipeline, "load_pipeline_config", lambda overrides=None: sample_config)
    rag = pipeline.RAGPipeline(cache_size=0)

    docs = ["doc-a", "doc-b"]
    metadata = [{"company": "Acme Corp"}, {"company": "Other"}]

    filtered_docs, filtered_meta = rag._filter_by_company("acme", docs, metadata)
    assert filtered_docs == ["doc-a"]
    assert filtered_meta == [{"company": "Acme Corp"}]

    fallback_docs, fallback_meta = rag._filter_by_company("missing", docs, metadata)
    assert fallback_docs == docs
    assert fallback_meta == metadata
