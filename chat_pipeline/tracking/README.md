# Tracking

Lightweight experiment tracking and model registry helpers.

- `exp_tracking.py`: Defensive W&B wrappers (`start_run`, `log_metrics`, `log_artifacts`, `finish_run`, `log_stage`) that no-op when W&B is unavailable or disabled.
- `push_to_registry.py`: Copies a model artifact from `models/` into a versioned folder under `models_registry/` and saves accompanying metadata.

Both modules are optional helpers; they are safe to skip in environments without W&B or where a registry is not configured.
