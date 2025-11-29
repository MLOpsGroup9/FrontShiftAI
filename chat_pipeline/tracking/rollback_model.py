"""Helper CLI for listing versions and rolling back the local/remote registry."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_NAME = os.getenv("MODEL_NAME", "frontshift-rag")
DEFAULT_REGISTRY_TARGET = os.getenv("MODEL_REGISTRY_DIR", str(PROJECT_ROOT / "models_registry"))
DEFAULT_REGISTRY_CACHE = Path(os.getenv("MODEL_REGISTRY_CACHE", PROJECT_ROOT / "models_registry"))
REMOTE_REGISTRY_PREFIXES = ("gs://",)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List or rollback model versions in the registry.")
    parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME, help="Logical model name (default: frontshift-rag).")
    parser.add_argument(
        "--registry-dir",
        default=None,
        help="Override MODEL_REGISTRY_DIR (local path or gs:// URI).",
    )
    parser.add_argument(
        "--registry-cache-dir",
        type=Path,
        default=None,
        help="Local staging directory when syncing a remote registry.",
    )
    parser.add_argument("--list-versions", action="store_true", help="List available versions and exit.")
    parser.add_argument(
        "--describe-version",
        metavar="VERSION",
        help="Print metadata for a specific version (e.g., v5) and exit.",
    )
    parser.add_argument(
        "--resolve-target",
        action="store_true",
        help="Resolve the requested target version (or previous) and exit.",
    )
    parser.add_argument(
        "--target-version",
        help="Specific version to rollback to (e.g., v5).",
    )
    parser.add_argument(
        "--previous",
        action="store_true",
        help="Rollback to the version prior to the current latest.",
    )
    parser.add_argument(
        "--reason",
        help="Reason for rollback (required when executing rollback).",
    )
    parser.add_argument(
        "--metadata-output",
        type=Path,
        default=None,
        help="Optional path to write metadata JSON when describing a version.",
    )
    parser.add_argument(
        "--log-output",
        type=Path,
        default=None,
        help="Optional path to write rollback log JSON (in addition to registry logs).",
    )
    return parser.parse_args()


def _is_remote_registry(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in REMOTE_REGISTRY_PREFIXES)


def _configure_registry(
    registry_target: Optional[str],
    cache_dir: Optional[Path],
) -> Tuple[Path, Optional[str]]:
    target = registry_target or DEFAULT_REGISTRY_TARGET
    if _is_remote_registry(target):
        local_dir = (cache_dir or DEFAULT_REGISTRY_CACHE).expanduser().resolve()
        local_dir.mkdir(parents=True, exist_ok=True)
        return local_dir, target.rstrip("/") + "/"

    local_dir = Path(target).expanduser().resolve()
    local_dir.mkdir(parents=True, exist_ok=True)
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


def _list_version_dirs(model_name: str, registry_dir: Path) -> List[Path]:
    prefix = f"{model_name}_v"

    def _version_key(path: Path) -> int:
        try:
            return int(path.name.split("_v")[-1])
        except ValueError:
            return -1

    return sorted([p for p in registry_dir.glob(f"{prefix}*") if p.is_dir()], key=_version_key)


def list_versions(model_name: str, registry_dir: Path) -> List[str]:
    return [path.name.split("_v")[-1] for path in _list_version_dirs(model_name, registry_dir)]


def _latest_pointer(registry_dir: Path) -> Optional[Path]:
    latest = registry_dir / "latest"
    if latest.is_symlink():
        try:
            return latest.resolve()
        except OSError:
            return None
    if latest.exists():
        content = latest.read_text(encoding="utf-8").strip()
        if content:
            version_dir = registry_dir / content
            if version_dir.exists():
                return version_dir
    return None


def get_current_version(model_name: str, registry_dir: Path) -> Optional[str]:
    latest_dir = _latest_pointer(registry_dir)
    if latest_dir and latest_dir.is_dir():
        name = latest_dir.name
        prefix = f"{model_name}_"
        if name.startswith(prefix):
            return name.split("_v")[-1]
    versions = list_versions(model_name, registry_dir)
    return versions[-1] if versions else None


def get_previous_version(model_name: str, registry_dir: Path) -> Optional[str]:
    versions = list_versions(model_name, registry_dir)
    current = get_current_version(model_name, registry_dir)
    if not versions or not current:
        return None
    try:
        idx = versions.index(current)
    except ValueError:
        return versions[-2] if len(versions) >= 2 else None
    prev_idx = idx - 1
    if prev_idx < 0:
        return None
    return versions[prev_idx]


def _version_dir(model_name: str, version: str, registry_dir: Path) -> Path:
    return registry_dir / f"{model_name}_{version}"


def load_metadata(model_name: str, registry_dir: Path, version: str) -> Dict:
    path = _version_dir(model_name, version, registry_dir) / "metadata.json"
    if not path.exists():
        raise FileNotFoundError(f"Metadata not found for version {version} at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _set_latest(registry_dir: Path, version_dir: Path) -> None:
    latest = registry_dir / "latest"
    try:
        if latest.exists() or latest.is_symlink():
            latest.unlink()
        latest.symlink_to(version_dir.name)
    except OSError:
        latest.write_text(str(version_dir), encoding="utf-8")


def _write_rollback_log(registry_dir: Path, payload: Dict) -> Path:
    logs_dir = registry_dir / "rollback_logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_path = logs_dir / f"rollback_{timestamp}.json"
    log_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    return log_path


def _resolve_target_version(
    model_name: str,
    registry_dir: Path,
    target_version: Optional[str],
    use_previous: bool,
) -> str:
    if use_previous:
        prev = get_previous_version(model_name, registry_dir)
        if not prev:
            raise RuntimeError("No previous version available to rollback to.")
        return prev
    if not target_version:
        raise RuntimeError("Must specify --target-version or --previous.")
    versions = list_versions(model_name, registry_dir)
    if target_version not in versions:
        raise RuntimeError(f"Target version {target_version} not found in registry.")
    return target_version


def _perform_rollback(
    model_name: str,
    registry_dir: Path,
    version: str,
    reason: str,
    actor: Optional[str] = None,
) -> Path:
    current = get_current_version(model_name, registry_dir)
    if current == version:
        print(f"⚠️ Target version {version} is already active. Updating logs only.")
    version_dir = _version_dir(model_name, version, registry_dir)
    if not version_dir.exists():
        raise FileNotFoundError(f"Version directory not found: {version_dir}")
    _set_latest(registry_dir, version_dir)
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model_name": model_name,
        "previous_version": current,
        "target_version": version,
        "reason": reason,
        "actor": actor or os.getenv("GITHUB_ACTOR") or os.getenv("USER") or "unknown",
    }
    return _write_rollback_log(registry_dir, payload)


def main() -> None:
    args = _parse_args()
    registry_dir, remote_uri = _configure_registry(args.registry_dir, args.registry_cache_dir)

    if remote_uri:
        _sync_remote_registry(remote_uri, registry_dir, "pull")

    if args.list_versions:
        versions = list_versions(args.model_name, registry_dir)
        if versions:
            print("\n".join(versions))
        else:
            print("No versions found.")
        return

    if args.describe_version:
        metadata = load_metadata(args.model_name, registry_dir, args.describe_version)
        output = json.dumps(metadata, indent=2, ensure_ascii=True)
        print(output)
        if args.metadata_output:
            args.metadata_output.parent.mkdir(parents=True, exist_ok=True)
            args.metadata_output.write_text(output, encoding="utf-8")
        return

    if args.resolve_target:
        version = _resolve_target_version(args.model_name, registry_dir, args.target_version, args.previous)
        print(version)
        return

    target_version = _resolve_target_version(args.model_name, registry_dir, args.target_version, args.previous)
    if not args.reason:
        raise RuntimeError("Rollback reason is required when applying a rollback.")

    log_path = _perform_rollback(args.model_name, registry_dir, target_version, args.reason)
    print(
        f"✅ Rolled back {args.model_name} to {target_version}. "
        f"Log recorded at {log_path}"
    )

    if args.log_output:
        args.log_output.parent.mkdir(parents=True, exist_ok=True)
        args.log_output.write_text(log_path.read_text(encoding="utf-8"), encoding="utf-8")

    if remote_uri:
        _sync_remote_registry(remote_uri, registry_dir, "push")
        print(f"Synced rollback to remote registry: {remote_uri}")


if __name__ == "__main__":
    main()
