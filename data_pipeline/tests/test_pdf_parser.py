from pathlib import Path
from data_pipeline.scripts.pdf_parser import MarkdownPDFExtractor

def get_any_pdf():
    raw_dir = Path("data/raw")  # ✅ fixed path
    pdf_files = list(raw_dir.glob("*.pdf"))
    assert pdf_files, f"No PDF files found in {raw_dir.resolve()}"
    return str(pdf_files[0])

def test_extraction_creates_output():
    pdf_path = get_any_pdf()
    extractor = MarkdownPDFExtractor(pdf_path)
    extractor.extract()

    parsed_dir = Path("data/parsed")  # ✅ fixed
    assert parsed_dir.exists(), "Parsed directory not created"

    md_files = list(parsed_dir.glob("*.md"))
    assert len(md_files) > 0, "No markdown files generated in parsed/"

def test_extraction_file_content():
    parsed_dir = Path("data/parsed")  # ✅ fixed
    md_files = list(parsed_dir.glob("*.md"))
    assert md_files, "No markdown files found"

    first_md = md_files[0]
    with open(first_md, "r", encoding="utf-8") as f:
        content = f.read()
    assert len(content.strip()) > 100, "Extracted markdown file is empty or too short"

def test_extraction_output_structure():
    base_dir = Path("data")
    parsed_dir = base_dir / "parsed"  # ✅ fixed
    cleaned_dir = base_dir / "cleaned"

    assert parsed_dir.exists(), "Parsed directory missing"
    sample_file = next(parsed_dir.glob("*.md"), None)
    assert sample_file is not None, "No parsed file found"
    assert sample_file.suffix == ".md", "Parsed output should be markdown (.md)"
