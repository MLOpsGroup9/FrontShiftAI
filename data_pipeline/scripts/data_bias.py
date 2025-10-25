#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Run bias diagnostics over the chunked dataset produced by the pipeline.
Loads JSONL files from data/chunked/ and writes reports to data/bias_analysis/.
"""

import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from collections import Counter

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer

# ---------------------------------------------------------------------------
# Paths and logging (align with other pipeline scripts)
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
CHUNKED_DIR = DATA_DIR / "chunked"
BIAS_ANALYSIS_ROOT = DATA_DIR / "bias_analysis"
LOGS_DIR = BASE_DIR / "logs" / "bias_analysis"

BIAS_ANALYSIS_ROOT.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "bias_analysis.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

DEFAULT_MAX_FEATURES = 5000
DEFAULT_PCA_MAX_DOCS = 2000

# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def safe_slug(name: str) -> str:
    cleaned = re.sub(r"[^\w\-]+", "_", (name or "").strip())
    return cleaned[:80] or "unknown"


def gini(array: List[float]) -> float:
    if not array:
        return 0.0
    arr = np.array(array, dtype=float)
    if np.amin(arr) < 0:
        arr -= np.amin(arr)
    arr += 1e-9  # avoid divide by zero
    arr = np.sort(arr)
    n = arr.size
    cumulative = np.cumsum(arr)
    return float((n + 1 - 2 * np.sum(cumulative) / cumulative[-1]) / n)


def entropy(proportions: List[float]) -> float:
    arr = np.array(proportions, dtype=float)
    arr = arr[arr > 0]
    return float(-np.sum(arr * np.log2(arr))) if arr.size else 0.0


def kl_divergence(p: np.ndarray, q: np.ndarray) -> float:
    eps = 1e-12
    p = p + eps
    q = q + eps
    return float(np.sum(p * np.log(p / q)))


def ratio_imbalance(counts: List[int]) -> float:
    arr = np.array(counts, dtype=float)
    if len(arr) == 0 or np.sum(arr) == 0:
        return 0.0
    return float(np.max(arr) / (np.min(arr) + 1e-9))


POS_WORDS = {
    "good",
    "great",
    "excellent",
    "positive",
    "benefit",
    "improve",
    "success",
    "safe",
    "safety",
    "compliant",
    "compliance",
    "growth",
    "increase",
    "gain",
    "profit",
    "happy",
    "satisfied",
    "support",
    "best",
    "well",
}
NEG_WORDS = {
    "bad",
    "poor",
    "negative",
    "risk",
    "issue",
    "problem",
    "fail",
    "unsafe",
    "violate",
    "violation",
    "loss",
    "decline",
    "decrease",
    "down",
    "complaint",
    "fraud",
    "error",
    "wrong",
    "breach",
    "penalty",
}


def sentiment_score(text: str) -> float:
    if not text:
        return 0.0
    words = [w.strip(".,;:!?()[]{}\"'").lower() for w in text.split()]
    pos = sum(1 for w in words if w in POS_WORDS)
    neg = sum(1 for w in words if w in NEG_WORDS)
    total = len(words) or 1
    return (pos - neg) / total


def distribution_metrics(series: pd.Series) -> Tuple[Dict[str, Any], pd.Series, pd.Series]:
    counts = series.value_counts(dropna=False)
    props = counts / counts.sum() if counts.sum() else counts
    metrics = {
        "unique": int(counts.shape[0]),
        "gini": gini(counts.values.tolist()),
        "entropy": entropy(props.values.tolist()),
        "ratio_imbalance": ratio_imbalance(counts.values.tolist()),
        "top_5": counts.head(5).to_dict(),
    }
    return metrics, counts, props


def split_pipe(col: pd.Series) -> List[str]:
    out: List[str] = []
    for value in col.dropna().astype(str):
        parts = [p.strip() for p in value.split("|") if p.strip()]
        out.extend(parts)
    return out


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def infer_industry_from_filename(path: Path) -> str:
    base = path.name
    stem = base.replace("_chunks.jsonl", "").replace(".jsonl", "")
    parts = stem.split("_")
    if not parts:
        return "Unknown"
    if len(parts) >= 2:
        two = f"{parts[0]}_{parts[1]}"
        if any(
            key in two.lower()
            for key in [
                "cleaning_maintenance",
                "health",
                "finance",
                "logistics",
                "manufacturing",
                "retail",
                "hospitality",
                "fieldservicetechnicians",
            ]
        ):
            return two
    return parts[0]


def normalize_industry(name: str) -> str:
    label = (name or "").lower()
    if "finance" in label:
        return "Finance"
    if "health" in label or "healthcare" in label:
        return "Healthcare"
    if "logistics" in label:
        return "Logistics"
    if "manufacturing" in label:
        return "Manufacturing"
    if "retail" in label:
        return "Retail"
    if "hospitality" in label:
        return "Hospitality"
    if "cleaning_maintenance" in label or "cleaning" in label or "maintenance" in label:
        return "Cleaning_Maintenance"
    if "fieldservicetechnicians" in label or "field_service" in label or "fieldservice" in label:
        return "FieldServiceTechnicians"
    head = name.split("_")[0] if name else "Unknown"
    return head.capitalize()


def collect_chunk_files(chunked_dir: Path) -> List[Path]:
    if not chunked_dir.exists():
        return []
    files = sorted(chunked_dir.glob("*.jsonl"))
    if not files:
        files = sorted(chunked_dir.rglob("*.jsonl"))
    return [file for file in files if file.is_file()]


def build_dataframe(chunked_dir: Path) -> pd.DataFrame:
    files = collect_chunk_files(chunked_dir)
    if not files:
        raise RuntimeError(f"No chunked JSONL files found in {chunked_dir}")

    records: List[Dict[str, Any]] = []
    for file_path in files:
        inferred = infer_industry_from_filename(file_path)
        with file_path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                try:
                    record = json.loads(raw_line)
                except json.JSONDecodeError:
                    logger.warning("Skipping invalid JSON line in %s", file_path)
                    continue
                metadata = record.get("metadata", {}) or {}
                meta_industry = (metadata.get("industry") or "").strip()
                if meta_industry and meta_industry.lower() not in {"hr/employee", "unknown", ""}:
                    industry = meta_industry
                else:
                    industry = inferred
                industry = normalize_industry(industry)
                records.append(
                    {
                        "industry": industry,
                        "org": metadata.get("org") or "",
                        "doc_type": metadata.get("doc_type") or "",
                        "company": metadata.get("company") or "",
                        "policy_tags": "|".join(metadata.get("policy_tags") or []),
                        "keywords": "|".join(metadata.get("keywords") or []),
                        "created_at": metadata.get("created_at") or "",
                        "token_count": metadata.get("token_count") or 0,
                        "text": record.get("text") or "",
                    }
                )
    if not records:
        raise RuntimeError("Chunked files were found but produced no records.")
    logger.info("Loaded %s records from %s files.", len(records), len(files))
    return pd.DataFrame.from_records(records)


# ---------------------------------------------------------------------------
# Bias metrics
# ---------------------------------------------------------------------------

def compute_representation_bias(df: pd.DataFrame, out_dir: Path) -> Dict[str, Any]:
    dims = ["industry", "org", "doc_type", "company", "policy_tags"]
    rep_metrics: Dict[str, Any] = {}
    rep_counts: Dict[str, pd.Series] = {}
    rep_props: Dict[str, pd.Series] = {}

    for dim in dims:
        metrics, counts, props = distribution_metrics(df[dim].fillna(""))
        rep_metrics[dim], rep_counts[dim], rep_props[dim] = metrics, counts, props

    (out_dir / "representation_metrics.json").write_text(json.dumps(rep_metrics, indent=2), encoding="utf-8")

    for dim in ["industry", "org"]:
        series = rep_counts[dim].head(15)
        if series.empty:
            continue
        plt.figure()
        series.plot(kind="bar")
        plt.title(f"Distribution by {dim} (Top 15)")
        plt.ylabel("Count")
        plt.tight_layout()
        plt.savefig(out_dir / f"dist_{dim}.png")
        plt.close()

    return {"metrics": rep_metrics, "counts": rep_counts, "props": rep_props}


def compute_sentiment_bias(df: pd.DataFrame, out_dir: Path) -> pd.Series:
    if df.empty:
        logger.warning("No data available for sentiment analysis.")
        return pd.Series(dtype=float)

    df_local = df.copy()
    df_local["sentiment"] = df_local["text"].apply(sentiment_score)
    sent_by_industry = df_local.groupby("industry")["sentiment"].mean().sort_values(ascending=False)
    if not sent_by_industry.empty:
        plt.figure()
        sent_by_industry.plot(kind="bar")
        plt.title("Average Sentiment by Industry")
        plt.ylabel("Mean sentiment")
        plt.tight_layout()
        plt.savefig(out_dir / "sentiment_by_industry.png")
        plt.close()
    df_local[["industry", "sentiment"]].to_csv(out_dir / "sentiment_by_doc.csv", index=False)
    return sent_by_industry


def compute_topic_bias(
    df: pd.DataFrame,
    out_dir: Path,
    max_features: int = DEFAULT_MAX_FEATURES,
    pca_max_docs: int = DEFAULT_PCA_MAX_DOCS,
) -> None:
    df_local = df.copy()
    df_local["__text"] = df_local["text"].fillna("").astype(str).str.strip()
    df_local = df_local[df_local["__text"] != ""]

    if df_local.empty:
        logger.warning("Skipping topic bias: no non-empty text available.")
        return

    vectorizer = TfidfVectorizer(max_features=max_features, stop_words="english")
    matrix = vectorizer.fit_transform(df_local["__text"].tolist())
    terms = np.array(vectorizer.get_feature_names_out())

    top_terms: Dict[str, List[str]] = {}
    industries = df_local["industry"].tolist()
    for industry in sorted(set(industries)):
        mask = np.array([ind == industry for ind in industries])
        if not mask.any():
            continue
        column_means = np.asarray(matrix[mask].mean(axis=0)).ravel()
        if not column_means.size:
            continue
        indices = np.argsort(column_means)[::-1][:15]
        top_terms[industry] = terms[indices].tolist()

    (out_dir / "top_terms_by_industry.json").write_text(json.dumps(top_terms, indent=2), encoding="utf-8")

    sample_count = min(matrix.shape[0], pca_max_docs)
    if sample_count >= 2:
        matrix_sample = matrix[:sample_count]
        svd = TruncatedSVD(n_components=2, random_state=0)
        coords = svd.fit_transform(matrix_sample)
        plt.figure()
        plt.scatter(coords[:, 0], coords[:, 1], s=6)
        plt.title("TruncatedSVD of TF-IDF (first 2 components)")
        plt.tight_layout()
        plt.savefig(out_dir / "pca_topics.png")
        plt.close()
    else:
        logger.info("Not enough documents for topic projection (need at least 2, have %s).", sample_count)


def compute_coverage_bias(df: pd.DataFrame, out_dir: Path) -> None:
    policy_tags = split_pipe(df["policy_tags"])
    keyword_tags = split_pipe(df["keywords"])

    if policy_tags:
        policy_counts = Counter(policy_tags)
        pd.Series(policy_counts).sort_values(ascending=False).to_csv(out_dir / "policy_tag_counts.csv")
        plt.figure()
        pd.Series(policy_counts).sort_values(ascending=False).head(20).plot(kind="bar")
        plt.title("Top Policy Tags (Top 20)")
        plt.ylabel("Count")
        plt.tight_layout()
        plt.savefig(out_dir / "policy_tags_top20.png")
        plt.close()
    else:
        logger.info("No policy tags present in the dataset.")

    if keyword_tags:
        keyword_counts = Counter(keyword_tags)
        pd.Series(keyword_counts).sort_values(ascending=False).head(100).to_csv(out_dir / "keyword_top100.csv")
    else:
        logger.info("No keywords present in the dataset.")


def write_report(out_dir: Path, rep: Dict[str, Any], subset_note: str = "") -> None:
    rep_metrics = rep["metrics"]
    rep_props = rep["props"]
    lines: List[str] = []

    header = "# Advanced Bias Detection Report"
    if subset_note:
        header += f" — {subset_note}"
    lines.append(header + "\n")
    lines.append("## Representation Metrics\n")
    for dimension, metrics in rep_metrics.items():
        lines.append(
            f"**{dimension}** — unique={metrics['unique']}, "
            f"gini={metrics['gini']:.3f}, entropy={metrics['entropy']:.3f}, "
            f"ratio_imbalance={metrics['ratio_imbalance']:.2f}"
        )
        top_5 = ", ".join([f"{k}:{v}" for k, v in metrics["top_5"].items()])
        lines.append(f"Top-5: {top_5}\n")

    lines.append("## Divergence from Uniform (KL)\n")
    for dimension in ["industry", "org", "doc_type", "company"]:
        props = rep_props[dimension].values.astype(float)
        if props.sum() == 0:
            continue
        props = props / props.sum()
        uniform = np.ones_like(props) / len(props)
        divergence = kl_divergence(props, uniform)
        lines.append(f"- {dimension}: KL={divergence:.3f}")

    lines.append("\n## Sentiment Bias\n- See `sentiment_by_industry.png` and `sentiment_by_doc.csv`.\n")
    lines.append("## Topic Bias\n- `top_terms_by_industry.json` and `pca_topics.png`.\n")
    lines.append("## Coverage Bias\n- `policy_tag_counts.csv`, `keyword_top100.csv`, and `policy_tags_top20.png`.\n")

    (out_dir / "bias_report.md").write_text("\n".join(lines), encoding="utf-8")


def generate_executive_summary(out_dir: Path, rep_metrics: Dict[str, Any], title_note: str = "") -> None:
    lines: List[str] = []
    title = "# Executive Summary: Data Bias Insights"
    if title_note:
        title += f" — {title_note}"
    lines.append(title + "\n")
    lines.append("### 1. Key Representation Findings\n")
    for dimension, metrics in rep_metrics.items():
        g_value = metrics["gini"]
        entropy_value = metrics["entropy"]
        ratio_value = metrics["ratio_imbalance"]
        top_entries = list(metrics["top_5"].items())[:3]
        top_str = ", ".join([f"{k} ({v})" for k, v in top_entries])
        if g_value > 0.6:
            level = "High imbalance"
        elif g_value > 0.4:
            level = "Moderate imbalance"
        else:
            level = "Low imbalance"
        lines.append(
            f"- **{dimension.capitalize()}** → {level} (Gini={g_value:.2f}, Entropy={entropy_value:.2f}, Ratio={ratio_value:.1f})"
        )
        lines.append(f"  - Top categories: {top_str}\n")

    lines.append("### 2. Overall Bias Interpretation\n- Uneven representation across categories may require rebalancing.\n")
    lines.append("### 3. Sentiment & Topic Overview\n- Inspect sentiment and topic plots to understand tonal or topical skew.\n")
    lines.append(
        "### 4. Recommended Actions\n"
        "1) Collect samples for underrepresented categories.\n"
        "2) Diversify document types where imbalance is high.\n"
        "3) Expand metadata coverage (policy tags, keywords).\n"
        "4) Verify tone bias with complementary NLP tooling.\n"
    )
    lines.append("### 5. Confidence Summary\n- Representation: High\n- Topic: Moderate\n- Sentiment: Low–Moderate\n")

    (out_dir / "executive_summary.md").write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_full_analysis(
    df: pd.DataFrame,
    out_dir: Path,
    subset_note: str,
    max_features: int,
    pca_max_docs: int,
) -> Dict[str, Any]:
    ensure_dir(out_dir)
    df.to_csv(out_dir / "all_records_preview.csv", index=False)
    rep = compute_representation_bias(df, out_dir)
    compute_sentiment_bias(df, out_dir)
    compute_topic_bias(df, out_dir, max_features=max_features, pca_max_docs=pca_max_docs)
    compute_coverage_bias(df, out_dir)
    write_report(out_dir, rep, subset_note=subset_note)
    generate_executive_summary(out_dir, rep["metrics"], title_note=subset_note)

    org_metrics = rep["metrics"].get("org", {"gini": np.nan, "entropy": np.nan, "ratio_imbalance": np.nan})
    sentiments = df["text"].apply(sentiment_score)
    return {
        "docs": int(len(df)),
        "org_gini": float(org_metrics.get("gini", np.nan)),
        "org_entropy": float(org_metrics.get("entropy", np.nan)),
        "org_ratio": float(org_metrics.get("ratio_imbalance", np.nan)),
        "avg_sentiment": float(sentiments.mean() if len(sentiments) > 0 else 0.0),
    }


def create_run_directory(root: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = root / f"run_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def run_bias_analysis(
    chunked_dir: Path = CHUNKED_DIR,
    output_root: Path = BIAS_ANALYSIS_ROOT,
    max_features: int = DEFAULT_MAX_FEATURES,
    pca_max_docs: int = DEFAULT_PCA_MAX_DOCS,
) -> Optional[Path]:
    logger.info("Starting bias analysis. Chunk source: %s", chunked_dir)

    try:
        df_all = build_dataframe(chunked_dir)
    except RuntimeError as exc:
        logger.error("Bias analysis aborted: %s", exc)
        return None

    if df_all.empty:
        logger.error("Bias analysis aborted: dataframe is empty.")
        return None

    run_dir = create_run_directory(output_root)
    logger.info("Writing bias analysis artifacts to %s", run_dir)

    run_full_analysis(
        df_all,
        run_dir,
        subset_note="All data",
        max_features=max_features,
        pca_max_docs=pca_max_docs,
    )

    logger.info("Bias analysis complete. Artifacts available at %s", run_dir)
    return run_dir


if __name__ == "__main__":
    run_bias_analysis()
