# 📁 CI/CD Module

### Purpose
Automates the **training → validation → bias detection → registry push** pipeline using GitHub Actions or Jenkins.

---

### ✅ Expected Files
| File | Description |
|------|--------------|
| `rag_pipeline.yml` | Workflow for model evaluation, bias detection, and deployment. |

---

### 🧠 To-Do
- [ ] Create `.github/workflows/rag_pipeline.yml` or add it here for portability.
- [ ] Integrate `tracking/push_to_registry.py` and `utils/email_notifier.py` in workflow steps.
- [ ] Add rollback trigger if evaluation thresholds fail.