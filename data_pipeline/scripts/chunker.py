"""
Chunk generation module: token-based chunking without validation or scoring.
Reads cleaned JSON from data/cleaned/, outputs chunks to data/chunked/chunks/.
"""

import os
import sys
import json
import re
import logging
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any, Set
from dataclasses import dataclass, asdict
from collections import Counter
from datetime import datetime
from tqdm import tqdm
import tiktoken
from dotenv import load_dotenv

# =====================================================
# Setup
# =====================================================
load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

CLEANED_DATA_DIR = DATA_DIR / "cleaned"
CHUNKED_DATA_DIR = DATA_DIR / "chunked"
(LOGS_DIR / "preprocessing").mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "preprocessing" / "chunker.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# =====================================================
# Config
# =====================================================
TARGET_TOKENS = 1024
OVERLAP_TOKENS = 64

POLICY_PATTERNS = {
    'FMLA', 'CFRA', 'ADA', 'EEOC', 'OSHA', 'FLSA', 'HIPAA', 'TITLE VII',
    'HARASSMENT', 'PTO', 'SICK LEAVE', 'OVERTIME', 'MEAL', 'REST',
    'I-9', 'E-VERIFY', 'COBRA', 'ERISA', 'USERRA', 'WARN', 'SOX'
}

ABBREV_PATTERN = re.compile(r'\b(Mr|Mrs|Ms|Dr|Inc|Ltd|Co|Corp|Sr|Jr)\.')
SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+')

# =====================================================
# Data Models
# =====================================================
@dataclass
class ChunkMetadata:
    """Chunk metadata schema."""
    doc_id: str
    company: str
    source_url: str
    org: str
    industry: str
    doc_type: str
    doc_title: str
    doc_year: str
    section_path: str
    section_title: str
    section_index: str
    chunk_id: str
    char_span: Tuple[int, int]
    sentence_count: int
    content_type: str
    prev_chunk_id: Optional[str]
    next_chunk_id: Optional[str]
    keywords: List[str]
    policy_tags: List[str]
    hash_64: str
    created_at: str
    token_count: int = 0


@dataclass
class Chunk:
    text: str
    metadata: ChunkMetadata

    def to_dict(self) -> Dict:
        return {'text': self.text, 'metadata': asdict(self.metadata)}


