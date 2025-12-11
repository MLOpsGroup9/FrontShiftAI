"""
Voice pipeline configuration loading utilities.
Loads YAML config files with optional environment overrides for secrets.
"""
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


CONFIG_DIR = Path(__file__).resolve().parents[1] / "configs"
DEFAULT_CONFIG_PATH = CONFIG_DIR / "default.yaml"


def _read_yaml(path: Optional[Path]) -> Dict[str, Any]:
    if not path or not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


@dataclass
class ProviderConfig:
    provider: str
    model: Optional[str] = None
    kwargs: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderChainConfig:
    primary: ProviderConfig
    fallbacks: List[ProviderConfig] = field(default_factory=list)


@dataclass
class BackendConfig:
    url: str
    token: str


@dataclass
class LiveKitConfig:
    stt: ProviderChainConfig
    llm: ProviderChainConfig
    tts: ProviderChainConfig
    vad: ProviderConfig


@dataclass
class VoicePipelineConfig:
    backend: BackendConfig
    livekit: LiveKitConfig


def _provider_from_dict(data: Dict[str, Any], *, required: bool = True) -> ProviderConfig:
    if not data:
        if required:
            raise ValueError("Provider configuration is required")
        return ProviderConfig(provider="", model=None, kwargs={})
    provider = data.get("provider")
    if not provider:
        raise ValueError("Provider configuration must include 'provider'")
    return ProviderConfig(
        provider=provider,
        model=data.get("model"),
        kwargs=data.get("kwargs", {}) or {},
    )


def _chain_from_dict(data: Dict[str, Any]) -> ProviderChainConfig:
    primary = _provider_from_dict(data.get("primary", {}))
    fallbacks = [
        _provider_from_dict(item, required=False)
        for item in data.get("fallbacks", [])
        if item
    ]
    # Filter out empty placeholder providers
    fallbacks = [cfg for cfg in fallbacks if cfg.provider]
    return ProviderChainConfig(primary=primary, fallbacks=fallbacks)


def load_voice_config() -> VoicePipelineConfig:
    """
    Load configuration from VOICE_AGENT_CONFIG_PATH or default YAML,
    with environment variables overriding sensitive values.
    """
    custom_path = os.getenv("VOICE_AGENT_CONFIG_PATH")
    config_path = Path(custom_path).expanduser() if custom_path else DEFAULT_CONFIG_PATH
    data = _read_yaml(config_path if config_path.exists() else None)

    backend_data = data.get("backend", {})
    backend_url = os.getenv("VOICE_AGENT_BACKEND_URL", backend_data.get("url"))
    backend_token = os.getenv("VOICE_AGENT_JWT", backend_data.get("token"))

    if not backend_url:
        raise ValueError("Backend URL is required. Set VOICE_AGENT_BACKEND_URL or backend.url.")
    if not backend_token:
        raise ValueError("Backend token is required. Set VOICE_AGENT_JWT or backend.token.")

    backend = BackendConfig(url=backend_url.rstrip("/"), token=backend_token)

    livekit_data = data.get("livekit", {})
    stt_cfg = _chain_from_dict(livekit_data.get("stt", {}))
    llm_cfg = _chain_from_dict(livekit_data.get("llm", {}))
    tts_cfg = _chain_from_dict(livekit_data.get("tts", {}))
    vad_cfg = _provider_from_dict(livekit_data.get("vad", {}))

    livekit = LiveKitConfig(stt=stt_cfg, llm=llm_cfg, tts=tts_cfg, vad=vad_cfg)
    return VoicePipelineConfig(backend=backend, livekit=livekit)


__all__ = [
    "load_voice_config",
    "VoicePipelineConfig",
    "ProviderConfig",
    "ProviderChainConfig",
    "BackendConfig",
    "LiveKitConfig",
]
