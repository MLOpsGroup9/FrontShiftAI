"""Convenience entrypoint to run chat pipeline evals/tuning from a single config."""

from __future__ import annotations

import argparse
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from chat_pipeline.evaluation.evaluation_runner import EvaluationConfig, EvaluationRunner
from chat_pipeline.evaluation import tuning_runner
from chat_pipeline.utils.logger import setup_logging


logger = logging.getLogger(__name__)
DEFAULT_PARALLELISM = "sequential"


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
    wandb_tags: Optional[List[str]] = None,
    wandb_run_name: Optional[str] = None,
    mode: str = "full",
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
        wandb_tags=wandb_tags or [],
        wandb_run_name=wandb_run_name,
    )
    runner = EvaluationRunner(cfg, config_overrides=pipeline_overrides or {}, mode=mode)
    runner.run()

    summary_path = output_dir / "summary.json"
    bias_path = output_dir / "bias_report.json"
    return {
        "label": label,
        "output_dir": str(output_dir),
        "summary": json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {},
        "bias_report": json.loads(bias_path.read_text(encoding="utf-8")) if bias_path.exists() else {},
    }


def _build_eval_payload(
    label: str,
    block: Dict[str, Any],
    slice_fields: List[str],
    pipeline_overrides: Optional[Dict[str, Any]],
    wandb_project: Optional[str],
    wandb_entity: Optional[str],
    disable_wandb: bool,
    wandb_tags: Optional[List[str]],
    wandb_run_name: Optional[str],
    mode: str,
) -> Dict[str, Any]:
    return {
        "label": label,
        "block": block,
        "slice_fields": slice_fields,
        "pipeline_overrides": pipeline_overrides,
        "wandb_project": wandb_project,
        "wandb_entity": wandb_entity,
        "disable_wandb": disable_wandb,
        "wandb_tags": wandb_tags or [],
        "wandb_run_name": wandb_run_name,
        "mode": mode,
    }


def _derive_run_type_tag(config_path: Path) -> str:
    stem = config_path.stem.lower()
    if "full" in stem:
        return "run-type:full-eval"
    if "core" in stem:
        return "run-type:core-eval"
    if "smoke" in stem:
        return "run-type:smoke-test"
    return f"run-type:{stem}"


def _eval_block_worker(payload: Dict[str, Any]) -> Dict[str, Any]:
    return _run_eval_block(**payload)


