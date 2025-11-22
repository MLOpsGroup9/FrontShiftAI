from types import SimpleNamespace

import pytest

from chat_pipeline.rag.retriever import CompanyCorpus, vector_retrieval, bm25_retrieval


class DummyCollection:
    def __init__(self, response):
        self.response = response
        self.last_args = None

    def query(self, **kwargs):
        self.last_args = kwargs
        return self.response


def test_vector_retrieval_returns_documents(monkeypatch):
    response = {
        "documents": [["doc-1", "doc-2"]],
        "metadatas": [[{"id": 1}, {"id": 2}]],
        "distances": [[0.2, 0.4]],
    }
    collection = DummyCollection(response)

    def fake_loader(company_name=None, max_documents=None):
        return CompanyCorpus(collection=collection, documents=[], filter_kwargs={"where": {"company": company_name}})

    monkeypatch.setattr("chat_pipeline.rag.retriever.load_data_company", fake_loader)

    docs, metadata = vector_retrieval("hello", top_k=2, company_name="ACME")

    assert docs == ["doc-1", "doc-2"]
    assert metadata[0]["id"] == 1
    assert metadata[1]["id"] == 2
    assert metadata[0]["retrieval_distance"] == pytest.approx(0.2)
    assert metadata[0]["retrieval_score"] == pytest.approx(1 / 1.2)
    assert collection.last_args["n_results"] == 2
    assert collection.last_args["where"]["company"] == "ACME"


def test_vector_retrieval_handles_empty(monkeypatch):
    collection = DummyCollection({"documents": []})

    def fake_loader(company_name=None, max_documents=None):
        return CompanyCorpus(collection=collection, documents=[], filter_kwargs={})

    monkeypatch.setattr("chat_pipeline.rag.retriever.load_data_company", fake_loader)

    docs, metadata = vector_retrieval("empty")

    assert docs == []
    assert metadata == []


def test_bm25_retrieval(monkeypatch):
    documents = [
        SimpleNamespace(page_content="alpha", metadata={"source": 1}, score=0.9),
        SimpleNamespace(page_content="beta", metadata={}, score=None),
    ]

    class DummyBM25:
        def __init__(self, docs, k):
            self.docs = docs
            self.k = k

        @classmethod
        def from_documents(cls, docs, k):
            return cls(docs, k)

        def invoke(self, query):
            return self.docs

    def fake_loader(company_name=None, max_documents=None):
        return CompanyCorpus(collection=None, documents=documents, filter_kwargs={})

    monkeypatch.setattr("chat_pipeline.rag.retriever.load_data_company", fake_loader)
    monkeypatch.setattr("chat_pipeline.rag.retriever.BM25Retriever", DummyBM25)

    docs, metadata = bm25_retrieval("query", top_k=2)

    assert docs == ["alpha", "beta"]
    assert metadata[0]["bm25_score"] == 0.9
    assert metadata[0]["retrieval_score"] == pytest.approx(0.9)
    assert "bm25_score" not in metadata[1] or metadata[1]["bm25_score"] is None
