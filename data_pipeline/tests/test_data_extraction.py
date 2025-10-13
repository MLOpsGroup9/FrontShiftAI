from pathlib import Path
import json
from data_pipeline.scripts.data_extraction import main as extract_main

def test_extraction_creates_output():
    # Run extraction
    extract_main()

    extracted_dir = Path("data_pipeline/data/extracted")
    combined = extracted_dir / "combined_chunks.json"
    tables = extracted_dir / "table_chunks.json"

    assert combined.exists(), "combined_chunks.json not created"
    assert tables.exists(), "table_chunks.json not created"


def test_extraction_non_empty():
    combined_path = Path("data_pipeline/data/extracted/combined_chunks.json")
    assert combined_path.exists(), "combined_chunks.json missing"

    with open(combined_path) as f:
        data = json.load(f)

    assert isinstance(data, list), "Extracted chunks should be a list"
    assert len(data) > 0, "Extracted chunks file is empty"


def test_extraction_chunk_structure():
    combined_path = Path("data_pipeline/data/extracted/combined_chunks.json")
    assert combined_path.exists(), "combined_chunks.json missing"

    with open(combined_path) as f:
        chunks = json.load(f)

    first = chunks[0]
    assert "text" in first, "Missing text field in extracted chunk"
    assert "metadata" in first, "Missing metadata field"
    assert isinstance(first["metadata"], dict), "Metadata is not a dictionary"
