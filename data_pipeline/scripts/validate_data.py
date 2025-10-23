"""
Comprehensive validation for processed chunks.
Reads from data/chunked/, validates schema, language, length, and metadata.
Outputs reports, valid chunks, and invalid chunk samples to data/validated/.
"""

# =====================================================
# 1. Imports
# =====================================================
import os
import json
import csv
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Set, Optional, Tuple
from langdetect import detect
from pydantic import BaseModel, Field, validator, ValidationError

# =====================================================
# 2. Path setup
# =====================================================
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

CHUNKS_DIR = DATA_DIR / "chunked"            # input from chunker.py
VALIDATED_DIR = DATA_DIR / "validated"       # output reports + valid chunks
REPORTS_DIR = VALIDATED_DIR / "reports"
LOG_DIR = BASE_DIR / "logs" / "validation"

# Ensure directories exist
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# =====================================================
# 3. Logging setup
# =====================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "validation.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# =====================================================
# 4. Pydantic Schema Definitions
# =====================================================
class ChunkMetadataModel(BaseModel):
    doc_id: str
    company: str
    source_url: Optional[str]
    org: str
    industry: str
    doc_type: str
    doc_title: str
    doc_year: str
    section_path: str
    section_title: str
    section_index: Optional[str]
    chunk_id: str
    char_span: Tuple[int, int]
    sentence_count: int = Field(..., ge=0)
    content_type: str
    prev_chunk_id: Optional[str]
    next_chunk_id: Optional[str]
    keywords: List[str]
    policy_tags: List[str]
    hash_64: str
    created_at: str
    token_count: Optional[int] = Field(default=None, ge=0)

    @validator("created_at")
    def validate_timestamp(cls, v):
        try:
            datetime.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError("Invalid ISO timestamp format")

    @validator("industry")
    def validate_industry(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError("Industry field missing or invalid")
        return v.strip()


class ChunkModel(BaseModel):
    text: str = Field(..., min_length=50)
    metadata: ChunkMetadataModel

    @validator("text")
    def ensure_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Text is empty or whitespace only")
        return v

# =====================================================
# 5. Helper functions
# =====================================================
def is_english(text: str) -> bool:
    """Detect if text is English."""
    try:
        return detect(text) == "en"
    except Exception:
        return False


def count_words(text: str) -> int:
    return len(text.split())


def validate_chunk_structure(chunk: Dict[str, Any], filename: str) -> List[str]:
    """Apply schema + semantic validations."""
    issues = []

    # --- Schema validation ---
    try:
        validated = ChunkModel(**chunk)
    except ValidationError as e:
        issues.append(f"SchemaError: {e.errors()}")
        return issues

    meta = validated.metadata
    text = validated.text

    # --- Core content checks ---
    if count_words(text) < 30:
        issues.append("TooShort(<30 words)")

    if not is_english(text):
        issues.append("NonEnglish")

    if not meta.company.strip():
        issues.append("MissingCompany")

    # --- Company consistency check ---
    expected_company_part = filename.split("_")[1] if "_" in filename else ""
    if expected_company_part and expected_company_part.lower() not in meta.company.lower().replace(" ", "_"):
        issues.append(f"CompanyMismatch({meta.company})")

    if not meta.industry.strip():
        issues.append("MissingIndustry")

    if len(meta.hash_64.strip()) < 8:
        issues.append("InvalidHash")

    if not meta.doc_id or not meta.chunk_id:
        issues.append("MissingIdentifiers")

    return issues

# =====================================================
# 6. Validation Pipeline
# =====================================================
def validate_all_chunks():
    """Validate all JSONL chunk files and produce reports."""
    jsonl_files = list(CHUNKS_DIR.glob("*.jsonl"))
    if not jsonl_files:
        logger.warning(f"No chunk files found in {CHUNKS_DIR}/")
        return

    report_csv = REPORTS_DIR / "validation_report.csv"
    summary_json = REPORTS_DIR / "validation_summary.json"
    invalid_jsonl = VALIDATED_DIR  / "invalid_chunks.jsonl"
    valid_jsonl = VALIDATED_DIR  / "valid_chunks.jsonl"

    seen_hashes: Set[str] = set()
    total_valid, total_invalid = 0, 0

    with open(report_csv, "w", newline="") as csvfile, \
         open(invalid_jsonl, "w", encoding="utf-8") as invalid_out, \
         open(valid_jsonl, "w", encoding="utf-8") as valid_out:

        writer = csv.writer(csvfile)
        writer.writerow(["filename", "total", "valid", "invalid", "issues", "timestamp"])

        for fpath in jsonl_files:
            file_valid, file_invalid = 0, 0
            file_issues: List[str] = []

            logger.info(f"🔍 Validating {fpath.name}")

            with open(fpath, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        file_invalid += 1
                        file_issues.append("JSONDecodeError")
                        continue

                    issues = validate_chunk_structure(obj, fpath.name)

                    # --- Duplicate hash check ---
                    h = obj.get("metadata", {}).get("hash_64", "")
                    if h in seen_hashes:
                        issues.append("DuplicateHash")
                    else:
                        seen_hashes.add(h)

                    if issues:
                        file_invalid += 1
                        file_issues.extend(issues)
                        invalid_out.write(json.dumps({
                            "file": fpath.name,
                            "issues": issues,
                            "metadata": obj.get("metadata", {}),
                            "preview": obj.get("text", "")[:150]
                        }) + "\n")
                    else:
                        file_valid += 1
                        valid_out.write(json.dumps(obj) + "\n")

            total_valid += file_valid
            total_invalid += file_invalid

            writer.writerow([
                fpath.name,
                file_valid + file_invalid,
                file_valid,
                file_invalid,
                "; ".join(sorted(set(file_issues)))[:200],
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ])

            logger.info(f"✅ {fpath.name}: {file_valid} valid | {file_invalid} invalid")

    # --- Summary ---
    summary = {
        "timestamp": datetime.now().isoformat(),
        "files_processed": len(jsonl_files),
        "valid_chunks": total_valid,
        "invalid_chunks": total_invalid,
        "valid_ratio": round(total_valid / (total_valid + total_invalid), 3)
        if (total_valid + total_invalid) > 0 else 0,
    }

    with open(summary_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    logger.info("📊 Validation summary saved to %s", summary_json)
    logger.info("🧾 Invalid chunks written to %s", invalid_jsonl)
    logger.info("✅ Valid chunks written to %s", valid_jsonl)
    logger.info("✔ Total valid chunks: %s", total_valid)
    logger.info("❌ Total invalid chunks: %s", total_invalid)
    logger.info("=" * 70)

# =====================================================
# 7. Entry point
# =====================================================
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("Chunk Validation Pipeline")
    print("=" * 70 + "\n")

    validate_all_chunks()

    print("\n" + "=" * 70)
    print("Validation Complete!")
    print("=" * 70 + "\n")
