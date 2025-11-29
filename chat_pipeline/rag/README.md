# Retrieval-Augmented Generation (RAG) Folder

This folder contains the “answering engine” that powers the chat experience. It is responsible for pulling the right context from the company handbook and working with different language-model backends to craft a grounded answer. Below is a plain-language walkthrough of each component and how they cooperate.

---

## 1. Step-by-step Flow

1. **Configuration** – `config_manager.py` reads `configs/rag.yaml`, blends in sensible defaults, and exposes helper functions so the rest of the code knows which retriever, reranker, and generator to use.
2. **Data loading** – `data_loader.py` ensures the Chroma vector database exists locally. If the data lives on a remote bucket (GCS), it can sync it down. It then returns LangChain `Document` objects that contain the text and metadata for every handbook chunk.
3. **Retrieval** – `retriever.py` implements two options:
   - `vector_retrieval` uses dense embeddings to find the most similar passages.
   - `bm25_retrieval` falls back to a traditional keyword/BM25 search.
   The pipeline can combine these or choose one via config.
4. **Reranking (optional)** – `reranker.py` uses a cross-encoder to score each candidate passage in context with the user question. This step cuts down noise before we hand the passages to the language model.
5. **Prompt building and generation** – `generator.py` assembles the final prompt (using templates from `prompt_templates.py`) and calls the configured backend:
   - `local` – llama.cpp model pointed to by `LLAMA_MODEL_PATH`.
   - `hf` – Hugging Face Inference API (needs `HF_API_TOKEN`).
   - `mercury` – Inception/Mercury API (needs `INCEPTION_API_KEY`).
   The backend can also be set to `auto`, where the code chooses based on availability.
6. **Pipeline orchestration** – `pipeline.py` exposes the `RAGPipeline` class and a CLI entrypoint. `RAGPipeline.run()` ties everything together (retrieval → rerank → generation), keeps track of timings, and returns a `PipelineResult` object with the final answer, metadata, and which backend handled the request.

---

## 2. Important Files

| File | Role |
| --- | --- |
| `config_manager.py` | Loads `configs/rag.yaml`, validates structure, and provides helper getters for vector store, streaming, and generation settings. |
| `data_loader.py` | Opens or syncs the vector database. Also prepares data structures for lexical (BM25) use. |
| `retriever.py` | Implements vector and BM25 retrieval along with utilities to merge results. |
| `reranker.py` | Contains the two-stage reranker and caches the cross-encoder model for efficiency. |
| `prompt_templates.py` | Houses all system/user prompt templates. Each template has a human-friendly key so configs can refer to them. |
| `generator.py` | Chooses the backend, prepares API calls or llama.cpp contexts, supports streaming, and records token usage/latency. |
| `pipeline.py` | High-level class plus CLI for running the pipeline directly or embedding it inside other tooling. |

---

## 3. Configuration Tips

All RAG-specific knobs live in `configs/rag.yaml`. Common fields include:

- `vector_store.local_path` – Where the Chroma database sits on disk.
- `vector_store.remote_uri` – Optional GCS path so workflows can sync the database before running.
- `pipeline.retriever.name` – `vector` or `bm25`.
- `pipeline.retriever.top_k` – Number of passages to pull.
- `pipeline.reranker.enabled` – Turn the cross-encoder reranker on/off.
- `pipeline.generation.template_key` – Which prompt template to use.

Environment variables like `GENERATION_BACKEND`, `LLAMA_MODEL_PATH`, and `HF_MODEL_NAME` override these defaults at runtime. The GitHub workflows export them automatically so the self-hosted runners use the local llama-cpp weights while cloud runners can fall back to hosted APIs.

---

## 4. Running the RAG Pipeline Manually

For quick testing, you can run the CLI directly:
```bash
python -m chat_pipeline.rag.pipeline \
  --question "How do I report a safety incident?" \
  --company "FrontShift" \
  --template general_prompt_1
```
Useful flags (see `pipeline.py --help`):
- `--retriever vector|bm25`
- `--top-k 5`
- `--backend local|hf|mercury|auto`
- `--stream` to stream tokens as they arrive

The CLI prints the answer plus the top contexts so you can visually inspect groundedness.

---

## 5. Troubleshooting Checklist

- **“Vector store not found”** – Ensure `CHROMA_DIR` points to a folder that contains `chroma.sqlite3` and related artifacts. Run the provided `gsutil rsync` command (see workflows) to sync from GCS if needed.
- **“Backend failed”** – Verify the corresponding API keys (`HF_API_TOKEN`, `INCEPTION_API_KEY`, `OPENAI_API_KEY`) are set. When using llama.cpp make sure the wheel matches your CPU/GPU setup and that `LLAMA_MODEL_PATH` points to an actual `.gguf` file.
- **Unexpected prompt or tone** – Check `configs/rag.yaml` for the `pipeline.generation.template_key`. Templates live in `prompt_templates.py`; tweak them there.
- **Slow responses** – Reduce `top_k`, disable the reranker, or switch to a faster backend. The `pipeline.py` logs include per-stage timings to help diagnose bottlenecks.

---

By understanding the pieces inside the `rag/` folder you can confidently adjust retrieval strategies, change prompt templates, or onboard new backends without touching the evaluation and deployment layers. Everything is designed to be modular: once the `RAGPipeline` returns a `PipelineResult`, the rest of the system treats it as a black box.***
