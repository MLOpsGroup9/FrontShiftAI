import json
from pathlib import Path
from data_pipeline.scripts.chunker import ChunkGenerator

def test_chunker_creates_jsonl(tmp_path):
    # Create dummy cleaned JSON file
    sample_data = {
        "filename": "sample_handbook_cleaned.json",
        "text": " ".join(["This is a sentence."] * 200)  # enough for multiple chunks
    }
    input_dir = tmp_path / "cleaned"
    input_dir.mkdir()
    cleaned_file = input_dir / "sample_handbook_cleaned.json"
    cleaned_file.write_text(json.dumps(sample_data))

    output_dir = tmp_path / "chunked"
    generator = ChunkGenerator(input_dir=input_dir, output_dir=output_dir)
    stats = generator.process_all()

    # --- Assertions ---
    assert stats["total_docs"] == 1
    out_files = list(output_dir.glob("*.jsonl"))
    assert len(out_files) == 1
    lines = out_files[0].read_text().strip().split("\n")
    first = json.loads(lines[0])
    assert "text" in first and "metadata" in first
    assert first["metadata"]["token_count"] > 0
