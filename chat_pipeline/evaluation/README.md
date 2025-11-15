# 📁 Evaluation Module

This package owns the end-to-end evaluation workflow for the RAG stack: generating synthetic questions, calling the production pipeline, judging the answers, and aggregating metrics.

## Directory Overview

| Path | Purpose |
| ---- | ------- |
| `test_questions/generation.py` | Synthetic data expander that reads `configs/test_set.yaml`, calls the RAG pipeline for each seed question, and writes JSONL datasets per category (`general/`, `domain/`, `slices/`). It enforces a strict “one question per JSON object” contract and logs to `test_questions/logs/`. |
| `eval_judge.py` | LLM-as-a-judge entry point. It runs the RAG pipeline, builds a structured prompt with the retrieved context, and asks GPT-4o-mini (or fallbacks via `JudgeClient`) to score relevance, groundedness, hallucination, and other answer metrics. |
| `judge_client.py` | Backend selector for the judge step. Prefers OpenAI, falls back to Meta-Llama-3.1-8B, then Qwen2.5-3B when credentials/hardware require it. Handles JSON extraction and logging. |
| `evaluation_runner.py` | Main harness that iterates over the generated question sets, invokes `eval_judge`, records per-example metrics, writes JSONL artifacts, and (optionally) logs everything to Weights & Biases. |
| `test_questions/general|domain|slices/` | Output folders where `generation.py` saves the individual question datasets (one JSON object per line). |
| `configs/test_set.yaml` | Source-of-truth seed questions, per-category sampling targets, and the strict judge prompt template. |
| `eval_results/` | Destination for all evaluation outputs (per-example JSON, summary.json, etc.) created by `evaluation_runner.py`. |

### Supporting Scripts

| File | Description |
|------|-------------|
| `rag_eval_metrics.py` | Legacy precision/recall evaluator that operates directly on static question lists. |
| `bias_detection.py` | Applies data slices to detect drift and bias across different cohorts. |
| `sensitivity_analysis.py` | Sweeps hyperparameters such as `top_k`, chunk size, and temperature to see how metrics move. |
| `unified_eval_summary.py` | Aggregates RAG, bias, and sensitivity outputs into one consolidated report for CI/CD gates. |

## Evaluation Flow

1. **Generate questions** – `test_questions/generation.py` ingests seeds from `configs/test_set.yaml`, enforces a JSON-only LLM response (`{"new_question": "...", "new_solution": null}`), dedupes, and writes JSONL files such as `test_questions/general/dataset.jsonl`.
2. **Run evaluations** – `evaluation_runner.py` reads those JSONL datasets, runs the production RAG pipeline for each question, calls `eval_with_llm()` via `judge_client.py`, and captures all metrics/latencies/token usage per query.
3. **Persist artifacts** – Each question’s results are written into `eval_results/` (per-example JSON plus `summary.json`), and optionally sent to W&B.
4. **Review metrics** – Use `unified_eval_summary.py`, `bias_detection.py`, or `sensitivity_analysis.py` to compile additional dashboards or slice-specific reports.
\n*** End Patch



# Evaluation Metrics Description

## 1. Precision
**Definition:**  
The proportion of retrieved documents that are relevant to the query.

**Formula:**  
`Precision = Relevant Retrieved Docs / Total Retrieved Docs`

**Why it matters:**  
High precision ensures the retriever is returning truly useful context.

---

## 2. Recall
**Definition:**  
The proportion of all relevant documents that were successfully retrieved.

**Formula:**  
`Recall = Relevant Retrieved Docs / Total Relevant Docs`

**Why it matters:**  
High recall ensures the system is not missing important information.

---

## 3. Latency (Retriever + Reranker + Generator)
**Definition:**  
End-to-end time taken to process the query and generate the final answer.

**Components:**  
- Retriever latency  
- Reranker latency  
- Generator latency  
- Total pipeline latency  

**Why it matters:**  
Directly impacts user experience and system responsiveness.

---

## 4. Token Usage
**Definition:**  
Total number of input (prompt) and output (completion) tokens consumed per query.

**Why it matters:**  
Token count determines cost and influences latency.

---

## 5. Context Precision (Context Relevance Score)
**Definition:**  
Measures how relevant the retrieved context is to answering the query.

**Why it matters:**  
Irrelevant context increases hallucination risk and degrades answer quality.

---

## 6. Context Recall (Coverage)
**Definition:**  
Measures how much of the necessary information is present in the retrieved context.

**Why it matters:**  
Missing context results in incomplete or incorrect answers.

---

## 7. Groundedness / Faithfulness
**Definition:**  
Measures how well the answer stays grounded in the retrieved context without inventing facts.

**Why it matters:**  
Prevents hallucinations and ensures factual integrity.

---

## 8. Answer Relevance / Correctness
**Definition:**  
Scores how well the generated answer addresses the user query.

**Why it matters:**  
Ensures the model is actually solving the user’s intent.

---

## 9. Answer Conciseness / Verbosity Score
**Definition:**  
Evaluates if the answer is too short, too long, or appropriately concise.

**Why it matters:**  
Improves clarity and reduces noise in responses.

---

## 10. Retrieval Diversity
**Definition:**  
Measures how diverse the retrieved documents are in terms of sources, files, or topics.

**Why it matters:**  
Higher diversity increases context coverage and reduces retrieval bias.

---

## 11. Reranker Gain
**Definition:**  
Difference in retrieval quality before and after reranking.

**Formula:**  
`Reranker Gain = Precision_after - Precision_before`

**Why it matters:**  
Shows whether the reranker is improving retrieval quality.

---

## 12. Coherence
**Definition:**  
Measures the logical flow and readability of the final answer.

**Why it matters:**  
Improves user comprehension and trust.

---

## 13. Factual Correctness
**Definition:**  
Determines whether the answer is accurate based on the provided context or known truth.

**Why it matters:**  
Critical for compliance, safety, and enterprise use cases.

---

## 14. No Hallucination Score
**Definition:**  
Evaluates how much of the answer is unsupported or invented.

**Why it matters:**  
Prevents misleading or dangerous outputs.

---

## 15. Structure Adherence
**Definition:**  
Checks whether the answer follows the requested output format (steps, bullets, sections, etc.).

**Why it matters:**  
Ensures consistent formatting for downstream workflows.

---

## 16. Cost per Query
**Definition:**  
Total cost of processing a single query based on token usage, model pricing, and compute overhead.

**Why it matters:**  
Essential for budgeting and production scaling.

---

## 17. Memory Utilization
**Definition:**  
RAM/VRAM consumed during retrieval, reranking, and generation.

**Why it matters:**  
Prevents resource exhaustion and supports production sizing.

---

## 18. Throughput
**Definition:**  
Number of queries the system can process per second (QPS).

**Why it matters:**  
Determines scalability and real-time system capacity.

---

## Summary Table

| Category        | Metrics |
|-----------------|---------|
| Retrieval       | Precision, Recall, Diversity, Reranker Gain |
| Context         | Context Precision, Context Recall, Groundedness |
| Answer Quality  | Relevance, Conciseness, Coherence, Structure Adherence, Factual Correctness, Hallucination Score |
| Performance     | Latency, Memory Utilization, Throughput, Token Usage, Cost per Query |
