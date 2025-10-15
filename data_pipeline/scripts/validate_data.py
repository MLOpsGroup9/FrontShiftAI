import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))


import os
import json
import re
import csv
import pandas as pd
from datetime import datetime
from langdetect import detect
from pydantic import BaseModel, ValidationError

# ---------------------- 1. Define schema ---------------------- #
class HandbookChunk(BaseModel):
    text: str
    filename: str
    company: str
    chunk_id: str


# ---------------------- 2. Helper functions ---------------------- #
def is_english(text: str) -> bool:
    try:
        return detect(text) == "en"
    except:
        return False


def has_min_words(text: str, min_words: int = 30) -> bool:
    return len(text.split()) >= min_words


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"•", "-", text)
    text = re.sub(r"[\r\n]+", " ", text)
    return text.strip()


def ensure_dir(path: str):
    if not os.path.exists(path):
        os.makedirs(path)


# ---------------------- 3. Validation pipeline ---------------------- #
def validate_dataset(input_folder: str, output_folder: str, log_folder: str):
    ensure_dir(output_folder)
    ensure_dir(log_folder)

    log_path = os.path.join(log_folder, "validation_report.csv")
    with open(log_path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["filename", "valid_chunks", "invalid_chunks", "timestamp"])

        # --- Read cleaned CSV instead of JSONs ---
        cleaned_path = os.path.join(input_folder, "cleaned_chunks.csv")
        if not os.path.exists(cleaned_path):
            raise FileNotFoundError(f"{cleaned_path} not found. Run preprocess.py first.")

        df = pd.read_csv(cleaned_path)
        grouped = df.groupby("filename")

        # --- Validate each file’s chunks separately ---
        for filename, group in grouped:
            valid_chunks = []
            invalid_count = 0

            for _, row in group.iterrows():
                try:
                    chunk = HandbookChunk(
                        text=clean_text(str(row["text"])),
                        filename=str(row.get("filename", "")),
                        company=str(row.get("company", "")),
                        chunk_id=str(row.get("chunk_id", ""))
                    )

                    text = chunk.text
                    if not text or not has_min_words(text):
                        invalid_count += 1
                        continue
                    if not is_english(text):
                        invalid_count += 1
                        continue

                    valid_chunks.append(chunk.dict())

                except ValidationError:
                    invalid_count += 1
                    continue

            # Deduplicate by text
            seen = set()
            deduped = []
            for c in valid_chunks:
                if c["text"] not in seen:
                    seen.add(c["text"])
                    deduped.append(c)

            # Save one validated JSON per handbook filename
            output_path = os.path.join(output_folder, f"{filename}_validated.json")
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(deduped, f, indent=2, ensure_ascii=False)

            print(f"✅ {filename}: {len(deduped)} valid | {invalid_count} invalid")
            writer.writerow([
                filename,
                len(deduped),
                invalid_count,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ])

    print(f"\n📊 Validation summary saved to {log_path}")


# ---------------------- 4. Run as script ---------------------- #
if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # data_pipeline/
    INPUT_DIR = os.path.join(BASE_DIR, "data", "cleaned")
    OUTPUT_DIR = os.path.join(BASE_DIR, "data", "validated")
    LOG_DIR = os.path.join(BASE_DIR, "logs")

    validate_dataset(INPUT_DIR, OUTPUT_DIR, LOG_DIR)
