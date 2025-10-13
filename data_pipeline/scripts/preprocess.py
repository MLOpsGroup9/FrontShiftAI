import json
import pandas as pd
from pathlib import Path


def load_extracted_data():
    """Load JSON outputs from the extraction step (combined + tables)."""
    # Resolve project root dynamically
    # __file__ = data_pipeline/scripts/preprocess.py
    project_root = Path(__file__).resolve().parents[1]  # data_pipeline/
    extracted_dir = project_root / "data" / "extracted"

    combined_path = extracted_dir / "combined_chunks.json"
    tables_path = extracted_dir / "table_chunks.json"

    if not combined_path.exists():
        raise FileNotFoundError(f"❌ {combined_path} not found. Run data_extraction.py first.")
    if not tables_path.exists():
        raise FileNotFoundError(f"❌ {tables_path} not found. Run data_extraction.py first.")

    with open(combined_path, "r", encoding="utf-8") as f:
        combined = json.load(f)
    with open(tables_path, "r", encoding="utf-8") as f:
        tables = json.load(f)

    print(f"✅ Loaded extracted data from {extracted_dir}")
    return combined, tables


def clean_chunks(chunks):
    """Clean text and normalize metadata from extracted chunks."""
    cleaned = []
    for c in chunks:
        text = c["text"].strip().replace("\n", " ")
        text = " ".join(text.split())  # normalize spaces
        meta = c.get("metadata", {})
        meta["filename"] = meta.get("filename", "").strip()
        cleaned.append({
            "text": text,
            "metadata": meta
        })
    return cleaned


def convert_to_dataframe(cleaned_chunks):
    """Convert list of cleaned chunks into a structured DataFrame."""
    df = pd.DataFrame([
        {
            "filename": c["metadata"].get("filename", ""),
            "company": c["metadata"].get("company", ""),
            "chunk_id": c["metadata"].get("chunk_id", ""),
            "text": c["text"]
        }
        for c in cleaned_chunks
    ])
    print(f"📊 Converted {len(df)} cleaned chunks into DataFrame")
    return df


def save_cleaned(df):
    """Save cleaned and structured data to CSV inside data/cleaned/."""
    project_root = Path(__file__).resolve().parents[1]
    out_dir = project_root / "data" / "cleaned"
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / "cleaned_chunks.csv"

    df.to_csv(output_path, index=False, encoding="utf-8")
    print(f"✅ Cleaned data saved to {output_path}")
    return output_path


def main():
    """Main preprocessing pipeline."""
    print("🔄 Starting preprocessing pipeline...")

    combined, tables = load_extracted_data()
    cleaned_chunks = clean_chunks(combined)
    df = convert_to_dataframe(cleaned_chunks)
    save_cleaned(df)

    print("\n🎉 Preprocessing completed successfully!")


if __name__ == "__main__":
    main()
