import json
from pathlib import Path
import pymupdf4llm
from langchain.text_splitter import MarkdownTextSplitter


def main():
    # Directories
    data_dir = Path(__file__).resolve().parents[1] / "data"
    raw_dir = data_dir / "raw"
    output_dir = data_dir / "extracted"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Chunk configuration
    chunk_size = 1024
    chunk_overlap = 64
    splitter = MarkdownTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    all_chunks = []

    # Load PDFs
    pdf_files = list(raw_dir.glob("*.pdf"))
    if not pdf_files:
        print("⚠️ No PDFs found in data/raw/")
        return

    for pdf_path in pdf_files:
        print(f"📘 Processing {pdf_path.name} ...")
        try:
            # Convert PDF to Markdown text
            markdown_text = pymupdf4llm.to_markdown(pdf_path)

            # Split Markdown text into chunks
            documents = splitter.create_documents([markdown_text])

            # Convert to dict with metadata
            for i, doc in enumerate(documents):
                all_chunks.append({
                    "text": doc.page_content,
                    "metadata": {
                        "filename": pdf_path.name,
                        "document_name": pdf_path.stem,
                        "chunk_id": i + 1
                    }
                })

            print(f"✅ {len(documents)} chunks extracted from {pdf_path.name}")

        except Exception as e:
            print(f"❌ Error processing {pdf_path.name}: {e}")

    # Save output JSON
    output_path = output_dir / "combined_chunks.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Done! Extracted {len(all_chunks)} total chunks from {len(pdf_files)} PDFs.")
    print(f"📄 Output saved at: {output_path}")


if __name__ == "__main__":
    main()