def _maybe_run_with_ray(payloads: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
    try:
        import ray  # type: ignore
    except ImportError:  # pragma: no cover - optional dependency
        logger.warning("Ray not installed; falling back to sequential execution.")
        return None

    if not payloads:
        return []

    needs_shutdown = False
    if not ray.is_initialized():  # type: ignore[attr-defined]
        ray.init(ignore_reinit_error=True, log_to_driver=False)  # type: ignore[attr-defined]
        needs_shutdown = True

    @ray.remote  # type: ignore[attr-defined]
    def _ray_runner(payload: Dict[str, Any]) -> Dict[str, Any]:
        return _eval_block_worker(payload)

    futures = [_ray_runner.remote(payload) for payload in payloads]  # type: ignore[attr-defined]
    results = ray.get(futures)  # type: ignore[attr-defined]
    if needs_shutdown:
        ray.shutdown()  # type: ignore[attr-defined]
    return results


def _execute_eval_payloads(payloads: List[Dict[str, Any]], parallelism: str) -> List[Dict[str, Any]]:
    if not payloads:
        return []

    # Check if Ray should be disabled via environment variable
    if os.environ.get("CHAT_PIPELINE_DISABLE_RAY", "0") == "1":
        logger.info("Ray disabled via CHAT_PIPELINE_DISABLE_RAY; forcing sequential execution")
        return [_eval_block_worker(payload) for payload in payloads]

    if parallelism == "ray" and len(payloads) > 1:
        ray_results = _maybe_run_with_ray(payloads)
        if ray_results is not None:
            return ray_results

    if parallelism == "multiprocessing" and len(payloads) > 1:
        from multiprocessing import get_context

        ctx = get_context("spawn")
        worker_count = min(len(payloads), os.cpu_count() or 1) or 1
        with ctx.Pool(processes=worker_count) as pool:
            return pool.map(_eval_block_worker, payloads)

    return [_eval_block_worker(payload) for payload in payloads]


def _determine_parallelism(cfg: Dict[str, Any], cli_parallelism: Optional[int] = None) -> str:
    # CLI argument takes highest priority
    if cli_parallelism is not None:
        if cli_parallelism == 1:
            return "sequential"
        return "ray"
    
    execution_cfg = cfg.get("execution_modes") or {}
    override_mode = os.getenv("CHAT_PIPELINE_EXECUTION_MODE")
    if override_mode:
        key = override_mode.strip().lower()
    else:
        key = "ci" if os.getenv("CI") else "local"
    entry = execution_cfg.get(key) or execution_cfg.get("local", {})
    parallelism = entry.get("parallelism")
    if not parallelism:
        return DEFAULT_PARALLELISM
    return str(parallelism).lower()


def _run_tuning(
    cfg: Dict[str, Any],
    tuning_cfg: Dict[str, Any],
    slice_fields: List[str],
    wandb_project: Optional[str],
    wandb_entity: Optional[str],
    disable_wandb: bool,
    wandb_tags: Optional[List[str]] = None,
    run_name_prefix: Optional[str] = None,
    run_timestamp: Optional[str] = None,
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
            wandb_tags=wandb_tags,
            run_name_prefix=run_name_prefix,
            run_timestamp=run_timestamp,
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
                wandb_tags=wandb_tags,
                run_name_prefix=run_name_prefix,
                run_timestamp=run_timestamp,
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
    parser.add_argument("--debug", action="store_true", help="Enable verbose logging output.")
    parser.add_argument(
        "--mode",
        choices=("full", "generate", "judge"),
        default="full",
        help="Run mode: full (default), generate-only, or judge-only.",
    )
    parser.add_argument(
        "--parallelism",
        type=int,
        default=None,
        help="Number of parallel workers (1 for sequential execution)",
    )
    args = parser.parse_args(argv)

    cfg = _load_config(args.config)
    run_ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")

    log_cfg = cfg.get("logging", {})
    setup_logging(
        level="DEBUG" if args.debug else log_cfg.get("level"),
        to_file=log_cfg.get("to_file", False),
        log_dir=Path(log_cfg["log_dir"]) if log_cfg.get("log_dir") else None,
    )

    eval_cfg = cfg.get("eval", {})
    slice_fields = eval_cfg.get("slice_fields", ["category", "company_name"])
    pipeline_overrides = eval_cfg.get("pipeline_overrides")
    wandb_cfg = cfg.get("wandb", {}) or {}
    wandb_project = wandb_cfg.get("project")
    wandb_entity = wandb_cfg.get("entity")
    disable_wandb = wandb_cfg.get("disable", True)
    base_tags = list(wandb_cfg.get("tags") or [])
    run_type_tag = _derive_run_type_tag(args.config)
    if run_type_tag:
        base_tags.append(run_type_tag)
    wandb_tags = sorted({tag for tag in base_tags if tag})
    run_mode_tag = f"mode:{args.mode}"
    wandb_tags.append(run_mode_tag)
    base_run_name = run_type_tag.replace("run-type:", "") if run_type_tag else args.config.stem.lower()
    parallelism = _determine_parallelism(cfg, args.parallelism)

    results: List[Dict[str, Any]] = []
    eval_payloads: List[Dict[str, Any]] = []

    if "main" in eval_cfg:
            eval_payloads.append(
                _build_eval_payload(
                    label="main",
                    block=eval_cfg["main"],
                    slice_fields=slice_fields,
                    pipeline_overrides=pipeline_overrides,
                    wandb_project=wandb_project,
                    wandb_entity=wandb_entity,
                    disable_wandb=disable_wandb or args.mode == "generate",
                    wandb_tags=wandb_tags,
                    wandb_run_name=f"{base_run_name}-main-{run_ts}",
                    mode=args.mode,
                )
            )

    slices_block = eval_cfg.get("slices", {})
    if slices_block.get("enabled", False):
        path = Path(slices_block.get("test_dir", ""))
        if path.exists():
            eval_payloads.append(
                _build_eval_payload(
                    label="slices",
                    block=slices_block,
                    slice_fields=slice_fields,
                    pipeline_overrides=pipeline_overrides,
                    wandb_project=wandb_project,
                    wandb_entity=wandb_entity,
                    disable_wandb=disable_wandb or args.mode == "generate",
                    wandb_tags=wandb_tags,
                    wandb_run_name=f"{base_run_name}-slices-{run_ts}",
                    mode=args.mode,
                )
            )
        else:
            logger.info("Slices dataset not found at %s; skipping slices eval.", path)

    results.extend(_execute_eval_payloads(eval_payloads, parallelism))

    tuning_cfg = cfg.get("tuning", {})
    if tuning_cfg.get("enabled", False):
        if args.mode != "full":
            logger.info("Skipping tuning in '%s' mode.", args.mode)
        else:
            tuning_tags = sorted({*(wandb_tags or []), "tuning"})
            tuning_prefix = f"{base_run_name}-tuning"
            _run_tuning(
                cfg=cfg,
                tuning_cfg=tuning_cfg,
                slice_fields=slice_fields,
                wandb_project=wandb_project,
                wandb_entity=wandb_entity,
                disable_wandb=disable_wandb,
                wandb_tags=tuning_tags,
                run_name_prefix=tuning_prefix,
                run_timestamp=run_ts,
            )

    summary_path = Path(eval_cfg.get("summary_output", "chat_pipeline/outputs/experiment_summary.json"))
    _ensure_dir(summary_path.parent)
    summary_path.write_text(json.dumps({"evals": results}, indent=2), encoding="utf-8")
    logger.info("Wrote experiment summary to %s", summary_path)


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    main()