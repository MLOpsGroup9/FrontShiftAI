# Tracking

Experiment tracking and registry helpers.

- `exp_tracking.py`: Defensive W&B wrappers for starting runs, logging metrics/artifacts, and finishing cleanly. They no-op when W&B is disabled or unavailable.
- `push_to_registry.py`: Metadata-only model registry writer. Creates versioned folders under `models_registry/`, copies only small artifacts (eval summary, bias report, pipeline config), computes a SHA256 for the referenced model file, writes `metadata.json`, and updates a `latest` pointer. It never copies model weights.

These helpers are optional; enable W&B and registry usage in environments that support them.***
