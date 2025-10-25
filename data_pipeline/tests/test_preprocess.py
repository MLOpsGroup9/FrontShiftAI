import json
from pathlib import Path
from data_pipeline.scripts.preprocess import TextPreprocessor

def test_preprocessor_creates_cleaned_json(tmp_path):
    """Test that preprocessing generates cleaned JSON files from markdown."""
    # Create a dummy markdown input file
    md_file = tmp_path / "sample.md"
    md_file.write_text("# Company Handbook\n\nThis is a sample policy document.\n\n## Benefits\nEmployees are eligible for PTO.")

    # Initialize preprocessor
    preprocessor = TextPreprocessor(
        input_dir=tmp_path,
        output_dir=tmp_path / "cleaned"
    )

    stats = preprocessor.process_all()

    # --- Assertions ---
    cleaned_files = list((tmp_path / "cleaned").glob("*_cleaned.json"))
    assert len(cleaned_files) == 1, "No cleaned JSON file generated"
    assert stats["total_docs"] == 1, "Document count mismatch"

    # Validate JSON structure
    with open(cleaned_files[0], "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "text" in data, "Missing 'text' key in cleaned output"
    assert "sections" in data, "Missing 'sections' key in cleaned output"
    assert len(data["text"]) > 10, "Cleaned text too short"


def test_section_detection_in_markdown(tmp_path):
    """Ensure section detection identifies headings correctly."""
    md_file = tmp_path / "handbook.md"
    md_file.write_text("# Overview\nSome intro text.\n\n## Policy\nDetails of the policy.")

    preprocessor = TextPreprocessor(
        input_dir=tmp_path,
        output_dir=tmp_path / "cleaned"
    )

    stats = preprocessor.process_all()

    cleaned_files = list((tmp_path / "cleaned").glob("*_cleaned.json"))
    with open(cleaned_files[0], "r", encoding="utf-8") as f:
        data = json.load(f)

    sections = data.get("sections", [])
    assert len(sections) >= 2, "Section detection failed"
    titles = [s["title"] for s in sections]
    assert "Overview" in titles and "Policy" in titles, "Expected section titles not found"


def test_preprocessor_handles_empty_file(tmp_path):
    """Preprocessor should skip empty or short markdown files."""
    md_file = tmp_path / "empty.md"
    md_file.write_text(" ")

    preprocessor = TextPreprocessor(
        input_dir=tmp_path,
        output_dir=tmp_path / "cleaned"
    )

    stats = preprocessor.process_all()
    assert stats["total_docs"] == 1, "Empty file should still count"
    cleaned_files = list((tmp_path / "cleaned").glob("*_cleaned.json"))
    assert len(cleaned_files) == 0, "Empty markdown should not produce cleaned output"
