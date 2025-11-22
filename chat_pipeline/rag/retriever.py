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

    documents = result["documents"][0]
    raw_meta = (result.get("metadatas") or [[]])[0] or []
    metadata: List[Dict] = [dict(item or {}) for item in raw_meta]
    if len(metadata) < len(documents):
        metadata.extend({} for _ in range(len(documents) - len(metadata)))
    distances = (result.get("distances") or [[]])
    distance_row = distances[0] if distances else []
    for idx, meta in enumerate(metadata):
        if distance_row and idx < len(distance_row):
            try:
                distance = float(distance_row[idx])
                meta["retrieval_distance"] = distance
                meta["retrieval_score"] = 1.0 / (1.0 + distance)
            except (TypeError, ValueError):
                continue
    return documents, metadata


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
        if meta.get("bm25_score") is not None:
            try:
                meta["retrieval_score"] = float(meta["bm25_score"])
            except (TypeError, ValueError):
                pass
        metadatas.append(meta)

    return documents, metadatas


def fusion_retrieval(*_args, **_kwargs):  # pragma: no cover - placeholder utility
    """Placeholder for reciprocal-rank fusion between dense and lexical search."""

    raise NotImplementedError("Fusion retrieval is not implemented yet.")
