# Configuration Directory

Every knob that affects the chat pipeline lives in this folder. Instead of hard-coding settings throughout the codebase we keep them here so non-developers can reason about how the system behaves. This document explains each file and how the overrides stack on top of each other.

---

## 1. Core Files

| File | Purpose | What to edit |
| --- | --- | --- |
| `rag.yaml` | Default settings for the RAG pipeline (retriever type, reranker options, prompt template, streaming parameters, vector-store paths). | Update when you need a new backend, change `top_k`, or point to a different Chroma directory. |
| `test_set.yaml` | Seed questions for the automatic test-question generator. Each entry includes company, slice, domain, and difficulty metadata so evaluations can create balanced datasets. | Add or adjust slices/domains to improve coverage. |

---

## 2. Experiment Configs (`experiments/*.yaml`)

These files orchestrate end-to-end evaluation runs via `chat_pipeline/cli.py`. They share a common structure:

```yaml
logging:
  level: INFO
  to_file: true
  log_dir: logs

wandb:
  project: FrontShiftAI_Latest
  entity: group9mlops-northeastern-university
  disable: false

execution_modes:
  local:
    parallelism: ray
  ci:
    parallelism: sequential

eval:
  summary_output: chat_pipeline/results/...
  slice_fields: [slice]
  pipeline_overrides:
    generation:
      backend: mercury
  main:
    test_dir: chat_pipeline/evaluation/test_questions
    output_dir: chat_pipeline/results/core_eval_main
    max_examples: 20
  slices:
    enabled: true
    test_dir: chat_pipeline/evaluation/test_questions/slices
    output_dir: chat_pipeline/results/core_eval_slices

tuning:
  enabled: true
  ...
```

### Available experiment files
- `quick_smoke.yaml` – Tiny dataset for CI with mocked services.
- `core_eval.yaml` – Core question set, Mercury backend by default.
- `core_eval_self_hosted.yaml` – Same dataset but tuned for the Mac runner (local llama backend, Ray parallelism).
- `full_eval.yaml` – Large evaluation for release readiness.
- `full_eval_self_hosted.yaml` – Full evaluation tailored to the self-hosted runner.

Each file decides:
- How many examples to run (`max_examples`).
- Where to save outputs (`output_dir`, `summary_output`).
- Which slices to compute bias metrics over (`slice_fields`).
- Whether to run optional tuning sweeps (`tuning.enabled`).

---

## 3. Override Precedence

When the pipeline loads configuration it merges settings in the following order (earliest wins only if later layers do not override the same field):

1. **Environment variables** – e.g., `GENERATION_BACKEND`, `LLAMA_MODEL_PATH`, `CHROMA_DIR`. GitHub workflows set these explicitly for CI/self-hosted runs.
2. **Experiment `pipeline_overrides`** – Each evaluation config can override a subset of the RAG settings (useful for forcing a local backend or different top‑k).
3. **Base defaults (`rag.yaml`)** – Provides safe fallbacks so local development “just works”.

Whenever you change a value, double-check which layer you are editing so you know whether the change applies globally or just to one evaluation.

---

## 4. Where Outputs Go

Experiment configs define output folders so you always know where to look:

| Setting | Meaning |
| --- | --- |
| `eval.main.output_dir` | Stores `examples.jsonl`, `summary.json`, bias report, and metadata for the main dataset. |
| `eval.slices.output_dir` | Same for the slice dataset (if enabled). |
| `eval.summary_output` | A single “experiment summary” JSON file that the dashboards and workflows use. |
| `tuning.output_dir` | Location of `tuning_report.json` when tuning is enabled. |

The deploy/rollback scripts copy the relevant `summary.json` and `bias_report.json` files into the registry, so keeping these paths consistent is important.

---

## 5. Making Safe Changes

1. **Clone an existing config** – e.g., copy `core_eval_self_hosted.yaml` to a new file instead of editing the original. This keeps workflows stable.
2. **Adjust the overrides** – change `pipeline_overrides`, `max_examples`, or slice fields as needed.
3. **Run the CLI locally** – `python -m chat_pipeline.cli --config <your-config>.yaml --mode full`.
4. **Inspect outputs** – confirm new files appear in `chat_pipeline/results/` and that the quality gate passes.
5. **Update workflows** – point the relevant GitHub Action (if any) to the new config file.

With this pattern, configuration changes stay traceable and safe – exactly what we need for a production-grade evaluation and deployment flow.***
