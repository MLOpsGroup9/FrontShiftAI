# Utils

Shared, lightweight helpers used across the pipeline.

- `logger.py`: Structured logging setup used by CLI, evaluation runner, and registry helpers.
- `email_notifier.py`: SMTP notifier for sending run summaries or alerts.

Safe to import from any stage (RAG, evaluation, tracking). No heavy dependencies.***
