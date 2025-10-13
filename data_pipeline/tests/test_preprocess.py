import json
import pandas as pd
from pathlib import Path
from data_pipeline.scripts.preprocess import (
    load_extracted_data,
    clean_chunks,
    convert_to_dataframe,
    save_cleaned
)

def test_load_extracted_data_returns_lists():
    combined, tables = load_extracted_data("data_pipeline/data/extracted")
    assert isinstance(combined, list)
    assert isinstance(tables, list)
    assert len(combined) > 0, "Combined data should not be empty"


def test_clean_chunks_removes_newlines_and_extra_spaces():
    sample = [{"text": " Hello\nWorld  ", "metadata": {"filename": "a.pdf", "company": "A", "chunk_id": 1}}]
    cleaned = clean_chunks(sample)
    text = cleaned[0]["text"]
    assert "\n" not in text
    assert text == "Hello World"


def test_convert_to_dataframe_has_columns():
    sample = [{"text": "sample", "metadata": {"filename": "a.pdf", "company": "A", "chunk_id": 1}}]
    df = convert_to_dataframe(sample)
    expected_cols = {"filename", "company", "chunk_id", "text"}
    assert expected_cols.issubset(df.columns)
    assert len(df) == 1


def test_save_cleaned_creates_file(tmp_path):
    df = pd.DataFrame([{"filename": "a.pdf", "company": "A", "chunk_id": 1, "text": "hello"}])
    output_file = save_cleaned(df, out_dir=tmp_path)
    assert output_file.exists(), "Cleaned CSV not saved correctly"
    content = pd.read_csv(output_file)
    assert len(content) == 1, "CSV content mismatch"


def test_empty_chunk_handling():
    sample = [{"text": "   ", "metadata": {}}]
    cleaned = clean_chunks(sample)
    df = convert_to_dataframe(cleaned)
    assert len(df) == 1
    assert isinstance(df.iloc[0]["text"], str)
