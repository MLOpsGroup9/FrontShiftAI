# 📁 RAG Module

### Purpose
Handles the **retrieval-augmented generation pipeline** — retrieves context from the vector store and generates grounded responses using LLMs.

---

### ✅ Existing Scripts
| File | Description |
|------|--------------|
| `rag_query_utils.py` | Core RAG utilities — embedding, retrieval, and context construction. |
| `test_rag_llama.py` | Current test harness for retriever–generator pipeline using Llama. |

---

### 🧠 To-Do
- [ ] Modularize `test_rag_llama.py` into `retriever.py` and `generator.py`.
- [ ] Add vector store versioning (GCS or DVC).
- [ ] Integrate reranker (optional) for improved context ordering.
- [ ] Add a caching layer for embeddings.
- [ ] Write integration tests under `tests/`.