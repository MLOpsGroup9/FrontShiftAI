import json
from pathlib import Path
from data_pipeline.scripts import store_in_chromadb

class DummyCollection:
    def __init__(self): self.add_called = False
    def add(self, **kwargs): self.add_called = True

class DummyClient:
    def __init__(self, path): self.collections = {}
    def list_collections(self): return []
    def create_collection(self, name, embedding_function):
        self.collections[name] = DummyCollection()
        return self.collections[name]

def test_store_in_chromadb_creates_embeddings(tmp_path, monkeypatch):
    # --- Arrange ---
    project_root = tmp_path / "fake_project"
    data_dir = project_root / "data" / "validated"
    data_dir.mkdir(parents=True)

    jsonl = data_dir / "valid_chunks.jsonl"
    jsonl.write_text(json.dumps({
        "text": "Sample text.",
        "metadata": {
            "company": "X",
            "chunk_id": "c1",
            "doc_id": "f1",
            "section_title": "Intro",
            "hash_64": "abcd"
        }
    }) + "\n")

    # Patch Path(__file__).resolve().parents[1] → tmp_path/fake_project
    fake_file = project_root / "scripts" / "store_in_chromadb.py"
    fake_file.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(store_in_chromadb.Path, "resolve", lambda self: fake_file)

    # Patch ChromaDB client
    monkeypatch.setattr(store_in_chromadb.chromadb, "PersistentClient", DummyClient)

    # --- Act ---
    store_in_chromadb.main()

    # --- Assert ---
    out_path = project_root / "data" / "vector_db"
    assert out_path.exists(), f"Expected {out_path} to be created"
