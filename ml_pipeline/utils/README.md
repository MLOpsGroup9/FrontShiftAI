# 📁 Utils Module

### Purpose
Contains shared utilities such as logging, configuration management, and notifications.

---

### ✅ Existing Scripts
| File | Description |
|------|--------------|
| `email_notifier.py` | Sends email alerts for evaluation or bias failures. |
| `logger.py` | Structured logger for pipeline-level events. |

---

### 🧠 To-Do
- [ ] Add `config_loader.py` for centralized YAML loading (rag.yaml, eval.yaml).
- [ ] Add Slack alert integration for CI/CD failures.
- [ ] Wrap all major pipeline events in `logger.py` calls (run_id, step, latency).