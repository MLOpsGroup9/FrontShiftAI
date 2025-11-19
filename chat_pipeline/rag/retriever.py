"""Retrieval helpers for the RAG pipeline."""

from typing import Dict, List, Optional, Tuple
from langchain_community.retrievers import BM25Retriever
from chat_pipeline.rag.data_loader import CompanyCorpus, load_data_company


def vector_retrieval(
    query: str,
    top_k: int = 10,
    company_name: Optional[str] = None,
) -> Tuple[List[str], List[Dict]]:
    """Run a dense vector search against the company corpus."""

    corpus: CompanyCorpus = load_data_company(company_name=company_name)
    args = {"query_texts": [query], "n_results": top_k}
    args.update(corpus.filter_kwargs)

    result = corpus.collection.query(**args)

    if not result.get("documents"):
        return [], []

    return result["documents"][0], result["metadatas"][0]


def bm25_retrieval(
    query: str,
    top_k: int = 10,
    company_name: Optional[str] = None,
    max_documents: Optional[int] = None,
) -> Tuple[List[str], List[Dict]]:
    """Run a BM25 search over the materialised LangChain documents."""

    corpus: CompanyCorpus = load_data_company(
        company_name=company_name,
        max_documents=max_documents,
    )

    if not corpus.documents:
        return [], []

    retriever = BM25Retriever.from_documents(corpus.documents, k=top_k)
    results = retriever.invoke(query)
    results = results if isinstance(results, list) else [results]

    documents: List[str] = []
    metadatas: List[Dict] = []
    for doc in results:
        documents.append(doc.page_content)
        meta = dict(getattr(doc, "metadata", {}) or {})
        score = getattr(doc, "score", None) or meta.get("score")
        if score is not None:
            meta.setdefault("bm25_score", score)
        metadatas.append(meta)

    return documents, metadatas


def fusion_retrieval(*_args, **_kwargs):  # pragma: no cover - placeholder utility
    """Placeholder for reciprocal-rank fusion between dense and lexical search."""

    raise NotImplementedError("Fusion retrieval is not implemented yet.")
