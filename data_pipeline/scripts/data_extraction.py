import json
from pathlib import Path
import camelot
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from data_pipeline.utils.logger import get_logger

logger = get_logger(__name__)

def main():
    try:
        # --- Directory setup ---
        data_dir = Path(__file__).resolve().parents[1] / "data"
        raw_dir = data_dir / "raw"
        output_dir = data_dir / "extracted"
        output_dir.mkdir(parents=True, exist_ok=True)

        # --- Chunk configuration ---
        chunk_size = 1024
        chunk_overlap = 64
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ".", " "]
        )

        all_chunks, all_tables = [], []

        pdf_files = list(raw_dir.glob("*.pdf"))
        if not pdf_files:
            logger.warning("No PDFs found in data/raw/.")
            return

        for pdf_path in pdf_files:
            logger.info(f"Processing {pdf_path.name} ...")

            try:
                company_name = pdf_path.stem.strip().replace("_", " ")

                # --- TEXT EXTRACTION ---
                loader = PyPDFLoader(str(pdf_path))
                pages = loader.load_and_split()
                combined_text = "\n".join(
                    [p.page_content for p in pages if p.page_content.strip()]
                )

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
                    logger.info(f"Extracted {len(tables)} tables from {pdf_path.name}")
                except Exception as e:
                    logger.warning(f"Table extraction failed for {pdf_path.name}: {e}")

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
                logger.info(f"{len(documents)} chunks extracted from {pdf_path.name}")

            except Exception as e:
                logger.error(f"Error processing {pdf_path.name}: {e}", exc_info=True)

        # --- SAVE OUTPUTS ---
        (output_dir / "combined_chunks.json").write_text(
            json.dumps(all_chunks, indent=2, ensure_ascii=False)
        )
        (output_dir / "table_chunks.json").write_text(
            json.dumps(all_tables, indent=2, ensure_ascii=False)
        )

        logger.info(f"Extraction complete for {len(pdf_files)} PDFs.")
        logger.info(f"Text output → {output_dir / 'combined_chunks.json'}")
        logger.info(f"Table output → {output_dir / 'table_chunks.json'}")

        # --- Basic anomaly check ---
        if len(all_chunks) == 0:
            logger.warning("No chunks were generated — check PDF parsing or file quality.")
        if len(all_tables) == 0:
            logger.warning("No tables detected — confirm PDFs contain tabular data.")

    except Exception as e:
        logger.critical(f"Fatal error in data_extraction.py: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
