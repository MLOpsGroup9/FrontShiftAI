import types

import pytest

from chat_pipeline.rag import generator


def test_align_metadata_extends_shorter_list():
    docs = ["a", "b"]
    metadata = [{"id": 1}]

    aligned = generator._align_metadata(docs, metadata)

    assert len(aligned) == 2
    assert aligned[0]["id"] == 1
    assert aligned[1] == {}


def test_align_metadata_raises_on_large_mismatch():
    docs = ["d"] * (generator.METADATA_MISMATCH_THRESHOLD + 2)

    with pytest.raises(ValueError):
        generator._align_metadata(docs, [{}])


def _fake_stream_response(*_args, **_kwargs):
    yield "Answer"


def test_generation_with_documents(monkeypatch):
    monkeypatch.setattr(generator, "stream_response", _fake_stream_response)
    monkeypatch.setattr(generator, "_select_prompt_template", lambda key: "template")
    monkeypatch.setattr(generator, "_prepare_context", lambda docs: "context")
    monkeypatch.setattr(generator, "_build_prompt", lambda template, context, query: "prompt")

    docs = ["doc1"]
    metadata = [{"company": "ACME"}]

    answer, meta = generator.generation(
        query="question",
        documents=docs,
        metadatas=metadata,
    )

    assert answer == "Answer"
    assert meta == metadata


def test_generation_streams_when_requested(monkeypatch):
    def fake_stream_response(*_args, **_kwargs):
        yield "chunk1"

    monkeypatch.setattr(generator, "stream_response", fake_stream_response)
    monkeypatch.setattr(generator, "_select_prompt_template", lambda key: "template")
    monkeypatch.setattr(generator, "_prepare_context", lambda docs: "context")
    monkeypatch.setattr(generator, "_build_prompt", lambda template, context, query: "prompt")

    stream, _ = generator.generation(
        query="question",
        documents=["doc"],
        metadatas=[{}],
        stream=True,
    )

    assert list(stream) == ["chunk1"]


def test_run_retrieval_with_reranker(monkeypatch):
    reranked = [
        {"document": "docA", "metadata": {"rank": 1}},
        {"document": "docB", "metadata": {"rank": 2}},
    ]
    monkeypatch.setattr(generator, "two_stage_reranker", lambda **_: reranked)

    docs, metadata = generator._run_retrieval(
        query="q",
        retriever="vector",
        top_k=2,
        company_name=None,
        reranker="two_stage",
        rerank_k=2,
        max_documents=None,
    )

    assert docs == ["docA", "docB"]
    assert metadata == [{"rank": 1}, {"rank": 2}]


def test_run_retrieval_invalid_backend():
    with pytest.raises(ValueError):
        generator._run_retrieval("q", retriever="invalid", top_k=1, company_name=None, reranker=None, rerank_k=None, max_documents=None)  # type: ignore[arg-type]
