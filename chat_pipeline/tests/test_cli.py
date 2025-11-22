from chat_pipeline import cli


def test_determine_parallelism_local(monkeypatch):
    monkeypatch.delenv("CHAT_PIPELINE_EXECUTION_MODE", raising=False)
    monkeypatch.delenv("CI", raising=False)
    cfg = {
        "execution_modes": {
            "local": {"parallelism": "ray"},
            "ci": {"parallelism": "multiprocessing"},
        }
    }
    assert cli._determine_parallelism(cfg) == "ray"


def test_determine_parallelism_ci_override(monkeypatch):
    monkeypatch.delenv("CHAT_PIPELINE_EXECUTION_MODE", raising=False)
    monkeypatch.setenv("CI", "true")
    cfg = {
        "execution_modes": {
            "local": {"parallelism": "ray"},
            "ci": {"parallelism": "multiprocessing"},
        }
    }
    assert cli._determine_parallelism(cfg) == "multiprocessing"


def test_determine_parallelism_custom_env(monkeypatch):
    monkeypatch.setenv("CHAT_PIPELINE_EXECUTION_MODE", "custom")
    cfg = {"execution_modes": {"custom": {"parallelism": "ray"}}}
    assert cli._determine_parallelism(cfg) == "ray"
