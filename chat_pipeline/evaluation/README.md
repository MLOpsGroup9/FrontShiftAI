# Evaluation

End-to-end evaluation of the RAG system: generate questions, run the pipeline, judge answers, and aggregate metrics with bias slices.

## Components
- `test_questions/generation.py`: Expands `configs/test_set.yaml` into JSONL datasets. Supports `general`, `domain`, and `slices` with metadata (slice/domain/difficulty).
- `eval_judge.py`: Runs the RAG pipeline for each question, collects contexts, and asks the judge LLM to score groundedness, relevance, hallucination, etc.
- `judge_client.py`: Chooses the judge backend (OpenAI `gpt-4o-mini` by default, fallbacks configured via env).
- `evaluation_runner.py`: Drives the loop, aggregates metrics, writes consolidated examples, summaries, and bias reports.
- `configs/experiments/*.yaml`: Experiment definitions consumed by `chat_pipeline/cli.py` for smoke vs full runs.

## Outputs per run
- `examples.jsonl`: all questions with metadata, contexts, answers, and metrics.
- `summary.json`: averaged metrics (precision, recall, groundedness, relevance, etc.).
- `bias_report.json`: slice-level averages for `groundedness`, `answer_relevance`, `factual_correctness` based on `slice_fields`.
- Top-level experiment summary path configured via `summary_output` in the experiment config (defaults under `chat_pipeline/results/`).

## Running
- Smoke: `python -m chat_pipeline.cli --config chat_pipeline/configs/experiments/quick_smoke.yaml`
- Full: `python -m chat_pipeline.cli --config chat_pipeline/configs/experiments/full_eval.yaml`

Notes: Slice metadata must be present in the datasets for bias reporting. Generation backend obeys `.env` (`GENERATION_BACKEND`) before config overrides.***
