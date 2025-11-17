from types import SimpleNamespace

from chat_pipeline.tracking import exp_tracking


class DummyArtifact:
    def __init__(self, name, type="dataset"):
        self.name = name
        self.type = type
        self.files = []

    def add_file(self, path):
        self.files.append(path)


class DummyWandb:
    def __init__(self):
        self.init_calls = []
        self.logs = []
        self.artifacts = []
        self.finished = 0

    def init(self, **kwargs):
        self.init_calls.append(kwargs)
        return SimpleNamespace()

    def log(self, payload):
        self.logs.append(payload)

    def Artifact(self, *args, **kwargs):
        return DummyArtifact(*args, **kwargs)

    def log_artifact(self, artifact):
        self.artifacts.append(artifact.name)

    def finish(self):
        self.finished += 1


def test_setup_wandb_records_config(monkeypatch):
    dummy = DummyWandb()
    monkeypatch.setattr(exp_tracking, "wandb", dummy)

    run = exp_tracking.setup_wandb(stage_name="eval", model_name="demo")

    assert isinstance(run, SimpleNamespace)
    assert dummy.init_calls
    call = dummy.init_calls[0]
    assert call["job_type"] == "eval"
    assert call["config"]["model_name"] == "demo"


def test_log_metrics_logs_and_artifacts(monkeypatch, tmp_path):
    dummy = DummyWandb()
    monkeypatch.setattr(exp_tracking, "wandb", dummy)

    artifact_file = tmp_path / "metrics.json"
    artifact_file.write_text("{}", encoding="utf-8")

    exp_tracking.log_metrics(
        stage_name="stage",
        model_name="demo",
        metrics={"m": 1},
        artifacts={"metrics": artifact_file},
    )

    assert dummy.logs == [{"m": 1}]
    assert dummy.artifacts == ["metrics_demo"]
    assert dummy.finished == 1
