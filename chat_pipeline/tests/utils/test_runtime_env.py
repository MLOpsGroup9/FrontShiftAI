from chat_pipeline.utils import runtime_env


def test_allow_heavy_fallbacks_with_override(monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_ALLOW_HEAVY_FALLBACKS", "1")
    assert runtime_env.allow_heavy_fallbacks() is True
    monkeypatch.setenv("CHAT_PIPELINE_ALLOW_HEAVY_FALLBACKS", "false")
    assert runtime_env.allow_heavy_fallbacks() is False


def test_allow_heavy_fallbacks_self_hosted_default(monkeypatch):
    monkeypatch.delenv("CHAT_PIPELINE_ALLOW_HEAVY_FALLBACKS", raising=False)
    monkeypatch.setenv("CHAT_PIPELINE_SELF_HOSTED", "true")
    assert runtime_env.allow_heavy_fallbacks() is True


def test_remote_timeout_seconds(monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_REMOTE_TIMEOUT", "30")
    assert runtime_env.remote_timeout_seconds() == 30
    monkeypatch.setenv("CHAT_PIPELINE_REMOTE_TIMEOUT", "invalid")
    assert runtime_env.remote_timeout_seconds(default=50) == 50


def test_remote_request_delay_seconds(monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_REMOTE_REQUEST_DELAY", "3.5")
    assert runtime_env.remote_request_delay_seconds() == 3.5
    monkeypatch.setenv("CHAT_PIPELINE_REMOTE_REQUEST_DELAY", "-1")
    assert runtime_env.remote_request_delay_seconds() == 1.0
