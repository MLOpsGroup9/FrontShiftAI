import json
from pathlib import Path
import pymupdf4llm
from pymupdf4llm.text_splitter import SentenceSplitter

def main():
    data_dir = Path(__file__).resolve().parents[1] / "data"
    raw_dir = data_dir / "raw"
    output_dir = data_dir / "extracted"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Chunk config
    splitter = SentenceSplitter(chunk_size=1024, chunk_overlap=64)
    all_chunks = []

    # Process all PDFs in data/raw
    pdf_files = list(raw_dir.glob("*.pdf"))
    if not pdf_files:
        print("⚠️ No PDFs found in data/raw/")
        return

    for pdf_path in pdf_files:
        print(f"📘 Processing {pdf_path.name} ...")
        try:
            chunks = splitter.split_file(pdf_path)

            # Add metadata (filename, doc id, etc.)
            for c in chunks:
                c["metadata"]["filename"] = pdf_path.name
                c["metadata"]["document_name"] = pdf_path.stem

            all_chunks.extend(chunks)
            print(f"✅ {len(chunks)} chunks extracted from {pdf_path.name}")
        except Exception as e:
            print(f"❌ Error processing {pdf_path.name}: {e}")

    # Save final combined JSON
    output_path = output_dir / "combined_chunks.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Done! Extracted {len(all_chunks)} total chunks from {len(pdf_files)} PDFs.")
    print(f"📄 Output saved at: {output_path}")

if __name__ == "__main__":
    main()
