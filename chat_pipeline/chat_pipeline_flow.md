This document explains, in plain English, how our entire chat/evaluation pipeline works end-to-end. Think of this as the “What actually happens behind the scenes?” guide.

---

## 1. Test Question Generation (Question Synthesis)

**Goal:** Automatically create a large, diverse test set of questions for evaluating our RAG system.

### How it works
1. We start with a small set of seed questions that we write manually.
2. `evaluation/test_questions/generation.py` reads these seeds from `configs/test_set.yaml`.
3. For each seed question, it asks a Large Language Model (GPT-4o-mini, Mercury, or a local model) to generate **exactly one** new question using a strict JSON prompt.
4. The script keeps generating new questions until it hits each category’s required count.
5. All generated questions are saved as JSONL files under:
   - `evaluation/test_questions/general/`
   - `evaluation/test_questions/domain/`
   - `evaluation/test_questions/slices/`

👉 *In short: You give it a handful of seeds → it turns them into hundreds of clean, unique test questions.*

---

## 2. Evaluation Runner (Automated RAG Testing)

**Goal:** Test the actual RAG pipeline on every generated question.

`evaluation/evaluation_runner.py`:
1. Reads all JSONL test questions.
2. Sends each question to our production RAG pipeline, which includes:
   - Vector retrieval (Chroma)
   - Optional BM25 retrieval
   - Optional reranking (Cross-Encoder, etc.)
   - Answer generation using LLaMA / Hugging Face Inference / Mercury
3. Collects for every query:
   - Final answer
   - Retrieved contexts
   - Latencies (retriever, reranker, generator)
   - Token usage and estimated cost
4. Immediately hands the result to our LLM judge.

👉 *In short: It runs every question through the real RAG stack and records everything.*

---

## 3. LLM Judge (Quality Evaluation)

**Goal:** Score each RAG answer automatically using an LLM.

`evaluation/eval_judge.py` + `JudgeClient`:
1. Take the original question, retrieved context, and final RAG answer.
2. Ask a judge model to score:
   - Relevance, Groundedness, Hallucination, Correctness, Coherence, Conciseness
3. GPT-4o-mini is used when available. Otherwise we fall back to:
   - Meta-Llama-3.1-8B (local/Hugging Face)
   - Qwen-2.5-3B (local/Hugging Face)

👉 *In short: Every answer is graded by the best available LLM, and the judge always returns the same JSON schema.*

---

## 4. Metrics & Artifacts

**Goal:** Produce a clean set of metrics, logs, and summaries for the team to review.

The evaluation runner writes:

- **Per-question JSON** → `evaluation/eval_results/<timestamp>/*.json`
  - Includes the question, answer, contexts, timings, costs, judge scores.
- **Summary JSON** → `evaluation/eval_results/<timestamp>/summary.json`
  - Contains averages (relevance, groundedness, hallucination rate), average latencies, total cost, throughput, and category/domain breakdowns.
- **Optional W&B logging** for dashboards.

👉 *In short: Every run outputs a traceable artifact trail plus an aggregate report.*

---

## 5. RAG Core Pipeline (`chat_pipeline/rag/`)

This is the “engine room” of our system:

1. `config_manager` – loads model/reranker/vectorstore settings from `rag.yaml`.
2. `data_loader` – opens Chroma/BM25 corpora and handles company filtering.
3. `retriever` – vector + BM25 retrieval helpers returning documents + metadata.
4. `reranker` – optional cross-encoder reranking stage.
5. `generator` – builds prompts, truncates context, and streams answers via LLaMA/HF/Mercury.
6. `pipeline.py` – orchestrator that glues everything, tracks timings, and exposes `RAGPipeline.run()` + a CLI.

👉 *In short: This package is the production RAG stack being exercised by the evaluation harness.*

---

## 6. Judge Backends

`JudgeClient` ensures the judge step works in any environment:

1. Try GPT-4o-mini via OpenAI if `OPENAI_API_KEY` is set.
2. Fall back to Meta-Llama-3.1-8B (Hugging Face Inference or local weights).
3. If that fails, fall back again to Qwen-2.5-3B.
4. Always sanitize the response into the same JSON schema.

👉 *In short: The judge always works, even offline.*

---

## End-to-End Summary (One Sentence)

✔ Seed questions → synthetic test sets → RAG pipeline → LLM judge → metrics & summaries. Every stage is modular, production-grade, and replaceable.

Use this document when onboarding teammates or explaining the full evaluation story.
