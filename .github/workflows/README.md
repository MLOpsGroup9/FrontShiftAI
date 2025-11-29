# GitHub Workflows Playbook

This document explains every workflow under `.github/workflows/` in plain English so anyone can tell which automation to trigger, what inputs it expects, and where to find the results. Workflows fall into four categories:

1. **Fast safety checks** – make sure code changes don’t break unit tests or the lightweight smoke suite.
2. **Heavy evaluations** – run the core/full chat-pipeline assessments after major changes.
3. **Deployment & recovery** – promote a model into the registry or roll back to a previous safe version.
4. **App-specific helpers** – CI for the backend, frontend, and specialized agents.

All workflows set `PYTHONPATH` to the repo root, disable tokenizer parallelism, and rely on secrets stored in the repository settings (`GCP_SA_KEY`, API keys, email creds, etc.).

---

## 1. Fast Safety Checks

| Workflow | Trigger | What it does | Artifacts / Notes |
| --- | --- | --- | --- |
| `component_test.yml` | Manual (or can be wired to PRs) | Installs chat-pipeline dependencies, runs unit tests, and lints with Black/Flake8 for quick feedback. | No artifacts; fails fast if tests or style checks break. |
| `smoke_test.yaml` | Manual (default) | Syncs the Chroma vector DB from GCS, installs deps, and runs `pytest chat_pipeline/tests -q` using mocked fixtures. Tests generation/routing logic without touching large models. | Uploads nothing; useful for verifying infrastructure/secrets. |

Use these workflows whenever you want confidence before running heavier evals.

---

## 2. Heavy Evaluation Runs

| Workflow | Trigger | Config used | Key steps | Outputs |
| --- | --- | --- | --- | --- |
| `core_eval.yaml` | Manual | `chat_pipeline/configs/experiments/core_eval.yaml` | Auth to GCP, sync vector DB (`gsutil rsync`), set env vars, run `chat_pipeline.cli` (main + slices), verify key files exist, upload `chat_pipeline/results/` and `models/`. | Artifact: `core-eval-results`. Email notification on completion. |
| `full_eval.yaml` | Manual | `chat_pipeline/configs/experiments/full_eval.yaml` | Same as core eval but with the full dataset and longer timeout. | Artifact: `eval-results`. Email notification. |
| `core_eval_self_hosted.yml` | Manual on Mac runner | `core_eval_self_hosted.yaml` (uses Ray + local llama backend) | Installs dependencies on the self-hosted Mac, runs `cli` twice (`--mode generate`, `--mode judge`), performs relaxed verification, uploads results. | Great for validating the local hardware path. |
| `full_eval_self_hosted.yml` | Manual on Mac runner | `core_eval_self_hosted.yaml` (core) + `full_eval_self_hosted.yaml` (full) | Runs both core and full evaluations sequentially on the same runner, again splitting generate vs judge passes. | Artifact: `all-eval-results`. |

These workflows populate `chat_pipeline/results/` and are the source of truth for the quality gate and registry push.

---

## 3. Deployment & Recovery

| Workflow | Trigger | Purpose | Highlights |
| --- | --- | --- | --- |
| `model_deploy.yml` | Manual or callable via `workflow_call` | Validates model artifacts, runs/uses the quality gate, then calls `python -m chat_pipeline.tracking.deploy_model` to push metadata into the registry (local folder or GCS). | Jobs: pre-validation → quality gate → deploy → post-deploy smoke check. Uploads the `models_registry/` artifact for downstream use. |
| `rollback.yml` | Manual | Rolls the registry back to a previous version when a deployment regresses. | Uses the new `chat_pipeline.tracking.rollback_model` helper to list versions, resolve targets, require approval on `main`, execute the rollback, run a verification snippet, and send notifications plus GitHub issues for auditing. |

Both workflows share the same registry helpers, so local dry runs behave exactly like CI.

---

## 4. Application-Specific Pipelines

| Workflow | Description |
| --- | --- |
| `backend.yml`, `frontend.yml` | CI for the backend API and frontend interface (install deps, run component tests, optionally build artifacts). |
| `LLM_backend_config.yml` | Keeps configuration files or secrets for the hosted LLM backend in sync. |
| `hr-ticket-agent.yml`, `pto_agent.yml`, `website-extraction-agent.yml` | Specialized agent workflows for other teams. They follow the same pattern: install deps, run targeted tests/evals, and upload artifacts. |

These workflows are orthogonal to the chat pipeline but live here for convenience.

---

## 5. Secrets & Reusable Patterns

- **GCP access** – Workflows that touch the vector DB call `google-github-actions/auth@v2` with `secrets.GCP_SA_KEY`, followed by `google-github-actions/setup-gcloud@v2`, then `gsutil rsync` to stage the embeddings.
- **Weights & Biases** – Set `WANDB_API_KEY`, `WANDB_ENTITY`, and `WANDB_PROJECT` via secrets to enable experiment logging. Workflows export these into the environment right before calling the CLI.
- **Email notifications** – `core_eval.yaml`, `full_eval.yaml`, and `rollback.yml` send summary emails using `dawidd6/action-send-mail` or the lightweight SMTP helper. Credentials come from `EMAIL_SENDER`, `EMAIL_PASSWORD`, and `EMAIL_RECEIVER`.
- **PYTHONPATH** – Every job runs `echo "PYTHONPATH=$(pwd)" >> $GITHUB_ENV` so modules resolve correctly without installing the package.

If you add a new workflow, copy these patterns to stay consistent with the rest of the automation.***
