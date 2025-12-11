"""Environment helpers shared across runtime components."""

from __future__ import annotations

import os


def _str_to_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return _str_to_bool(raw)


def allow_heavy_fallbacks() -> bool:
    """Return True when large local/HF backends may be used."""

    override = os.getenv("CHAT_PIPELINE_ALLOW_HEAVY_FALLBACKS")
    if override is not None:
        return _str_to_bool(override)
    return env_flag("CHAT_PIPELINE_SELF_HOSTED", False)


def remote_timeout_seconds(default: int = 45) -> int:
    value = os.getenv("CHAT_PIPELINE_REMOTE_TIMEOUT", str(default))
    try:
        return max(int(value), 5)
    except ValueError:
        return default


def remote_max_attempts(default: int = 3) -> int:
    value = os.getenv("CHAT_PIPELINE_REMOTE_MAX_ATTEMPTS", str(default))
    try:
        return max(int(value), 1)
    except ValueError:
        return default


def remote_retry_backoff(default: float = 2.0) -> float:
    value = os.getenv("CHAT_PIPELINE_REMOTE_RETRY_BACKOFF", str(default))
    try:
        return max(float(value), 1.0)
    except ValueError:
        return default


def remote_retry_initial_delay(default: float = 2.0) -> float:
    value = os.getenv("CHAT_PIPELINE_REMOTE_RETRY_INITIAL_DELAY", str(default))
    try:
        return max(float(value), 0.5)
    except ValueError:
        return default


def remote_request_delay_seconds(default: float = 1.0) -> float:
    value = os.getenv("CHAT_PIPELINE_REMOTE_REQUEST_DELAY", str(default))
    try:
        parsed = float(value)
        return parsed if parsed >= 0.0 else default
    except ValueError:
        return default


def task_timeout_seconds(default: float = 600.0) -> float:
    value = os.getenv("CHAT_PIPELINE_TASK_TIMEOUT", str(default))
    try:
        return max(float(value), 10.0)
    except ValueError:
        return default


def consecutive_failure_limit(default: int = 5) -> int:
    value = os.getenv("CHAT_PIPELINE_MAX_CONSECUTIVE_FAILURES", str(default))
    try:
        return max(int(value), 1)
    except ValueError:
        return default
