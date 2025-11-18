# Utils

Shared helpers used across the chat pipeline.

- `logger.py`: Structured logging setup used by CLI, evaluation runner, and registry helpers.
- `email_notifier.py`: Simple SMTP notifier for sending run summaries/alerts.

These modules are dependency-light and safe to import from any stage (RAG pipeline, evaluation, or tracking).
