# Evaluation Lab

This folder contains the tools we use to check whether the chat pipeline is trustworthy. The goal is to treat the model like a student taking an exam: we generate questions, collect answers, grade them with a reliable judge, and write detailed report cards. This README explains each step in simple language.

---

## 1. What Happens During an Evaluation Run?

1. **Question preparation** – We load curated questions from `evaluation/test_questions/`. These files are generated from `configs/test_set.yaml` and include slice/domain metadata so we can measure bias.
2. **Answer generation** – For each question we call the RAG pipeline (retrieval → rerank → generation) using the settings defined in the selected experiment config.
3. **Grading** – A judge model (default: OpenAI `gpt-4o-mini`) scores the answer on groundedness, answer relevance, factual correctness, hallucination risk, latency, and more.
4. **Aggregation & bias analysis** – We average the scores across the whole dataset and per slice (e.g., domain, difficulty) to flag any weak areas.
5. **Reporting** – Results are written to `chat_pipeline/results/...` so other components (quality gate, registry, dashboards) can read them.

All of the above is orchestrated by `chat_pipeline/cli.py` using the configuration files in `chat_pipeline/configs/experiments/`.

---

## 2. Key Components in This Folder

| File | Role in the evaluation |
| --- | --- |
| `test_questions/generation.py` | Converts the seed test-set definition into JSONL datasets grouped by slice/domain/difficulty. |
| `evaluation_runner.py` | Main workhorse. Loads questions, calls the RAG pipeline, invokes the judge, tracks metrics, writes examples/summaries/bias reports, and pushes artifacts to W&B when enabled. |
| `eval_judge.py` | Helper functions that talk to the judge model and compute per-example metrics (precision, recall, groundedness, hallucination score, etc.). |
| `judge_client.py` | Manages judge backends (OpenAI, Mercury, or custom). Handles retries and fallback models according to environment variables. |
| `tuning_runner.py` | Runs small what-if experiments (e.g., change `top_k`, enable reranker) and writes a `tuning_report.json` comparing the results. |

---

## 3. Outputs Explained

After running `chat_pipeline.cli`, you will find the following files:

| File | Description |
| --- | --- |
| `results/<label>/examples.jsonl` | Each question, retrieved contexts, generated answer, judge scores, latency, and metadata (slice, company, etc.). Ideal for deep dives. |
| `results/<label>/summary.json` | Averaged metrics for the dataset (precision, recall, groundedness, answer relevance, coherence, hallucination score, latency, etc.). |
| `results/<label>/bias_report.json` | Slice-level averages based on `slice_fields` in the experiment config. Helpful for spotting fairness issues. |
| `results/*experiment_summary*.json` | Top-level summaries referenced by dashboards and CI workflows. |
| `results/quality_gate.txt` | PASS/FAIL flag written by `tracking/compute_quality_gate.py` based on the latest evaluation outputs. |

All logs are plain JSON so they can be versioned, plotted, or shipped to monitoring tools.

---

## 4. How to Run Evaluations

### Smoke Test
```
python -m chat_pipeline.cli --config chat_pipeline/configs/experiments/quick_smoke.yaml
```
Uses tiny datasets with mocked services; ideal for developers.

### Core Evaluation
```
python -m chat_pipeline.cli --config chat_pipeline/configs/experiments/core_eval.yaml
```
Runs the standard 20-question set plus slices.

### Full Evaluation
```
python -m chat_pipeline.cli --config chat_pipeline/configs/experiments/full_eval.yaml
```
Exercises the entire dataset (takes longer but provides full coverage).

### Self-hosted Variants
Use `core_eval_self_hosted.yaml` or `full_eval_self_hosted.yaml` when running on the Mac self-hosted runner to leverage the local llama.cpp backend and Ray parallelism.

The CLI supports `--mode generate`, `--mode judge`, or `--mode full` depending on whether you want to run both stages together or separately (the self-hosted workflows run them separately to save GPU memory).

---

## 5. Connecting to the Quality Gate

After any evaluation run, execute:
```bash
python -m chat_pipeline.tracking.compute_quality_gate
```
The gate checks:
- Main metrics (groundedness, factual correctness, answer relevance, hallucination score, latency).
- Slice metrics (minimum thresholds per slice).
- Smoke-test sanity checks.
- Optional tuning improvements.

It then writes `PASS` or `FAIL` to `chat_pipeline/results/quality_gate.txt`. The deploy workflow refuses to promote a model if the gate failed, giving us a simple but effective safety net.

---

## 6. Tips for Non-Technical Operators

- **Need to inspect a single failure?** Open `examples.jsonl` in a JSONL viewer and search for the question ID. Each record contains the contexts, generated answer, and judge comments.
- **Want to compare two runs?** Place the two `summary.json` files side by side and focus on groundedness and factual correctness first; these correlate strongly with user trust.
- **Bias concerns?** Look at `bias_report.json`. Each key corresponds to a slice (e.g., “construction_ppe”). Low values indicate the model struggles for that scenario.
- **Slow runs?** Decrease `max_examples` in the experiment config or use the smoke test to verify code changes quickly.

With these scripts and reports, anyone on the team can audit the model’s behavior without diving into the underlying Python code. The evaluation folder is intentionally transparent: every number is stored in plain JSON, making it easy to debug, visualize, or share.***
