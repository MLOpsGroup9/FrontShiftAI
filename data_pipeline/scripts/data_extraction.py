import json
from pathlib import Path
import camelot
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter


def main():
    project_root = Path(__file__).resolve().parents[1]
    data_dir = project_root / "data"
    raw_dir = data_dir / "raw"
    output_dir = data_dir / "extracted"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Chunk configuration
    chunk_size = 1024
    chunk_overlap = 64
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ".", " "]
    )

    all_chunks = []
    all_tables = []

    pdf_files = list(raw_dir.glob("*.pdf"))
    if not pdf_files:
        print("⚠️ No PDFs found in data/raw/")
        return

    for pdf_path in pdf_files:
        print(f"📘 Processing {pdf_path.name} ...")

        try:
            company_name = pdf_path.stem.strip().replace("_", " ")

            # --- TEXT EXTRACTION ---
            loader = PyPDFLoader(str(pdf_path))
            pages = loader.load_and_split()
            combined_text = "\n".join([p.page_content for p in pages if p.page_content.strip()])

            # --- TABLE EXTRACTION ---
            try:
                tables = camelot.read_pdf(str(pdf_path), pages="all")
                for i, table in enumerate(tables, start=1):
                    df = table.df
                    table_text = df.to_markdown(index=False)
                    all_tables.append({
                        "filename": pdf_path.name,
                        "table_index": i,
                        "data": df.to_dict(orient="records"),
                        "markdown": table_text
                    })
                    combined_text += f"\n\n### Table {i}\n{table_text}\n"
            except Exception as e:
                print(f"⚠️ Table extraction failed for {pdf_path.name}: {e}")

            # --- CHUNKING ---
            documents = splitter.create_documents([combined_text])
            for i, doc in enumerate(documents):
                all_chunks.append({
                    "text": doc.page_content,
                    "metadata": {
                        "filename": pdf_path.name,
                        "document_name": pdf_path.stem,
                        "chunk_id": i + 1,
                        "company": company_name
                    }
                })

            print(f"✅ {len(documents)} chunks extracted from {pdf_path.name}")

        except Exception as e:
            print(f"❌ Error processing {pdf_path.name}: {e}")

    # --- SAVE OUTPUTS ---
    (output_dir / "combined_chunks.json").write_text(
        json.dumps(all_chunks, indent=2, ensure_ascii=False)
    )
    (output_dir / "table_chunks.json").write_text(
        json.dumps(all_tables, indent=2, ensure_ascii=False)
    )

    print(f"\n✅ Done! Extracted {len(all_chunks)} total chunks from {len(pdf_files)} PDFs.")
    print(f"📄 Text output: {output_dir / 'combined_chunks.json'}")
    print(f"📊 Table output: {output_dir / 'table_chunks.json'}")


if __name__ == "__main__":
    main()
