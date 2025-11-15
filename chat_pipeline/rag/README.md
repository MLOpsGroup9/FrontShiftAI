# 📁 Retrieval-Augmented Generation (RAG) Module

This package wires together our retrieval system, reranker, and multiple LLM backends. Everything is driven by the config in `configs/rag.yaml`, and the components can be swapped or extended by editing the submodules below.

## File-by-file Overview

| Path | Role |
| ---- | ---- |
| `config_manager.py` | Loads `rag.yaml`, merges it with sane defaults, and exposes helpers like `load_rag_config()` / `get_vector_store_config()`. All downstream modules call into this to stay consistent. |
| `data_loader.py` | Finds or downloads the Chroma vector store, exposes `load_data_company()` which returns both the dense collection handle and BM25-ready LangChain documents, and normalises company filters. |
| `retriever.py` | Implements `vector_retrieval()` and `bm25_retrieval()` using the corpus from `data_loader`. Both return lists of documents + metadata dictionaries that downstream stages consume. |
| `reranker.py` | Optional two-stage reranking built on `sentence-transformers` cross encoders. Given a query and an initial result set, it reorders documents so the generator only sees the most relevant chunks. |
| `prompt_templates.py` | Dictionary of system prompts keyed by template name. The generator looks up `template_key` here before constructing the final prompt. |
| `generator.py` | High-level glue that takes a question, fetches context (via retriever + optional reranker), builds a prompt, and streams a response from whichever LLM backend is available (local LLaMA, HuggingFace Inference, or Inception Labs Mercury). Includes utilities for context truncation, caching LLaMA instances, and error fallbacks. |
| `pipeline.py` | User-facing orchestrator. `RAGPipeline.run()` loads config, executes retrieval/reranking/generation, tracks timings, optionally caches answers, and returns a `PipelineResult`. The CLI entry point in this file is how we drive the RAG stack end-to-end. |
| `tests/` | Lightweight unit tests for each module. They mock heavy dependencies (Chroma, transformers) so we get quick regression coverage without external services. |

## How it fits together

1. **Configuration** – `config_manager` parses `rag.yaml`, ensuring every component sees the same knobs.
2. **Data access** – `data_loader` provides company-specific contexts to the retrievers.
3. **Retrieval** – `retriever` fetches candidate chunks (dense or BM25). `reranker` can optionally reorder them with a cross encoder.
4. **Prompting + Generation** – `generator` builds a context-aware prompt from `prompt_templates` and streams a grounded answer using the configured LLM backend.
5. **Pipeline orchestration** – `pipeline.RAGPipeline` stitches the above steps, adds caching/latency tracking, and exposes both a Python API and a CLI.

Refer to `tests/` for concrete usage examples and integration sanity checks.
