# Tracking & Registry Overview

The tracking folder contains the “operations toolkit” for the chat pipeline. These scripts do two simple but important jobs:

1. **Observe every evaluation run** – so we always know what happened and can share rich dashboards through Weights & Biases (W&B).
2. **Promote or roll back a model safely** – by writing lightweight metadata to `models_registry/` and keeping a reliable `latest` pointer for deployments.

Even if you have never used W&B or managed a model registry before, this guide will walk you through each helper.

---

## Files at a Glance

| File | What it does |
| --- | --- |
| `exp_tracking.py` | Protective wrapper around W&B. It tries to start a run, log metrics/artifacts, and finish cleanly – but quietly does nothing if W&B credentials are missing. Perfect for local development. |
| `push_to_registry.py` | “Promotion” script. Takes a model path plus evaluation artifacts, writes a new version folder under `models_registry/`, computes a checksum of the model file, copies small JSON artifacts, and updates `latest`. Used inside the deploy workflow. |
| `deploy_model.py` | CLI that glues everything together: reads the latest eval summaries, enforces the quality gate status, pulls the current pipeline config, and calls `push_to_registry`. It also understands remote registries hosted on GCS, using `gsutil rsync` behind the scenes. |
| `rollback_model.py` | CLI for incident response. Lists available versions, resolves “previous” vs “target” builds, switches the `latest` pointer, records a rollback log, and syncs the registry back to GCS if needed. |
| `compute_quality_gate.py` | Checks the latest evaluation metrics and writes `PASS` or `FAIL` to `chat_pipeline/results/quality_gate.txt`. The gate looks at groundedness, answer relevance, factual correctness, hallucination score, latency, and slice-level thresholds. |

---

## Typical Workflows

### A. Promote a model after a successful evaluation

1. Run the evaluation (`chat_pipeline.cli ...`).
2. Run the quality gate:
   ```bash
   python -m chat_pipeline.tracking.compute_quality_gate
   ```
   This writes `quality_gate.txt` pointing to PASS or FAIL.
3. Deploy to the registry:
   ```bash
   python -m chat_pipeline.tracking.deploy_model \
     --model-name frontshift-rag \
     --model-path models/Llama-3.2-3B-Instruct-Q4_K_S.gguf
   ```
   The script:
   - Pulls the current registry (if it lives on GCS).
   - Verifies the gate status (unless you explicitly allow failures).
   - Copies `summary.json` and `bias_report.json` into the new version folder.
   - Stores the pipeline configuration alongside the metadata so we can always rebuild the exact settings.
   - Pushes the updated registry back to GCS when done.

### B. Roll back in case of regression

1. List available versions:
   ```bash
   python -m chat_pipeline.tracking.rollback_model --list-versions
   ```
2. Pick a version or choose `--previous`, then execute:
   ```bash
   python -m chat_pipeline.tracking.rollback_model \
     --target-version v7 \
     --reason "Spike in hallucinations"
   ```
3. Check the log under `models_registry/rollback_logs/` for an audit trail. The GitHub workflow automatically uploads this folder as an artifact.

### C. Log experiments to Weights & Biases

`exp_tracking.py` is used inside the evaluation runner. You do not have to call it manually; simply set the following environment variables and the logs will appear:
```
WANDB_API_KEY=...
WANDB_PROJECT=FrontShiftAI
WANDB_ENTITY=group9mlops-northeastern-university
```
If these variables are missing, the tracker prints a short warning and keeps going without crashing your job.

---

## Understanding the Registry Layout

When you run `deploy_model.py`, the registry ends up with directories like:
```
models_registry/
├── frontshift-rag_v1/
│   ├── metadata.json
│   ├── summary.json
│   ├── bias_report.json
│   └── pipeline_config.json
├── frontshift-rag_v2/
│   └── ...
├── latest -> frontshift-rag_v2
└── rollback_logs/
    └── rollback_20240701_093030.json
```

- `metadata.json` stores the model path, SHA256 checksum, evaluation metrics, timestamp, and references to the copied artifacts.
- The `latest` symlink (or text file on systems without symlinks) points to the currently active version.
- `rollback_logs/` contains timestamped JSON logs describing why and when a rollback happened, plus who triggered it (GitHub actor if available).

This lightweight structure intentionally avoids copying large weight files. Only metadata and small JSON summaries are stored, making it easy to sync the entire registry to a cloud bucket.

---

## Safety Checks Built Into the Helpers

- **Quality gate guardrail** – `deploy_model.py` refuses to push a model if the gate status is FAIL unless `--allow-gate-fail` is set. This prevents accidental promotions when metrics regress.
- **Remote registry syncs** – Both deploy and rollback commands pull the latest state from the remote bucket before making changes, then push the new state back. This avoids lost updates when two workflows run close to each other.
- **Hashing** – `push_to_registry.py` computes a SHA256 hash of the model file so we can always verify the weights on disk match the registered metadata.
- **Audit logs** – Rollbacks create dedicated log files, and the GitHub workflow adds a ticket plus email notification so no action goes unnoticed.

---

## When to Use These Tools

- Use **`compute_quality_gate.py`** whenever you finish an evaluation; it is the single source of truth for PASS/FAIL.
- Trigger **`deploy_model.py`** from CI (the `model_deploy.yml` workflow does this) or manually after you verify the gate.
- Keep **`rollback_model.py`** handy when a new deployment causes issues and you need to restore the previous stable version quickly.
- The GitHub Actions `model_deploy` and `rollback` workflows call the same scripts, so local dry runs behave exactly like the automated pipelines.

With these helpers in place, you always know which model version is active, which metrics justified it, and how to revert if needed – all without touching the heavy model binaries.***
