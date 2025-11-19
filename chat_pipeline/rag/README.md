# Retrieval-Augmented Generation (RAG)

This folder implements the RAG pipeline: load the vector store, retrieve context, optionally rerank, build a prompt, and call an LLM backend.

## Modules
- `config_manager.py`: Reads `configs/rag.yaml`, merges defaults, exposes helpers to other modules.
- `data_loader.py`: Ensures the Chroma store exists (local, GCS sync, or DVC), opens the collection, and materialises LangChain `Document` objects for lexical/BM25 use.
- `retriever.py`: Dense vector retrieval (`vector_retrieval`) and BM25 retrieval (`bm25_retrieval`).
- `reranker.py`: Two-stage reranker using a cross-encoder; reduces the context set before generation.
- `prompt_templates.py`: System prompts keyed by template name.
- `generator.py`: Fetches context, builds the prompt, and streams a response using the selected backend (local llama-cpp, Hugging Face Inference, or Mercury). Chooses backend from `GENERATION_BACKEND` in the environment, with `rag.yaml` as fallback.
- `pipeline.py`: High-level orchestrator. `RAGPipeline.run()` executes retrieval → rerank → generation, tracks timings, and returns a `PipelineResult`. Also provides a CLI entrypoint.

## Flow
1) Config is loaded from `rag.yaml`.  
2) Vector store is loaded via `data_loader`.  
3) Retriever fetches candidate chunks; reranker (optional) reorders them.  
4) Generator builds a prompt from `prompt_templates` and streams tokens from the chosen backend.  
5) `pipeline.RAGPipeline` ties timing, caching, and result packaging together.

Backend notes: `.env` overrides backend selection. For llama-cpp GPU offload, ensure the wheel is built with GPU support and set `LLAMA_N_GPU_LAYERS`. HF and Mercury require tokens/keys.***
