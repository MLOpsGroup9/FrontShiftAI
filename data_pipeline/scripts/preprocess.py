import json
import pandas as pd
from pathlib import Path


def load_extracted_data(extracted_dir=None):
    """Load JSON outputs from the extraction step."""
    project_root = Path(__file__).resolve().parents[1]
    data_dir = project_root / "data"
    extracted_dir = extracted_dir or (data_dir / "extracted")

    combined_path = Path(extracted_dir) / "combined_chunks.json"
    tables_path = Path(extracted_dir) / "table_chunks.json"

    if not combined_path.exists():
        raise FileNotFoundError(f"{combined_path} not found.")
    if not tables_path.exists():
        raise FileNotFoundError(f"{tables_path} not found.")

    with open(combined_path, "r") as f:
        combined = json.load(f)
    with open(tables_path, "r") as f:
        tables = json.load(f)

    return combined, tables


def clean_chunks(chunks):
    """Clean text and normalize metadata."""
    cleaned = []
    for c in chunks:
        text = c["text"].strip().replace("\n", " ")
        text = " ".join(text.split())  # Normalize spaces
        meta = c.get("metadata", {})
        meta["filename"] = meta.get("filename", "").strip()
        cleaned.append({
            "text": text,
            "metadata": meta
        })
    return cleaned


def convert_to_dataframe(cleaned_chunks):
    """Convert list of cleaned chunks into a DataFrame."""
    df = pd.DataFrame([
        {
            "filename": c["metadata"].get("filename", ""),
            "company": c["metadata"].get("company", ""),
            "chunk_id": c["metadata"].get("chunk_id", ""),
            "text": c["text"]
        }
        for c in cleaned_chunks
    ])
    return df


def save_cleaned(df, out_dir=None):
    """Save cleaned and structured data to CSV."""
    project_root = Path(__file__).resolve().parents[1]
    data_dir = project_root / "data"
    out_dir = out_dir or (data_dir / "cleaned")

    Path(out_dir).mkdir(parents=True, exist_ok=True)
    output_path = Path(out_dir) / "cleaned_chunks.csv"
    df.to_csv(output_path, index=False)
    print(f"✅ Cleaned data saved to {output_path}")
    return output_path


def main():
    """Main preprocessing pipeline."""
    combined, tables = load_extracted_data()
    cleaned_chunks = clean_chunks(combined)
    df = convert_to_dataframe(cleaned_chunks)
    save_cleaned(df)


if __name__ == "__main__":
    main()
