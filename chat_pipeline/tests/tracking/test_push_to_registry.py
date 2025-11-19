import json
from pathlib import Path

from chat_pipeline.tracking import push_to_registry


def test_push_to_registry_writes_metadata_and_artifacts(monkeypatch, tmp_path: Path):
    registry_dir = tmp_path / "registry"
    registry_dir.mkdir()
    monkeypatch.setattr(push_to_registry, "REGISTRY_DIR", registry_dir)

    model_file = tmp_path / "models" / "model.bin"
    model_file.parent.mkdir()
    model_file.write_bytes(b"123")

    eval_summary = tmp_path / "summary.json"
    eval_summary.write_text(json.dumps({"precision": 1}), encoding="utf-8")
    bias_report = tmp_path / "bias.json"
    bias_report.write_text(json.dumps({"bias": "low"}), encoding="utf-8")

    metadata = push_to_registry.push_to_registry(
        model_name="demo_model",
        model_path=str(model_file),
        pipeline_config={"setting": True},
        evaluation_metrics={
            "groundedness": 4.5,
            "answer_relevance": 4.2,
            "factual_correctness": 4.0,
            "latency_avg_ms": 123,
        },
        artifacts={
            "eval_summary": str(eval_summary),
            "bias_report": str(bias_report),
        },
    )

    dest_dir = registry_dir / f"demo_model_{metadata['version']}"
    assert dest_dir.exists()
    assert (dest_dir / "metadata.json").exists()
    assert (dest_dir / "summary.json").exists()
    assert (dest_dir / "bias.json").exists()
    assert metadata["model_reference"]["sha256"]
    assert metadata["evaluation"]["groundedness"] == 4.5


def test_push_to_registry_increments_version(monkeypatch, tmp_path: Path):
    registry_dir = tmp_path / "registry"
    registry_dir.mkdir()
    monkeypatch.setattr(push_to_registry, "REGISTRY_DIR", registry_dir)

    # Pre-create a version folder to simulate prior runs.
    existing = registry_dir / "mymodel_v1"
    existing.mkdir()

    next_version = push_to_registry.get_next_version("mymodel")
    assert next_version == "v2"
