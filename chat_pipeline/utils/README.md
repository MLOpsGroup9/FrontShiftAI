# Utilities Folder

The utilities folder holds small helpers that are shared by every part of the chat pipeline. They are deliberately lightweight, easy to read, and free of heavy dependencies so they can be imported from anywhere. Here is what you will find inside and how to use it.

---

## Files

| File | Description | Typical Usage |
| --- | --- | --- |
| `logger.py` | Central logging setup. Configures formatting, log levels, and optional file handlers so all modules emit consistent messages. | Imported by `chat_pipeline/cli.py`, evaluation runner, registry helpers, etc. Call `setup_logging(level="INFO", to_file=True, log_dir=Path("logs"))` at the start of any script. |
| `email_notifier.py` | Minimal SMTP helper for sending plain-text status emails (e.g., CI notifications). Reads credentials from `EMAIL_SENDER`, `EMAIL_PASSWORD`, and `EMAIL_RECEIVER`. | Used in workflows that need to alert operators after long-running jobs or rollbacks. Can also be invoked manually in incident response scripts. |

---

## Why These Helpers Matter

- **Consistency** – A single logging configuration means every script (retrieval, evaluation, tracking) writes logs in the same format, simplifying debugging and log aggregation.
- **Lightweight notifications** – The email notifier avoids external dependencies; it sends mail using basic Python libraries so it works in both CI and local environments with the same code.
- **Reusability** – Because these helpers sit in a dedicated module with no heavy imports, they can be used by any package (`rag`, `evaluation`, `tracking`, or even Airflow/DVC steps) without causing circular dependencies.

---

## Quick Examples

### Logging
```python
from pathlib import Path
from chat_pipeline.utils.logger import setup_logging

setup_logging(level="INFO", to_file=True, log_dir=Path("logs"))
```
This snippet configures logging once; downstream modules simply call `logging.getLogger(__name__)`.

### Email notification
```python
from chat_pipeline.utils.email_notifier import send_email

send_email(
    subject="Eval finished",
    body="Core evaluation completed successfully.",
    to_override="ops@example.com",  # optional
)
```
Before calling `send_email`, make sure the environment variables for sender, password, and default recipient are set.

---

Keep these helpers simple and trustworthy, and feel free to add more general-purpose utilities here as the project grows.***
