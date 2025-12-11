"""Helper CLI to push evaluated models into the lightweight registry.

Supports both local directories and remote GCS buckets (via MODEL_REGISTRY_DIR)."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from chat_pipeline.rag.pipeline import load_pipeline_config
from chat_pipeline.tracking import push_to_registry


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_PATH = os.getenv("LLAMA_MODEL_PATH")
DEFAULT_MODEL_NAME = os.getenv("MODEL_NAME", "frontshift-rag")
DEFAULT_RESULTS_DIR = Path(os.getenv("RESULTS_DIR", "chat_pipeline/results"))
DEFAULT_REGISTRY_TARGET = os.getenv("MODEL_REGISTRY_DIR", str(PROJECT_ROOT / "models_registry"))
DEFAULT_REGISTRY_CACHE = Path(os.getenv("MODEL_REGISTRY_CACHE", PROJECT_ROOT / "models_registry"))
REMOTE_REGISTRY_PREFIXES = ("gs://",)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Register a model in the local metadata registry after evaluations."
    )
    parser.add_argument(
        "--model-path",
        default=DEFAULT_MODEL_PATH,
        help="Path to the model weights on disk (optional).",
    )
    parser.add_argument(
        "--model-name",
        default=DEFAULT_MODEL_NAME,
        help="Logical model name to version inside the registry.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=DEFAULT_RESULTS_DIR,
        help="Directory that contains evaluation artifacts (default: chat_pipeline/results).",
    )
    parser.add_argument(
        "--summary-path",
        type=Path,
        default=None,
        help="Optional explicit path to the core evaluation summary.json.",
    )
    parser.add_argument(
        "--bias-report-path",
        type=Path,
        default=None,
        help="Optional explicit path to the bias_report.json.",
    )
    parser.add_argument(
        "--quality-gate-path",
        type=Path,
        default=None,
        help="Path to quality gate status file (default: <results>/quality_gate.txt).",
    )
    parser.add_argument(
        "--quality-gate-status",
        default=None,
        help="Override quality gate status (PASS/FAIL).",
    )
    parser.add_argument(
        "--allow-gate-fail",
        action="store_true",
        help="Push to the registry even when the quality gate reports FAIL.",
    )
    parser.add_argument(
        "--metadata-output",
        type=Path,
        default=None,
        help="Optional path to write the generated registry metadata JSON.",
    )
    parser.add_argument(
        "--pipeline-config",
        type=Path,
        default=None,
        help="Path to a JSON file containing the pipeline config to embed.",
    )
    parser.add_argument(
        "--registry-dir",
        default=None,
        help="Override MODEL_REGISTRY_DIR (can be a local path or gs:// bucket URI).",
    )
    parser.add_argument(
        "--registry-cache-dir",
        type=Path,
        default=None,
        help="Local staging directory when syncing a remote registry (default: models_registry_cache).",
    )
    return parser.parse_args()


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _pipeline_config(config_path: Optional[Path]) -> Dict[str, Any]:
    if config_path:
        return _load_json(config_path)
    return load_pipeline_config()


def _evaluation_metrics(summary: Dict[str, Any]) -> Dict[str, Any]:
    latency_ms = summary.get("latency_avg_ms")
    if latency_ms is None and summary.get("latency_total") is not None:
        latency_ms = float(summary["latency_total"]) * 1000.0

    return {
        "groundedness": summary.get("groundedness"),
        "answer_relevance": summary.get("answer_relevance"),
        "factual_correctness": summary.get("factual_correctness"),
        "latency_avg_ms": latency_ms,
    }


def _resolve_quality_status(override: Optional[str], status_file: Path) -> str:
    candidate = (override or "").strip().upper()
    if candidate and candidate != "AUTO":
        return candidate

    if status_file.exists():
        file_value = status_file.read_text(encoding="utf-8").strip().upper()
        if file_value:
            return file_value

    raise RuntimeError(
        "Quality gate status unavailable. Provide --quality-gate-status "
        "or run compute_quality_gate.py first."
    )


def _is_remote_registry(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in REMOTE_REGISTRY_PREFIXES)


def _configure_registry(
    registry_target: Optional[str],
    cache_dir: Optional[Path],
) -> Tuple[Path, Optional[str]]:
    """Return the local registry dir and optional remote URI."""

    target = registry_target or DEFAULT_REGISTRY_TARGET
    if _is_remote_registry(target):
        local_dir = (cache_dir or DEFAULT_REGISTRY_CACHE).expanduser().resolve()
        local_dir.mkdir(parents=True, exist_ok=True)
        push_to_registry.REGISTRY_DIR = local_dir
        os.environ["MODEL_REGISTRY_DIR"] = str(local_dir)
        return local_dir, target.rstrip("/") + "/"

    local_dir = Path(target).expanduser().resolve()
    local_dir.mkdir(parents=True, exist_ok=True)
    push_to_registry.REGISTRY_DIR = local_dir
    os.environ["MODEL_REGISTRY_DIR"] = str(local_dir)
    return local_dir, None


def _sync_remote_registry(remote_uri: str, local_dir: Path, direction: str) -> None:
    if direction not in {"pull", "push"}:
        raise ValueError("direction must be 'pull' or 'push'")

    src, dest = (remote_uri, str(local_dir)) if direction == "pull" else (str(local_dir), remote_uri)
    action = "Downloading" if direction == "pull" else "Uploading"
    print(f"{action} registry via gsutil rsync: {src} -> {dest}")

    try:
        result = subprocess.run(
            ["gsutil", "-m", "rsync", "-r", src, dest],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("gsutil command not found. Ensure the Google Cloud SDK is installed.") from exc

    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "unknown error"
        if direction == "pull" and "matched no objects" in message.lower():
            print("Remote registry is empty; continuing with fresh local staging directory.")
            return
        raise RuntimeError(f"gsutil rsync failed ({direction}): {message}")


def main() -> None:
    args = _parse_args()

    raw_model_path = (args.model_path or "").strip()
    model_path: Optional[str] = None
    if raw_model_path:
        model_candidate = Path(raw_model_path).expanduser()
        if model_candidate.exists():
            model_path = str(model_candidate.resolve())
        else:
            model_path = raw_model_path

    if model_path:
        print(f"Using model reference: {model_path}")
    else:
        print("No model path provided; registry entry will not include a local model checksum.")

    results_dir = args.results_dir
    summary_path = args.summary_path or (results_dir / "core_eval_main" / "summary.json")
    bias_report_path = args.bias_report_path or (results_dir / "core_eval_slices" / "bias_report.json")
    quality_gate_path = args.quality_gate_path or (results_dir / "quality_gate.txt")
    local_registry_dir, remote_registry_uri = _configure_registry(
        registry_target=args.registry_dir,
        cache_dir=args.registry_cache_dir,
    )

    if remote_registry_uri:
        _sync_remote_registry(remote_registry_uri, local_registry_dir, "pull")

    status = _resolve_quality_status(args.quality_gate_status, quality_gate_path)
    print(f"Quality gate status: {status}")
    if not args.allow_gate_fail and status != "PASS":
        raise SystemExit("Refusing to push to registry because the quality gate failed.")

    summary = _load_json(summary_path)
    evaluation_metrics = _evaluation_metrics(summary)

    artifacts: Dict[str, Optional[str]] = {}
    if summary_path.exists():
        artifacts["eval_summary"] = str(summary_path)
    if bias_report_path.exists():
        artifacts["bias_report"] = str(bias_report_path)

    metadata = push_to_registry.push_to_registry(
        model_name=args.model_name,
        model_path=model_path,
        pipeline_config=_pipeline_config(args.pipeline_config),
        evaluation_metrics=evaluation_metrics,
        artifacts=artifacts,
    )

    print(f"Registered {metadata['model_name']} version {metadata['version']} in {local_registry_dir}")

    if remote_registry_uri:
        _sync_remote_registry(remote_registry_uri, local_registry_dir, "push")
        print(f"Synced registry to remote bucket: {remote_registry_uri}")

    if args.metadata_output:
        args.metadata_output.parent.mkdir(parents=True, exist_ok=True)
        args.metadata_output.write_text(json.dumps(metadata, indent=2, ensure_ascii=True), encoding="utf-8")
        print(f"Metadata written to {args.metadata_output}")


if __name__ == "__main__":
    main()
