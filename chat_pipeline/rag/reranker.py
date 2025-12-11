"""Rerank retrieval results by semantic relevance using a cross encoder.

The idea of reranking is to maximise recall during the retrieval step and then
minimise the number of documents that reach the LLM by reordering everything
with a stronger relevance signal.
"""

from __future__ import annotations

import logging
import asyncio
from typing import Dict, List, Literal, Optional

from sentence_transformers import CrossEncoder

from chat_pipeline.rag.retriever import bm25_retrieval, vector_retrieval


logger = logging.getLogger(__name__)

DEFAULT_CROSS_ENCODER = "cross-encoder/ms-marco-MiniLM-L-6-v2"
_CROSS_ENCODER_CACHE: Dict[str, CrossEncoder] = {}


def _get_cross_encoder(model_name: str = DEFAULT_CROSS_ENCODER) -> CrossEncoder:
    """Return (and cache) the configured cross-encoder model."""

    if model_name not in _CROSS_ENCODER_CACHE:
        try:
            logger.info("Loading cross-encoder model %s", model_name)
            _CROSS_ENCODER_CACHE[model_name] = CrossEncoder(model_name)
        except OSError as exc:  # pragma: no cover - download issues
            raise RuntimeError(
                "Cross encoder weights not found locally. Run `pip install sentence-transformers` "
                "and ensure the model '%s' is downloadable from Hugging Face."
                % model_name
            ) from exc
        except Exception as exc:  # pragma: no cover - defensive
            raise RuntimeError(
                f"Unable to load cross encoder '{model_name}'. Set RERANKER_MODEL or disable reranking."
            ) from exc
    return _CROSS_ENCODER_CACHE[model_name]


def two_stage_reranker(
    query: str,
    retrieval: Literal["vector", "bm25"] = "vector",
    top_k: int = 5,
    rerank_k: Optional[int] = None,
    company_name: Optional[str] = None,
    max_documents: Optional[int] = None,
    model_name: str = DEFAULT_CROSS_ENCODER,
    batch_size: Optional[int] = None,
) -> List[Dict[str, object]]:
    """Rerank retrieval results using a cross encoder.

    Parameters
    ----------
    query:
        Natural language question to run through the retriever(s).
    retrieval:
        ``"vector"`` (dense) or ``"bm25"`` (lexical) retrieval backend.
    top_k:
        Number of documents to pull from the first-stage retriever.
    rerank_k:
        Optional cap on how many documents to return after reranking.
        Defaults to ``top_k`` when omitted.
    company_name:
        Optional company filter forwarded to the retrievers.
    max_documents:
        Upper bound for materialising BM25 documents (passed through).
    model_name:
        Cross encoder checkpoint to use for scoring.

    Returns
    -------
    List[Dict[str, object]]
        Each entry contains ``document``, ``metadata`` and the
        ``score`` assigned by the cross encoder.
    """

    retrieval = retrieval.lower()

    if retrieval == "vector":
        docs, metadata = vector_retrieval(
            query=query,
            top_k=top_k,
            company_name=company_name,
        )
    elif retrieval == "bm25":
        docs, metadata = bm25_retrieval(
            query=query,
            top_k=top_k,
            company_name=company_name,
            max_documents=max_documents,
        )
    else:
        raise ValueError("retrieval must be 'vector' or 'bm25'")

    if not docs:
        logger.warning("Retrieval returned no documents for query: %s", query)
        return []

    if not metadata:
        metadata = [{} for _ in docs]
    elif len(metadata) < len(docs):
        metadata = list(metadata) + [{} for _ in range(len(docs) - len(metadata))]

    cross_encoder = _get_cross_encoder(model_name=model_name)
    pairs = [[query, doc] for doc in docs]
    predict_kwargs = {"batch_size": batch_size} if batch_size else {}
    cross_scores = cross_encoder.predict(pairs, **predict_kwargs)

    rerank_limit = rerank_k or top_k
    ranked = sorted(
        (
            {
                "document": doc,
                "metadata": meta,
                "score": float(score),
            }
            for doc, meta, score in zip(docs, metadata, cross_scores)
        ),
        key=lambda item: item["score"],
        reverse=True,
    )

    if rerank_limit is not None:
        ranked = ranked[:rerank_limit]

    return ranked



async def two_stage_reranker_async(
    *args,
    batch_size: Optional[int] = None,
    **kwargs,
) -> List[Dict[str, object]]:
    """Async wrapper around :func:`two_stage_reranker` for high-throughput inference."""

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        lambda: two_stage_reranker(*args, batch_size=batch_size, **kwargs),
    )


__all__ = ["two_stage_reranker", "two_stage_reranker_async"]
        
