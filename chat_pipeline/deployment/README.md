# 📁 Deployment Module

### Purpose
Hosts all deployment and containerization scripts for CI/CD and registry pushes.

---

### ✅ Expected Files
| File | Description |
|------|--------------|
| `Dockerfile` | Base image for running RAG pipeline. |
| `requirements.txt` | Lists dependencies for reproducible builds. |

---

### 🧠 To-Do
- [ ] Add rollback script for restoring previous stable model.
- [ ] Add environment variables for model version tagging.
- [ ] Integrate with GitHub Actions workflow (`ci_cd/rag_pipeline.yml`).