import json
from pathlib import Path
from data_pipeline.scripts import validate_data

def test_validate_chunks_creates_reports(tmp_path):
    # Create a valid chunk entry
    valid_chunk = {
        "text": "This is a valid English text with enough words." * 5,
        "metadata": {
            "doc_id": "doc1",
            "company": "TestCorp",
            "source_url": "",
            "org": "General",
            "industry": "Finance",
            "doc_type": "handbook",
            "doc_title": "TestCorp Handbook",
            "doc_year": "2023",
            "section_path": "Intro",
            "section_title": "Welcome",
            "section_index": "",
            "chunk_id": "doc1_chunk_0001",
            "char_span": [0, 100],
            "sentence_count": 1,
            "content_type": "text",
            "prev_chunk_id": None,
            "next_chunk_id": None,
            "keywords": ["test"],
            "policy_tags": [],
            "hash_64": "abcdef1234567890",
            "created_at": "2024-01-01T00:00:00",
            "token_count": 10
        }
    }

    # --- Arrange test input directory ---
    chunk_dir = tmp_path / "chunked"
    chunk_dir.mkdir()
    file_path = chunk_dir / "test.jsonl"
    file_path.write_text(json.dumps(valid_chunk) + "\n")

    # --- Redirect internal paths used by validate_data ---
    validate_data.CHUNKS_DIR = chunk_dir
    validate_data.DATA_DIR = tmp_path
    validate_data.VALIDATED_DIR = tmp_path / "validated"
    validate_data.REPORTS_DIR = tmp_path / "reports"

    # ✅ Create the necessary output directories
    validate_data.VALIDATED_DIR.mkdir(parents=True, exist_ok=True)
    validate_data.REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # --- Act ---
    validate_data.validate_all_chunks()

    # --- Assert ---
    validated = tmp_path / "validated" / "valid_chunks.jsonl"
    report_csv = tmp_path / "reports" / "validation_report.csv"
    summary_json = tmp_path / "reports" / "validation_summary.json"

    assert validated.exists(), "Expected valid_chunks.jsonl to be created"
    assert report_csv.exists(), "Expected validation_report.csv to be created"
    assert summary_json.exists(), "Expected validation_summary.json to be created"
    assert "TestCorp" in validated.read_text()
