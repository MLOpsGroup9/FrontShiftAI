# 📁 Configs Module

### Purpose
Stores all configuration files controlling pipeline parameters and thresholds.

---

### ✅ Expected Files
| File | Description |
|------|--------------|
| `rag.yaml` | Retriever/generator parameters — chunk size, top_k, temperature. |
| `eval.yaml` | Validation thresholds (precision, recall, relevance, latency). |
| `slices.yaml` | Slicing definitions for bias detection (topic, language, accent). |

---

### 🧠 To-Do
- [ ] Add default templates for each YAML config.
- [ ] Validate configurations at runtime using a loader in `utils/config_loader.py`.