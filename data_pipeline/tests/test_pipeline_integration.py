from pathlib import Path
from data_pipeline.scripts.data_extraction_not_ import main as extract_main
from data_pipeline.scripts.preprocess import main as preprocess_main

def test_full_pipeline_flow():
    # Run extraction
    extract_main()

    extracted_dir = Path("data_pipeline/data/extracted")
    combined = extracted_dir / "combined_chunks.json"
    assert combined.exists(), "combined_chunks.json not created"

    # Run preprocessing
    preprocess_main()

    cleaned_dir = Path("data_pipeline/data/cleaned")
    cleaned_file = cleaned_dir / "cleaned_chunks.csv"
    assert cleaned_file.exists(), "Cleaned CSV not generated after preprocessing"
