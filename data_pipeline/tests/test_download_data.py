import json
from pathlib import Path
import pytest
from data_pipeline.scripts import download_data

def test_download_pdf_creates_files(tmp_path, monkeypatch):
    # --- Setup ---
    fake_pdf_content = b"%PDF-1.4 fake pdf"
    urls_file = tmp_path / "urls.json"
    out_dir = tmp_path / "raw"
    out_dir.mkdir()

    urls = [
        {"domain": "example.com", "company": "TestCorp", "url": "https://fake-url.com/sample.pdf"}
    ]
    urls_file.write_text(json.dumps(urls))

    class FakeResponse:
        ok = True
        status_code = 200
        def iter_content(self, chunk_size=1024):
            yield fake_pdf_content

    # Patch requests.get to return fake response
    monkeypatch.setattr(download_data.requests, "get", lambda *a, **k: FakeResponse())

    # --- Run ---
    download_data.download_pdf(urls_path=urls_file, save_dir=out_dir)

    # --- Assert ---
    files = list(out_dir.glob("*.pdf"))
    assert files, "PDF file was not created"
    content = files[0].read_bytes()
    assert fake_pdf_content in content
