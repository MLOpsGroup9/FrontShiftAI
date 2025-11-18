"""Convenience entrypoint to run chat pipeline evals/tuning from a single config."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from chat_pipeline.evaluation.evaluation_runner import EvaluationConfig, EvaluationRunner
from chat_pipeline.evaluation import tuning_runner
from chat_pipeline.utils.logger import setup_logging


logger = logging.getLogger(__name__)


def _load_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _run_eval_block(
    label: str,
    block: Dict[str, Any],
    slice_fields: List[str],
    pipeline_overrides: Optional[Dict[str, Any]],
    wandb_project: Optional[str],
    wandb_entity: Optional[str],
    disable_wandb: bool,
) -> Dict[str, Any]:
    test_dir = Path(block["test_dir"])
    output_dir = _ensure_dir(Path(block.get("output_dir", f"chat_pipeline/outputs/eval_{label}")))
    max_examples = block.get("max_examples")

    cfg = EvaluationConfig(
        test_questions_dir=test_dir,
        output_dir=output_dir,
        max_examples=max_examples,
        wandb_project=wandb_project,
        wandb_entity=wandb_entity,
        disable_wandb=disable_wandb,
        dataset_label=label,
        slice_fields=slice_fields,
    )
    runner = EvaluationRunner(cfg, config_overrides=pipeline_overrides or {})
    runner.run()

    summary_path = output_dir / "summary.json"
    bias_path = output_dir / "bias_report.json"
    return {
        "label": label,
        "output_dir": str(output_dir),
        "summary": json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {},
        "bias_report": json.loads(bias_path.read_text(encoding="utf-8")) if bias_path.exists() else {},
    }


def _run_tuning(
    cfg: Dict[str, Any],
    tuning_cfg: Dict[str, Any],
    slice_fields: List[str],
    wandb_project: Optional[str],
    wandb_entity: Optional[str],
    disable_wandb: bool,
) -> Path:
    output_dir = _ensure_dir(Path(tuning_cfg.get("output_dir", "chat_pipeline/outputs/tuning")))
    max_examples = tuning_cfg.get("max_examples")
    grid = tuning_cfg.get("grid") or tuning_runner._default_grid()

    all_runs: List[Dict[str, Any]] = []
    eval_cfg = cfg.get("eval", {})

    # main
    main_block = eval_cfg.get("main", {})
    all_runs.extend(
        tuning_runner._run_eval(  # type: ignore[attr-defined]
            test_dir=Path(main_block.get("test_dir", "chat_pipeline/evaluation/test_questions")),
            output_dir=output_dir,
            label="main",
            grid=grid,
            max_examples=max_examples,
            slice_fields=slice_fields,
            wandb_project=wandb_project,
            wandb_entity=wandb_entity,
            disable_wandb=disable_wandb,
        )
    )

    slices_block = eval_cfg.get("slices", {})
    if slices_block.get("enabled", False) and Path(slices_block.get("test_dir", "")).exists():
        all_runs.extend(
            tuning_runner._run_eval(  # type: ignore[attr-defined]
                test_dir=Path(slices_block.get("test_dir")),
                output_dir=output_dir,
                label="slices",
                grid=grid,
                max_examples=max_examples,
                slice_fields=slice_fields,
                wandb_project=wandb_project,
                wandb_entity=wandb_entity,
                disable_wandb=disable_wandb,
            )
        )

    report = {"runs": all_runs}
    report_path = output_dir / "tuning_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    logger.info("Wrote tuning report to %s", report_path)
    return report_path


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Chat pipeline runner (eval + tuning)")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("chat_pipeline/configs/experiments/quick_smoke.yaml"),
        help="Experiment config YAML",
    )
    args = parser.parse_args(argv)

    cfg = _load_config(args.config)

    log_cfg = cfg.get("logging", {})
    setup_logging(
        level=log_cfg.get("level"),
        to_file=log_cfg.get("to_file", False),
        log_dir=Path(log_cfg["log_dir"]) if log_cfg.get("log_dir") else None,
    )

    eval_cfg = cfg.get("eval", {})
    slice_fields = eval_cfg.get("slice_fields", ["category", "company_name"])
    pipeline_overrides = eval_cfg.get("pipeline_overrides")
    wandb_project = cfg.get("wandb", {}).get("project")
    wandb_entity = cfg.get("wandb", {}).get("entity")
    disable_wandb = cfg.get("wandb", {}).get("disable", True)

    results: List[Dict[str, Any]] = []

    if "main" in eval_cfg:
        results.append(
            _run_eval_block(
                label="main",
                block=eval_cfg["main"],
                slice_fields=slice_fields,
                pipeline_overrides=pipeline_overrides,
                wandb_project=wandb_project,
                wandb_entity=wandb_entity,
                disable_wandb=disable_wandb,
            )
        )

    slices_block = eval_cfg.get("slices", {})
    if slices_block.get("enabled", False):
        path = Path(slices_block.get("test_dir", ""))
        if path.exists():
            results.append(
                _run_eval_block(
                    label="slices",
                    block=slices_block,
                    slice_fields=slice_fields,
                    pipeline_overrides=pipeline_overrides,
                    wandb_project=wandb_project,
                    wandb_entity=wandb_entity,
                    disable_wandb=disable_wandb,
                )
            )
        else:
            logger.info("Slices dataset not found at %s; skipping slices eval.", path)

    tuning_cfg = cfg.get("tuning", {})
    if tuning_cfg.get("enabled", False):
        _run_tuning(
            cfg=cfg,
            tuning_cfg=tuning_cfg,
            slice_fields=slice_fields,
            wandb_project=wandb_project,
            wandb_entity=wandb_entity,
            disable_wandb=disable_wandb,
        )

    summary_path = Path(eval_cfg.get("summary_output", "chat_pipeline/outputs/experiment_summary.json"))
    _ensure_dir(summary_path.parent)
    summary_path.write_text(json.dumps({"evals": results}, indent=2), encoding="utf-8")
    logger.info("Wrote experiment summary to %s", summary_path)


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    main()
