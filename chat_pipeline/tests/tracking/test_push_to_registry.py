from pathlib import Path

from chat_pipeline.tracking import push_to_registry


def test_push_to_registry_copies_model_and_writes_metadata(monkeypatch, tmp_path: Path):
    model_dir = tmp_path / "models"
    registry_dir = tmp_path / "registry"
    model_dir.mkdir()
    registry_dir.mkdir()

    model_file = model_dir / "model.bin"
    model_file.write_bytes(b"123")

    monkeypatch.setattr(push_to_registry, "MODEL_SOURCE_DIR", model_dir)
    monkeypatch.setattr(push_to_registry, "REGISTRY_DIR", registry_dir)

    metadata = push_to_registry.push_to_registry("demo_model", model_file.name, {"score": 0.99})

    dest_dir = registry_dir / f"demo_model_{metadata['version']}"
    assert dest_dir.exists()
    assert (dest_dir / model_file.name).read_bytes() == b"123"
    written = (dest_dir / "metadata.json").read_text(encoding="utf-8")
    assert '"score": 0.99' in written


def test_push_to_registry_increments_version(monkeypatch, tmp_path: Path):
    registry_dir = tmp_path / "registry"
    registry_dir.mkdir()
    monkeypatch.setattr(push_to_registry, "REGISTRY_DIR", registry_dir)

    # Pre-create a version folder to simulate prior runs.
    existing = registry_dir / "mymodel_v1"
    existing.mkdir()

    next_version = push_to_registry.get_next_version("mymodel")
    assert next_version == "v2"