# =====================================================
# Chunk Generator
# =====================================================
class ChunkGenerator:
    """Simple token-based chunk generator (1024 tokens, 64 overlap)."""

    def __init__(
        self,
        input_dir: str = CLEANED_DATA_DIR,
        output_dir: str = CHUNKED_DATA_DIR,
        tokenizer_name: str = "cl100k_base"
    ):
        self.input_dir = input_dir
        self.output_dir = os.path.join(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)

        try:
            self.tokenizer = tiktoken.get_encoding(tokenizer_name)
            logger.info(f"Loaded tokenizer: {tokenizer_name}")
        except Exception as e:
            logger.warning(f"Failed to load {tokenizer_name}, defaulting to cl100k_base: {e}")
            self.tokenizer = tiktoken.get_encoding("cl100k_base")

        self.stats = {'total_docs': 0, 'total_chunks': 0}
        self.seen_hashes: Set[str] = set()

    # ------------------------------
    # Helper Functions
    # ------------------------------
    def count_tokens(self, text: str) -> int:
        try:
            return len(self.tokenizer.encode(text))
        except Exception:
            return len(text) // 4

    def split_into_sentences(self, text: str) -> List[str]:
        text = ABBREV_PATTERN.sub(r'\1@PERIOD@', text)
        return [s.replace('@PERIOD@', '.') for s in SENTENCE_SPLIT.split(text) if s.strip()]

    def extract_company_name(self, filename: str) -> str:
        """Extract company name from filename."""
        clean_fn = filename.replace('_cleaned.json', '').replace('.json', '').replace('.md', '')
        parts = re.split(r'[_\-]+', clean_fn)
        if len(parts) > 1:
            parts = parts[1:]
        filtered = [w for w in parts if w.lower() not in {
            'handbook', 'policy', 'manual', 'guide', 'document', 'employee',
            'team', 'member', 'updated', 'effective', 'md', 'pdf'
        }]
        return ' '.join(w.capitalize() for w in filtered if w).strip() or "Unknown Company"

    def compute_simhash(self, text: str) -> str:
        """Simple simhash for deduplication."""
        tokens = text.lower().split()
        if not tokens:
            return "0" * 16
        v = [0] * 64
        for token in tokens:
            h = int(hashlib.md5(token.encode()).hexdigest(), 16)
            for i in range(64):
                v[i] += 1 if h & (1 << i) else -1
        fingerprint = sum(1 << i for i in range(64) if v[i] > 0)
        return format(fingerprint, '016x')

    def extract_keywords(self, text: str, top_n: int = 5) -> List[str]:
        STOPWORDS = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
            'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are',
            'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did'
        }
        words = [w.lower() for w in text.split() if len(w) > 3 and w.isalpha() and w.lower() not in STOPWORDS]
        return [word for word, _ in Counter(words).most_common(top_n)]

    def detect_policy_tags(self, text: str) -> List[str]:
        return sorted(tag for tag in POLICY_PATTERNS if tag in text.upper())

    # ------------------------------
    # Chunk Logic
    # ------------------------------
    def create_token_based_chunks(self, text: str) -> List[str]:
        """Create fixed-size chunks (1024 tokens, 64 overlap)."""
        sentences = self.split_into_sentences(text)
        chunks = []
        current_chunk = []
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)
            if current_tokens + sentence_tokens > TARGET_TOKENS and current_chunk:
                chunk_text = ' '.join(current_chunk)
                chunks.append(chunk_text)

                # overlap by last 64 tokens
                overlap_chunk = []
                total_overlap = 0
                for s in reversed(current_chunk):
                    s_tokens = self.count_tokens(s)
                    if total_overlap + s_tokens <= OVERLAP_TOKENS:
                        overlap_chunk.insert(0, s)
                        total_overlap += s_tokens
                    else:
                        break
                current_chunk = overlap_chunk + [sentence]
                current_tokens = sum(self.count_tokens(s) for s in current_chunk)
            else:
                current_chunk.append(sentence)
                current_tokens += sentence_tokens

        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks

    # ------------------------------
    # Metadata Creation
    # ------------------------------
    def create_metadata(
        self,
        text: str,
        chunk_id: str,
        filename: str,
        char_span: Tuple[int, int],
        prev_chunk_id: Optional[str],
        next_chunk_id: Optional[str]
    ) -> ChunkMetadata:
        company = self.extract_company_name(filename)
        token_count = self.count_tokens(text)
        keywords = self.extract_keywords(text)
        policy_tags = self.detect_policy_tags(text)
        simhash = self.compute_simhash(text)

        year_match = re.search(r'20\d{2}', filename)
        doc_year = year_match.group() if year_match else "unknown"

        return ChunkMetadata(
            doc_id=filename.replace('_cleaned.json', ''),
            company=company,
            source_url="",
            org="General Business",
            industry="HR/Employee",
            doc_type="handbook",
            doc_title=company,
            doc_year=doc_year,
            section_path="Unknown",
            section_title="Unknown",
            section_index="",
            chunk_id=chunk_id,
            char_span=char_span,
            sentence_count=len(self.split_into_sentences(text)),
            content_type='text',
            prev_chunk_id=prev_chunk_id,
            next_chunk_id=next_chunk_id,
            keywords=keywords,
            policy_tags=policy_tags,
            hash_64=simhash,
            created_at=datetime.now().isoformat(),
            token_count=token_count
        )

    # ------------------------------
    # File Processing
    # ------------------------------
    def process_cleaned_file(self, json_path: str) -> Optional[str]:
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                cleaned_data = json.load(f)

            filename = cleaned_data.get('filename', os.path.basename(json_path))
            text = cleaned_data.get('text', '')

            if not text or len(text.strip()) < 100:
                logger.warning(f"Skipped short file: {filename}")
                return None

            chunk_texts = self.create_token_based_chunks(text)
            chunks = []

            char_offset = 0
            for idx, chunk_text in enumerate(chunk_texts):
                chunk_id = f"{filename.replace('_cleaned.json', '')}_chunk_{idx:04d}"
                prev_chunk_id = f"{filename.replace('_cleaned.json', '')}_chunk_{idx-1:04d}" if idx > 0 else None
                next_chunk_id = f"{filename.replace('_cleaned.json', '')}_chunk_{idx+1:04d}" if idx < len(chunk_texts) - 1 else None

                metadata = self.create_metadata(
                    text=chunk_text,
                    chunk_id=chunk_id,
                    filename=filename,
                    char_span=(char_offset, char_offset + len(chunk_text)),
                    prev_chunk_id=prev_chunk_id,
                    next_chunk_id=next_chunk_id
                )
                chunks.append(Chunk(text=chunk_text, metadata=metadata))
                char_offset += len(chunk_text)

            # Save JSONL
            base_name = os.path.splitext(os.path.basename(json_path))[0].replace('_cleaned', '')
            output_path = os.path.join(self.output_dir, f"{base_name}_chunks.jsonl")
            with open(output_path, 'w', encoding='utf-8') as f:
                for chunk in chunks:
                    f.write(json.dumps(chunk.to_dict(), ensure_ascii=False) + '\n')

            self.stats['total_chunks'] += len(chunks)
            logger.info(f"✅ {filename}: {len(chunks)} chunks → {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Error processing {json_path}: {e}", exc_info=True)
            return None

    # ------------------------------
    # Process All Files
    # ------------------------------
    def process_all(self) -> Dict[str, Any]:
        json_files = list(Path(self.input_dir).glob("*_cleaned.json"))
        if not json_files:
            logger.warning(f"No cleaned files found in {self.input_dir}")
            return self.stats

        logger.info(f"Found {len(json_files)} files to process")
        self.stats['total_docs'] = len(json_files)

        for json_path in tqdm(json_files, desc="Generating chunks"):
            self.process_cleaned_file(str(json_path))

        logger.info(f"Total chunks created: {self.stats['total_chunks']}")
        return self.stats


# =====================================================
# Entry Point
# =====================================================
def main():
    print("\n" + "="*70)
    print("Chunk Generation Pipeline (1024 tokens, 64 overlap)")
    print("="*70 + "\n")

    generator = ChunkGenerator()
    stats = generator.process_all()

    print("\n" + "="*70)
    print("Chunk Generation Complete!")
    print("="*70)
    print(f"Processed: {stats['total_docs']} documents")
    print(f"Generated chunks: {stats['total_chunks']}")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
