# GitHub Workflows Overview

This repository uses separate workflows for fast checks, full evaluations, and deployment helpers.

- `smoke_test.yaml`: Runs on push/PR to main. Installs dependencies, syncs the Chroma vector DB from GCS, and runs the test suite against mocked/tiny fixtures.

- `full_eval.yaml`: Manual trigger. Syncs the vector DB from GCS, then runs the full evaluation via `chat_pipeline.cli` using the `full_eval.yaml` experiment config. Uploads eval artifacts and prints key metrics.

- `self_hosted.yaml`: Manual trigger for macOS self-hosted runners. Syncs the vector DB from GCS and runs the full evaluation locally on the self-hosted machine.

- `model_deploy.yml`: Standalone deployment workflow (manual or callable). Validates a model file, then pushes it using the legacy deploy script. Artifacts can be uploaded as part of the run.

- `component_test.yml` / `rollback.yml`: Auxiliary workflows for component-level tests or rollback procedures as needed by the project.

Each workflow sets `PYTHONPATH` to the repo root and disables tokenizer parallelism. GCS access requires a service account JSON stored in `GCP_SA_KEY` and uses `google-github-actions/auth` plus `gsutil rsync` to stage the vector DB locally.***
