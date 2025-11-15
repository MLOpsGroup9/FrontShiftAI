# 📁 Tracking Module

### Purpose
Logs all experiments, metrics, and model registry events.

---

### ✅ Existing Scripts
| File | Description |
|------|--------------|
| `exp_tracking.py` | MLflow integration for logging parameters, metrics, and artifacts. |
| `push_to_registry.py` | Handles pushing validated models to GCP Artifact Registry. |

---

### 🧠 To-Do
- [ ] Add artifact upload (plots and config files) to MLflow.
- [ ] Log hyperparameter search results.
- [ ] Add helper for fetching best-performing runs.
- [ ] Connect MLflow run status to Slack/email via `utils/email_notifier.py`.