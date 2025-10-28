import pandas as pd
from pathlib import Path
from data_pipeline.scripts import data_bias

def test_bias_analysis_generates_reports(tmp_path):
    df = pd.DataFrame([
        {"industry": "Finance", "org": "A", "doc_type": "handbook",
         "company": "X", "policy_tags": "FMLA|PTO",
         "keywords": "policy|benefit", "created_at": "2024-01-01",
         "token_count": 100, "text": "Good policy improves safety."}
    ])
    out_dir = tmp_path / "bias_run"
    out_dir.mkdir()

    data_bias.compute_representation_bias(df, out_dir)
    data_bias.compute_sentiment_bias(df, out_dir)
    data_bias.compute_coverage_bias(df, out_dir)

    # --- Assertions ---
    assert (out_dir / "representation_metrics.json").exists()
    assert (out_dir / "policy_tag_counts.csv").exists()
    assert (out_dir / "sentiment_by_doc.csv").exists()
