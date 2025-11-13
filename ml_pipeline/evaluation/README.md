# 📁 Evaluation Module

### Purpose
Implements the **evaluation and validation stage** of the RAG lifecycle.  
All model metrics, bias reports, and sensitivity analyses live here.

---

### ✅ Existing Scripts
| File | Description |
|------|--------------|
| `rag_eval_metrics.py` | Computes precision, recall, relevance, latency, and F1. |
| `unified_eval_summary.py` | Aggregates metrics from multiple runs; used in CI/CD gates. |
| `sensitivity_analysis.py` | Measures how RAG performance changes with top_k, chunk_size, temperature. |
| `bias_detection.py` | Detects and quantifies bias using data slicing. |
| `eval_results/` | Directory for saving evaluation artifacts (plots, reports, bias summaries). |

---

### 🧠 To-Do
- [ ] Implement `hyperparam_tuner.py` for automated parameter sweeps.
- [ ] Export all visualizations (`confusion_matrix.png`, `latency_plot.png`) into `eval_results/`.
- [ ] Generate `bias_report.json` after every evaluation run.
- [ ] Integrate with `tracking/exp_tracking.py` for MLflow artifact upload.