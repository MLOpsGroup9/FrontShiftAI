import json
import pandas as pd
from pathlib import Path
from data_pipeline.utils.logger import get_logger

logger = get_logger(__name__)

def load_extracted_data():
    """Load JSON outputs from the extraction step (combined + tables)."""
    project_root = Path(__file__).resolve().parents[1]
    extracted_dir = project_root / "data" / "extracted"

    combined_path = extracted_dir / "combined_chunks.json"
    tables_path = extracted_dir / "table_chunks.json"

    if not combined_path.exists():
        msg = f"{combined_path} not found. Run data_extraction.py first."
        logger.error(msg)
        raise FileNotFoundError(msg)
    if not tables_path.exists():
        msg = f"{tables_path} not found. Run data_extraction.py first."
        logger.error(msg)
        raise FileNotFoundError(msg)

    with open(combined_path, "r", encoding="utf-8") as f:
        combined = json.load(f)
    with open(tables_path, "r", encoding="utf-8") as f:
        tables = json.load(f)

    logger.info(f"Loaded extracted data from {extracted_dir}")
    return combined, tables


def clean_chunks(chunks):
    """Clean text and normalize metadata from extracted chunks."""
    cleaned = []
    for c in chunks:
        text = c["text"].strip().replace("\n", " ")
        text = " ".join(text.split())
        meta = c.get("metadata", {})
        meta["filename"] = meta.get("filename", "").strip()
        cleaned.append({
            "text": text,
            "metadata": meta
        })
    logger.info(f"Cleaned {len(cleaned)} chunks.")
    return cleaned


def convert_to_dataframe(cleaned_chunks):
    """Convert list of cleaned chunks into a structured DataFrame."""
    if not cleaned_chunks:
        logger.warning("No cleaned chunks found — possible extraction issue.")
    df = pd.DataFrame([
        {
            "filename": c["metadata"].get("filename", ""),
            "company": c["metadata"].get("company", ""),
            "chunk_id": c["metadata"].get("chunk_id", ""),
            "text": c["text"]
        }
        for c in cleaned_chunks
    ])
    logger.info(f"Converted {len(df)} cleaned chunks into DataFrame.")
    return df


def save_cleaned(df, out_dir=None):
    project_root = Path(__file__).resolve().parents[1]
    out_dir = project_root / "data" / "cleaned" if out_dir is None else Path(out_dir)

    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / "cleaned_chunks.csv"
    df.to_csv(output_path, index=False, encoding="utf-8")
    logger.info(f"Cleaned data saved to {output_path}")

    # Anomaly check: empty DataFrame
    if df.empty:
        logger.warning("Cleaned CSV is empty. Check extraction step for issues.")
    return output_path


def main():
    """Main preprocessing pipeline."""
    logger.info("Starting preprocessing pipeline...")

    try:
        combined, tables = load_extracted_data()
        cleaned_chunks = clean_chunks(combined)
        df = convert_to_dataframe(cleaned_chunks)
        save_cleaned(df)
        logger.info("Preprocessing completed successfully!")

    except Exception as e:
        logger.error(f"Error in preprocessing pipeline: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
