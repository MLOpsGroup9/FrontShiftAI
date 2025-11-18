# Evaluation

End-to-end evaluation harness for the RAG pipeline: dataset generation, LLM-as-a-judge scoring, and report aggregation.

## What lives here
- `test_questions/`: Seed datasets and the generator (`generation.py`) that expands `configs/test_set.yaml` into JSONL question sets (`general/`, `domain/`, `slices/`).
- `eval_judge.py`: Runs the production RAG pipeline for a question, captures contexts, and asks the judge LLM to score groundedness, relevance, hallucination, and other metrics.
- `judge_client.py`: Backend selector for the judge (prefers OpenAI `gpt-4o-mini`, falls back to other configured models).
- `evaluation_runner.py`: Orchestrates the evaluation loop, persists per-example artifacts, and writes summaries and bias reports.
- `configs/experiments/*.yaml`: Experiment definitions consumed by `chat_pipeline/cli.py` (smoke vs full eval, overrides, output locations).

## Outputs
- Per-example JSON: `results/<run_label>/example_XXXX.json` (question, metadata, contexts, model answer, metrics).
- Aggregates: `summary.json` (averaged metrics) and `bias_report.json` (slice-level averages for `groundedness`, `answer_relevance`, `factual_correctness`) inside each run folder.
- Top-level experiment summary: configurable via `summary_output` in the experiment config (defaults under `chat_pipeline/results/`).

## How to run
- Smoke test: `python -m chat_pipeline.cli --config chat_pipeline/configs/experiments/quick_smoke.yaml`
- Full test set: `python -m chat_pipeline.cli --config chat_pipeline/configs/experiments/full_eval.yaml`

## Notes
- Judge metrics come from the LLM in `judge_client.py`; no separate bias classifier exists—the bias report is computed by slicing those metrics by fields in `slice_fields` (e.g., `category`, `company_name`).
- Generation backend for the RAG call honors `.env` (`GENERATION_BACKEND`) before any config overrides.
