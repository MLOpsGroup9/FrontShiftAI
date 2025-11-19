"""Lightweight hyperparameter sweep and sensitivity report for the RAG pipeline.

This script runs the RAG evaluation over a small grid of retrieval/reranker
settings for both the main eval set and the slices set (if provided), and
collects aggregate metrics plus bias reports for each run.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from chat_pipeline.evaluation.evaluation_runner import EvaluationConfig, EvaluationRunner


def _default_grid() -> List[Dict[str, Any]]:
    # Keep the grid intentionally small to avoid long runtimes.
    return [
        {"name": "baseline", "overrides": {}},
        {"name": "topk3", "overrides": {"retriever": {"top_k": 3}}},
        {"name": "topk7", "overrides": {"retriever": {"top_k": 7}}},
        {"name": "rerank_on", "overrides": {"reranker": {"enabled": True, "rerank_k": 3}}},
    ]


def _run_eval(
    test_dir: Path,
    output_dir: Path,
    label: str,
    grid: List[Dict[str, Any]],
    max_examples: Optional[int],
    slice_fields: List[str],
    wandb_project: Optional[str],
    wandb_entity: Optional[str],
    disable_wandb: bool,
) -> List[Dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    runs: List[Dict[str, Any]] = []

    for item in grid:
        run_name = item.get("name") or "run"
        overrides = item.get("overrides") or {}
        dest = output_dir / f"{label}_{run_name}"
        cfg = EvaluationConfig(
            test_questions_dir=test_dir,
            output_dir=dest,
            max_examples=max_examples,
            wandb_project=wandb_project,
            wandb_entity=wandb_entity,
            disable_wandb=disable_wandb,
            dataset_label=label,
            slice_fields=slice_fields,
        )
        runner = EvaluationRunner(cfg, config_overrides=overrides)
        runner.run()

        summary_path = dest / "summary.json"
        bias_path = dest / "bias_report.json"
        summary_data = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
        bias_data = json.loads(bias_path.read_text(encoding="utf-8")) if bias_path.exists() else {}

        runs.append(
            {
                "run": run_name,
                "dataset": label,
                "overrides": overrides,
                "summary": summary_data,
                "bias_report": bias_data,
                "output_dir": str(dest),
            }
        )
    return runs


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Small hyperparameter sweep for RAG pipeline.")
    parser.add_argument(
        "--test-dir",
        type=Path,
        default=Path("chat_pipeline/evaluation/test_questions"),
        help="Main evaluation dataset directory.",
    )
    parser.add_argument(
        "--slices-dir",
        type=Path,
        default=Path("chat_pipeline/evaluation/test_questions/slices"),
        help="Optional slices dataset directory for bias checks.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("chat_pipeline/evaluation/tuning_results"),
        help="Root output directory for tuning artifacts.",
    )
    parser.add_argument("--max-examples", type=int, help="Limit number of examples per dataset.")
    parser.add_argument(
        "--slice-fields",
        default="category,company_name",
        help="Comma-separated metadata fields to slice bias metrics on.",
    )
    parser.add_argument("--wandb-project", help="Weights & Biases project name.")
    parser.add_argument("--wandb-entity", help="Weights & Biases entity/team.")
    parser.add_argument("--disable-wandb", action="store_true", help="Disable W&B logging.")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    slice_fields = [field.strip() for field in args.slice_fields.split(",") if field.strip()]
    grid = _default_grid()

    all_runs: List[Dict[str, Any]] = []
    all_runs.extend(
        _run_eval(
            test_dir=args.test_dir,
            output_dir=args.output_dir,
            label="main",
            grid=grid,
            max_examples=args.max_examples,
            slice_fields=slice_fields,
            wandb_project=args.wandb_project,
            wandb_entity=args.wandb_entity,
            disable_wandb=args.disable_wandb,
        )
    )

    if args.slices_dir.exists():
        all_runs.extend(
            _run_eval(
                test_dir=args.slices_dir,
                output_dir=args.output_dir,
                label="slices",
                grid=grid,
                max_examples=args.max_examples,
                slice_fields=slice_fields,
                wandb_project=args.wandb_project,
                wandb_entity=args.wandb_entity,
                disable_wandb=args.disable_wandb,
            )
        )

    report = {
        "runs": all_runs,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report_path = args.output_dir / "tuning_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote tuning report to {report_path}")


if __name__ == "__main__":
    main()
