from types import SimpleNamespace

import pytest

from chat_pipeline.rag import reranker


class DummyEncoder:
    def __init__(self, scores):
        self.scores = scores

    def predict(self, pairs, **kwargs):
        assert len(pairs) == len(self.scores)
        return self.scores


def test_two_stage_reranker_vector(monkeypatch):
    monkeypatch.setattr("chat_pipeline.rag.reranker.vector_retrieval", lambda **_: (["doc1", "doc2"], [{"meta": 1}]))
    monkeypatch.setattr("chat_pipeline.rag.reranker._get_cross_encoder", lambda model_name=reranker.DEFAULT_CROSS_ENCODER: DummyEncoder([0.1, 0.9]))

    ranked = reranker.two_stage_reranker("question", retrieval="vector", top_k=2, rerank_k=1)

    assert len(ranked) == 1
    assert ranked[0]["document"] == "doc2"  # highest score
    assert isinstance(ranked[0]["metadata"], dict)


def test_two_stage_reranker_handles_empty(monkeypatch):
    monkeypatch.setattr("chat_pipeline.rag.reranker.vector_retrieval", lambda **_: ([], []))

    result = reranker.two_stage_reranker("question", retrieval="vector")

    assert result == []


def test_two_stage_reranker_invalid_backend():
    with pytest.raises(ValueError):
        reranker.two_stage_reranker("q", retrieval="unknown")  # type: ignore[arg-type]


def test_two_stage_reranker_pads_metadata(monkeypatch):
    monkeypatch.setattr("chat_pipeline.rag.reranker.vector_retrieval", lambda **_: (["a", "b"], [{}]))
    monkeypatch.setattr("chat_pipeline.rag.reranker._get_cross_encoder", lambda model_name=reranker.DEFAULT_CROSS_ENCODER: DummyEncoder([0.3, 0.2]))

    ranked = reranker.two_stage_reranker("q", retrieval="vector", top_k=2)

    assert len(ranked) == 2
    assert ranked[1]["metadata"] == {}
