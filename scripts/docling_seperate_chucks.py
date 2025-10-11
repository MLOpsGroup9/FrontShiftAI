import json
import logging
import time
import re
from pathlib import Path
import pandas as pd
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, EasyOcrOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from sentence_transformers import SentenceTransformer, util
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --------------------------------------------------------
# SEMANTIC CHUNKING HELPERS
# --------------------------------------------------------

def split_by_headings(text):
    """Split text by markdown-style headings (#, ##, ###)."""
    pattern = r"(?=^#{1,3}\s)"
    sections = re.split(pattern, text, flags=re.MULTILINE)
    sections = [s.strip() for s in sections if len(s.strip()) > 30]
    return sections


def semantic_similarity_chunking(text, model, sim_threshold=0.5, max_len=1000):
    """Split text semantically, constrained by max length."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    if len(sentences) < 3:
        return [text]

    embeddings = model.encode(sentences)
    chunks, current_chunk, current_length = [], [sentences[0]], len(sentences[0])

    for i in range(1, len(sentences)):
        sim = util.cos_sim(embeddings[i-1], embeddings[i]).item()
        sent_len = len(sentences[i])

        # Split if semantic similarity drops or max length exceeded
        if sim < sim_threshold or current_length + sent_len > max_len:
            chunks.append(" ".join(current_chunk))
            current_chunk = [sentences[i]]
            current_length = sent_len
        else:
            current_chunk.append(sentences[i])
            current_length += sent_len

    chunks.append(" ".join(current_chunk))
    return [c.strip() for c in chunks if len(c.strip()) > 30]


# --------------------------------------------------------
# PDF EXTRACTION
# --------------------------------------------------------

def extract_pdf_content(pdf_path: Path, doc_converter: DocumentConverter):
    """Extract text and tables from a single PDF."""
    logger.info(f"Processing: {pdf_path.name}")

    start_time = time.time()
    conv_res = doc_converter.convert(pdf_path)
    elapsed = time.time() - start_time
    logger.info(f"Converted {pdf_path.name} in {elapsed:.2f} sec")

    doc = conv_res.document

    # Collect all text elements (ignore page numbers)
    text_fragments = []
    for item, _ in doc.iterate_items():
        text_content = getattr(item, "text", "") or getattr(item, "content", "")
        if text_content and len(text_content.strip()) > 0:
            text_fragments.append(text_content.strip())

    full_text = "\n".join(text_fragments)

    # Extract tables
    tables_data = []
    for i, table in enumerate(doc.tables, 1):
        df = table.export_to_dataframe()
        tables_data.append({
            "filename": pdf_path.name,
            "table_index": i,
            "data": df.to_dict(orient="records")
        })

    return full_text, tables_data


# --------------------------------------------------------
# MAIN PIPELINE
# --------------------------------------------------------

def main():
    data_dir = Path(__file__).resolve().parents[1] / "data"
    raw_dir = data_dir / "raw"
    output_dir = data_dir / "extracted"
    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = list(raw_dir.glob("*.pdf"))
    if not pdf_files:
        logger.warning("No PDFs found in data/raw/")
        return

    # Initialize Docling pipeline
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.ocr_options = EasyOcrOptions()
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options.do_cell_matching = True

    doc_converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
    )

    # Initialize embedding model for semantic chunking
    model = SentenceTransformer("all-MiniLM-L6-v2")

    all_texts = []
    all_tables = []
    all_semantic_chunks = []

    for pdf_path in pdf_files:
        full_text, tables_data = extract_pdf_content(pdf_path, doc_converter)
        all_tables.extend(tables_data)

        # Store raw text
        all_texts.append({
            "filename": pdf_path.name,
            "text_length": len(full_text),
            "text": full_text
        })

        # --- Hybrid chunking (headings + semantic + paragraph fallback) ---
        sections = split_by_headings(full_text)

        # Fallback: paragraph splitting
        if not sections:
            sections = re.split(r"\n{2,}", full_text)
            sections = [s.strip() for s in sections if len(s.strip()) > 100]

        # Final fallback: full text
        if not sections and len(full_text.strip()) > 50:
            sections = [full_text.strip()]

        # Semantic subchunking (max_len=1000)
        for sec in sections:
            subchunks = semantic_similarity_chunking(sec, model, max_len=1000)
            for subchunk in subchunks:
                all_semantic_chunks.append({
                    "document_name": pdf_path.stem,
                    "filename": pdf_path.name,
                    "chunk_index": len(all_semantic_chunks) + 1,
                    "chunk_length": len(subchunk),
                    "source_path": str(pdf_path),
                    "content": subchunk
                })

        logger.info(f"📄 {pdf_path.name}: {len(all_semantic_chunks)} total chunks so far.")

    # Save outputs
    (output_dir / "text_chunks.json").write_text(json.dumps(all_texts, indent=2))
    (output_dir / "table_chunks.json").write_text(json.dumps(all_tables, indent=2))
    (output_dir / "semantic_chunks.json").write_text(json.dumps(all_semantic_chunks, indent=2))

    logger.info(f"✅ Extracted text, tables, and {len(all_semantic_chunks)} semantic chunks with metadata.")


if __name__ == "__main__":
    main()
