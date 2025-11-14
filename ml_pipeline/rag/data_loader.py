"""Utility helpers for loading the FrontShiftAI RAG corpus.

This module centralises the logic for locating, downloading (if required),
and opening the Chroma vector store that backs the RAG pipeline.  It returns
both the raw Chroma collection – used for dense vector search – and a set of
LangChain :class:`~langchain.schema.Document` objects that power lexical
retrievers such as BM25.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.utils import embedding_functions
from langchain_core.documents import Document

from .config_manager import get_vector_store_config


PROJECT_ROOT = Path(
    os.getenv("PROJECT_ROOT", Path(__file__).resolve().parents[2])
)
_DEFAULT_CHROMA_DIR = PROJECT_ROOT / "data_pipeline" / "data" / "vector_db"
VECTOR_CONFIG = get_vector_store_config()

_DEFAULT_COMPANY_INDEX = _DEFAULT_CHROMA_DIR / "company_index.json"

logger = logging.getLogger(__name__)


def _resolve_path(path_value: Optional[str], default: Path) -> Path:
    if not path_value:
        return default
    candidate = Path(path_value)
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    return candidate


def _to_optional_int(value: Optional[str]) -> Optional[int]:
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


CHROMA_DIR = _resolve_path(
    os.getenv("CHROMA_DIR") or VECTOR_CONFIG.get("local_path"),
    _DEFAULT_CHROMA_DIR,
)
CHROMA_REMOTE_URI = os.getenv("CHROMA_REMOTE_URI") or VECTOR_CONFIG.get("remote_uri")
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION") or VECTOR_CONFIG.get("collection", "frontshift_handbooks")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL") or VECTOR_CONFIG.get("embedding_model", "all-MiniLM-L6-v2")
DEFAULT_MAX_DOCUMENTS = (
    _to_optional_int(os.getenv("CHROMA_MAX_DOCUMENTS"))
    or _to_optional_int(VECTOR_CONFIG.get("max_documents"))
    or 1000
)
if DEFAULT_MAX_DOCUMENTS is not None and DEFAULT_MAX_DOCUMENTS <= 0:
    DEFAULT_MAX_DOCUMENTS = None

COMPANY_INDEX_PATH = _resolve_path(
    os.getenv("COMPANY_INDEX_PATH"),
    _DEFAULT_COMPANY_INDEX,
)


def _normalize_company(value: Optional[str]) -> str:
    return (value or "").strip().lower()


@lru_cache(maxsize=1)
def _load_company_index() -> Dict[str, str]:
    """Return a cached lookup table of company names (if available)."""

    try:
        if not COMPANY_INDEX_PATH or not COMPANY_INDEX_PATH.exists():
            return {}
        with COMPANY_INDEX_PATH.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError:
        return {}
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning(
            "Failed to load company index from %s: %s",
            COMPANY_INDEX_PATH,
            exc,
        )
        return {}

    names: List[str] = []
    if isinstance(payload, dict):
        if "companies" in payload and isinstance(payload["companies"], list):
            names = [str(item) for item in payload["companies"]]
        else:
            names = [str(value) for value in payload.values()]
    elif isinstance(payload, list):
        names = [str(item) for item in payload]

    index: Dict[str, str] = {}
    for name in names:
        normalized = _normalize_company(name)
        if normalized:
            index[normalized] = name
    return index


class CompanyCorpus(NamedTuple):
    """Container returned by :func:`load_data_company`.

    Attributes
    ----------
    collection:
        The live Chroma collection handle for dense/vector retrieval.
    documents:
        LangChain ``Document`` objects materialised from the same store,
        suitable for BM25 or other lexical strategies.
    filter_kwargs:
        Optional ``where`` clause applied when fetching data; useful for
        reusing the same filter during collection queries.
    """

    collection: Collection
    documents: List[Document]
    filter_kwargs: Dict[str, Dict]


def ensure_chroma_store(chroma_dir: Path = CHROMA_DIR, remote_uri: Optional[str] = CHROMA_REMOTE_URI) -> Path:
    """Ensure the Chroma vector store is available locally.

    Parameters
    ----------
    chroma_dir:
        Path to the expected local store. Defaults to ``CHROMA_DIR``.
    remote_uri:
        Optional GCS/HTTP URI to sync from when the local store is missing.

    Returns
    -------
    Path
        The directory that contains the Chroma DB files.

    Raises
    ------
    FileNotFoundError
        If the store cannot be found and no remote URI is provided.
    RuntimeError
        If syncing from the remote URI fails.
    """

    chroma_dir = Path(chroma_dir)
    if chroma_dir.exists():
        return chroma_dir

    if not remote_uri:
        raise FileNotFoundError(
            f"Chroma store not found at {chroma_dir}. Set CHROMA_DIR or provide CHROMA_REMOTE_URI."
        )

    chroma_dir.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            ["gsutil", "-m", "rsync", "-r", remote_uri, str(chroma_dir)],
            check=True,
            capture_output=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("gsutil is required to download the remote Chroma store.") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"Failed to download Chroma store from {remote_uri}: {exc.stderr.decode().strip()}"
        ) from exc

    if not chroma_dir.exists():
        raise RuntimeError(f"Chroma store download completed but {chroma_dir} is still missing.")

    return chroma_dir


@lru_cache(maxsize=1)
def _embedding_function():
    """Create (and cache) the sentence transformer embedding function."""

    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )


@lru_cache(maxsize=1)
def get_chroma_client() -> chromadb.PersistentClient:
    """Return a cached Chroma ``PersistentClient`` instance."""

    chroma_path = ensure_chroma_store()
    return chromadb.PersistentClient(path=str(chroma_path))


@lru_cache(maxsize=1)
def get_collection() -> Collection:
    """Open the configured Chroma collection with the shared embedding fn."""

    client = get_chroma_client()
    try:
        return client.get_collection(
            name=COLLECTION_NAME,
            embedding_function=_embedding_function(),
        )
    except Exception as exc:  # pragma: no cover - defensive guard
        raise RuntimeError(
            "Failed to open Chroma collection. The vector store may be corrupt or "
            "incompatible. Try deleting the directory at "
            f"{CHROMA_DIR} and re-syncing it."
        ) from exc


def resolve_company_filter(collection: Collection, company_name: Optional[str]) -> Dict[str, Dict]:
    """Build a case-insensitive ``where`` clause for the requested company."""

    if not company_name:
        return {}

    normalized = _normalize_company(company_name)
    if not normalized:
        return {}

    index = _load_company_index()
    if index:
        if normalized in index:
            return {"where": {"company": index[normalized]}}
        for key, canonical in index.items():
            if normalized in key:
                return {"where": {"company": canonical}}

    try:
        peek = collection.peek(limit=200)
        matches = [
            meta.get("company")
            for meta in peek.get("metadatas", [])
            if normalized in _normalize_company(meta.get("company"))
        ]
        if matches:
            return {"where": {"company": matches[0]}}
    except Exception as exc:  # pragma: no cover - best effort fallback
        logger.debug("Unable to identify company filter via peek(): %s", exc)
    return {}


def _collection_documents(
    collection: Collection,
    where: Optional[Dict] = None,
    limit: Optional[int] = DEFAULT_MAX_DOCUMENTS,
) -> List[Document]:
    """Materialise LangChain ``Document`` objects from a collection snapshot."""

    kwargs: Dict = {"include": ["documents", "metadatas"]}
    if where:
        kwargs["where"] = where
    if limit:
        kwargs["limit"] = limit

    try:
        snapshot = collection.get(**kwargs)
    except Exception as exc:  # pragma: no cover - defensive guard
        raise RuntimeError(
            "Unable to materialise documents from Chroma. If the store was upgraded "
            "with a different Chroma version, re-ingest or resync the store."
        ) from exc
    documents = snapshot.get("documents", [])
    metadatas = snapshot.get("metadatas", [])

    return [
        Document(page_content=doc, metadata=meta or {})
        for doc, meta in zip(documents, metadatas)
    ]


def load_data_company(
    company_name: Optional[str] = None,
    max_documents: Optional[int] = DEFAULT_MAX_DOCUMENTS,
) -> CompanyCorpus:
    """Return the core corpus for the requested company.

    Parameters
    ----------
    company_name:
        Optional company filter applied to both vector and lexical views.
    max_documents:
        Optional guard to avoid loading the entire collection when BM25 only
        needs a subset. Defaults to ``CHROMA_MAX_DOCUMENTS`` when set.

    Returns
    -------
    CompanyCorpus
        The NamedTuple containing the ``collection`` handle, ``documents``
        list, and ``filter_kwargs`` (for reuse in vector queries).
    """

    collection = get_collection()
    filter_kwargs = resolve_company_filter(collection, company_name)
    documents = _collection_documents(
        collection,
        where=filter_kwargs.get("where"),
        limit=max_documents,
    )

    return CompanyCorpus(collection=collection, documents=documents, filter_kwargs=filter_kwargs)


__all__ = [
    "CompanyCorpus",
    "load_data_company",
    "get_collection",
    "ensure_chroma_store",
]
