"""
Token-based text preprocessing with quality scoring and validation.
Chunks documents using tiktoken, detects sections, tags policies, scores quality.
"""

import json
import os
import sys
from typing import List, Dict, Optional, Tuple, Any, Set
from dataclasses import dataclass, field, asdict
import re
from tqdm import tqdm
import logging
from pathlib import Path
import shutil
from datetime import datetime
import hashlib
from collections import Counter
import tiktoken

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config import (
    EXTRACTED_DATA_DIR, 
    CLEANED_DATA_DIR, 
    VALIDATED_DATA_DIR,
    LOGS_DIR
)

# Setup logging
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(os.path.join(LOGS_DIR, 'preprocessing'), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, 'preprocess.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Policy patterns for HR compliance tagging  
POLICY_PATTERNS = {
    'FMLA', 'CFRA', 'ADA', 'EEOC', 'OSHA', 'FLSA', 'HIPAA', 'TITLE VII',
    'HARASSMENT', 'PTO', 'SICK LEAVE', 'OVERTIME', 'MEAL', 'REST',
    'I-9', 'E-VERIFY', 'COBRA', 'ERISA', 'USERRA', 'WARN', 'SOX'
}

# Precompiled regex patterns
ABBREV_PATTERN = re.compile(r'\b(Mr|Mrs|Ms|Dr|Inc|Ltd|Co|Corp|Sr|Jr)\.')
SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+')


@dataclass
class Section:
    """Section/heading information with hierarchy."""
    title: str
    level: int
    index: str
    start_page: int
    parent_path: str = ""
    
    def get_breadcrumb(self, depth: int = 2) -> str:
        """Get section breadcrumb path."""
        parts = [p for p in [self.parent_path, self.title] if p]
        return ' › '.join(parts[-depth:]) if parts else self.title


@dataclass  
class ChunkMetadata:
    """Comprehensive chunk metadata schema."""
    # Required fields
    doc_id: str
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
    
    # Optional fields
    token_count: int = 0
    overlap_with_prev: int = 0
    page_number: Optional[int] = None
    has_tables: bool = False
    has_images: bool = False
    quality_score: float = 0.0
    context_preview_prev: str = ""
    context_preview_next: str = ""


@dataclass
class Chunk:
    """Enhanced chunk with full metadata."""
    text: str
    metadata: ChunkMetadata
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        meta_dict = asdict(self.metadata)
        # Convert tuple to list for JSON
        if 'char_span' in meta_dict:
            meta_dict['char_span'] = list(meta_dict['char_span'])
        return {
            'chunk_id': self.metadata.chunk_id,
            'text': self.text,
            'metadata': meta_dict
        }


class ProductionPreprocessor:
    """Production text preprocessing with token-based chunking and quality scoring."""
    
    def __init__(
        self,
        tokenizer_name: str = "cl100k_base",
        target_tokens: int = 220,
        hard_max_tokens: int = 320,
        overlap_ratio: float = 0.12,
        input_dir: str = EXTRACTED_DATA_DIR,
        output_dir: str = CLEANED_DATA_DIR,
        validated_dir: str = VALIDATED_DATA_DIR,
        min_chars: int = 180,
        min_words: int = 50,
        quality_threshold: float = 0.55
    ):
        # Configuration
        self.target_tokens = target_tokens
        self.hard_max_tokens = hard_max_tokens
        self.overlap_ratio = overlap_ratio
        self.min_chars = min_chars
        self.min_words = min_words
        self.quality_threshold = quality_threshold
        
        # Directories
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.validated_dir = validated_dir
        
        # Initialize tokenizer
        try:
            self.tokenizer = tiktoken.get_encoding(tokenizer_name)
            logger.info(f"Loaded tokenizer: {tokenizer_name}")
        except Exception as e:
            logger.warning(f"Failed to load {tokenizer_name}, using cl100k_base: {e}")
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
        # Create directories
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(validated_dir, "chunks"), exist_ok=True)
        os.makedirs(os.path.join(LOGS_DIR, 'preprocessing'), exist_ok=True)
        
        # Section detection patterns
        self.section_patterns = {
            'numbered': re.compile(r'^(\d+(?:\.\d+)*)\s+([A-Z].+)', re.MULTILINE),
            'allcaps': re.compile(r'^[A-Z0-9][A-Z0-9\s&/\-]{3,}$', re.MULTILINE),
        }
        
        # Statistics
        self.stats = {
            'total_docs': 0,
            'total_pages': 0,
            'total_chunks': 0,
            'rejected_chunks': 0,
            'merged_chunks': 0,
            'split_chunks': 0,
            'avg_quality_score': 0.0,
        }
        
        # Chunk hash registry for deduplication
        self.seen_hashes: Set[str] = set()
    
    def normalize_text(self, text: str) -> str:
        """Normalize text: fix Unicode, bullets, whitespace, remove page numbers and TOC leader dots."""
        if not text:
            return ""
        
        # Fix Unicode issues
        text = text.replace('\u200b', '')  # Zero-width space
        text = text.replace('\ufeff', '')  # BOM
        text = text.replace('\xa0', ' ')   # Non-breaking space
        
        # Normalize bullets
        bullet_chars = ['•', '◦', '▪', '▫', '–', '—']
        for bullet in bullet_chars:
            text = text.replace(bullet, '-')
        
        # Dehyphenate line breaks (word- \n breaks → wordbreaks)
        text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
        
        # Normalize whitespace
        text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces/tabs to single space
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Multiple newlines to double
        
        # Remove standalone page numbers
        text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*Page \d+\s*$', '', text, flags=re.MULTILINE)
        
        # Remove Table of Contents leader dots (e.g., "Title ........... 5")
        # Handles: regular periods (...), Unicode ellipsis (…), and other leader characters
        # Pattern 1: Multiple periods/dots
        text = re.sub(r'\.{3,}\s*\d*', '', text)
        # Pattern 2: Unicode ellipsis (U+2026) - single or repeated
        text = re.sub(r'…+\s*\d*', '', text)
        # Pattern 3: Mixed dots and ellipsis
        text = re.sub(r'[.…]{3,}\s*\d*', '', text)
        # Pattern 4: Cleanup trailing dot+number patterns (e.g., ".5", "..6")
        text = re.sub(r'\.+\d+\s*$', '', text, flags=re.MULTILINE)
        # Pattern 5: Standalone dots at end of lines
        text = re.sub(r'\s+\.+\s*$', '', text, flags=re.MULTILINE)
        
        return text.strip()
    
    def detect_sections(self, pages_data: Dict) -> List[Section]:
        """Detect numbered and ALL-CAPS sections, build hierarchy."""
        sections = []
        section_stack = []  # Track hierarchy
        
        for page_num, page_data in sorted(pages_data.items(), key=lambda x: int(x[0])):
            text = page_data.get('text', '')
            if not text:
                continue
            
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check for numbered sections (1.2.3 Title)
                match = self.section_patterns['numbered'].match(line)
                if match:
                    index = match.group(1)
                    title = match.group(2).strip()
                    level = index.count('.') + 1
                    
                    # Update section stack
                    while section_stack and section_stack[-1].level >= level:
                        section_stack.pop()
                    
                    parent_path = ' › '.join([s.title for s in section_stack])
                    
                    section = Section(
                        title=title,
                        level=level,
                        index=index,
                        start_page=int(page_num),
                        parent_path=parent_path
                    )
                    sections.append(section)
                    section_stack.append(section)
                    continue
                
                # Check for ALL CAPS sections
                if self.section_patterns['allcaps'].match(line) and len(line) > 5:
                    # Treat as level 1 section
                    level = 1
                    
                    # Clear stack for top-level
                    section_stack = []
                    
                    section = Section(
                        title=line,
                        level=level,
                        index="",
                        start_page=int(page_num),
                        parent_path=""
                    )
                    sections.append(section)
                    section_stack.append(section)
        
        logger.info(f"Detected {len(sections)} sections")
        return sections
    
    def count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken."""
        try:
            return len(self.tokenizer.encode(text))
        except:
            # Fallback: estimate 1 token ≈ 4 chars
            return len(text) // 4
    
    def split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences with abbreviation handling."""
        # Protect abbreviations in one pass
        text = ABBREV_PATTERN.sub(r'\1@PERIOD@', text)
        # Split and restore
        return [s.replace('@PERIOD@', '.') for s in SENTENCE_SPLIT.split(text) if s.strip()]
    
    def create_token_based_chunks(self, text: str, section: Optional[Section] = None, page_num: int = 1) -> List[str]:
        """Create token-based chunks with overlap (target: 220, max: 320, overlap: 12%)."""
        sentences = self.split_into_sentences(text)
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        overlap_tokens = int(self.target_tokens * self.overlap_ratio)
        
        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)
            
            # If adding this sentence exceeds target
            if current_tokens + sentence_tokens > self.target_tokens and current_chunk:
                # Save current chunk
                chunk_text = ' '.join(current_chunk)
                chunks.append(chunk_text)
                
                # Overlap: take last N sentences that fit
                overlap_idx = next(
                    (i for i in range(len(current_chunk) - 1, -1, -1)
                     if sum(self.count_tokens(s) for s in current_chunk[i:]) <= overlap_tokens),
                    len(current_chunk)
                )
                current_chunk = current_chunk[overlap_idx:] + [sentence]
                current_tokens = sum(self.count_tokens(s) for s in current_chunk)
            else:
                current_chunk.append(sentence)
                current_tokens += sentence_tokens
            
            # Hard limit check - split if exceeds hard max
            if current_tokens > self.hard_max_tokens:
                chunk_text = ' '.join(current_chunk)
                chunks.append(chunk_text)
                current_chunk = []
                current_tokens = 0
        
        # Add remaining
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append(chunk_text)
        
        return chunks
    
    def detect_policy_tags(self, text: str) -> List[str]:
        """Detect HR policy mentions (FMLA, OSHA, etc.)."""
        return sorted(tag for tag in POLICY_PATTERNS if tag in text.upper())
    
    def calculate_quality_score(self, text: str, metadata: Dict) -> float:
        """Calculate 4-factor quality score: informativeness, cohesion, cleanliness, size fit."""
        if not text:
            return 0.0
        
        scores = {}
        
        # 1. Informativeness (35%)
        words = text.split()
        if not words:
            return 0.0
        
        # Count meaningful words (3+ chars, alphanumeric)
        meaningful_words = [w for w in words if len(w) >= 3 and any(c.isalnum() for c in w)]
        info_ratio = len(meaningful_words) / len(words) if words else 0
        scores['informativeness'] = min(info_ratio * 1.2, 1.0)  # Boost and cap
        
        # 2. Cohesion (25%)
        sentences = self.split_into_sentences(text)
        if len(sentences) >= 2:
            # Simple cohesion: check for transition words
            transitions = ['however', 'therefore', 'additionally', 'furthermore', 'moreover', 'also']
            transition_count = sum(1 for s in sentences if any(t in s.lower() for t in transitions))
            cohesion = min((transition_count / len(sentences)) * 2, 1.0)
        else:
            cohesion = 0.7  # Single sentence gets neutral score
        scores['cohesion'] = cohesion
        
        # 3. Cleanliness (20%)
        # Check for excessive special chars
        special_chars = len([c for c in text if not c.isalnum() and not c.isspace()])
        cleanliness = max(1.0 - (special_chars / len(text)), 0.3)
        scores['cleanliness'] = cleanliness
        
        # 4. Size fit (20%)
        token_count = metadata.get('token_count', self.count_tokens(text))
        if self.target_tokens * 0.8 <= token_count <= self.target_tokens * 1.2:
            size_score = 1.0
        elif token_count < self.target_tokens * 0.5:
            size_score = 0.5
        elif token_count > self.hard_max_tokens:
            size_score = 0.4
        else:
            size_score = 0.8
        scores['size_fit'] = size_score
        
        # Weighted sum
        total_score = (
            scores['informativeness'] * 0.35 +
            scores['cohesion'] * 0.25 +
            scores['cleanliness'] * 0.20 +
            scores['size_fit'] * 0.20
        )
        
        return round(total_score, 3)
    
    def compute_simhash(self, text: str, hash_bits: int = 64) -> str:
        """Compute simhash for deduplication."""
        # Simple simhash implementation
        tokens = text.lower().split()
        if not tokens:
            return "0" * 16
        
        # Create feature hashes
        v = [0] * hash_bits
        for token in tokens:
            # Hash token
            h = int(hashlib.md5(token.encode()).hexdigest(), 16)
            for i in range(hash_bits):
                if h & (1 << i):
                    v[i] += 1
                else:
                    v[i] -= 1
        
        # Generate fingerprint
        fingerprint = 0
        for i in range(hash_bits):
            if v[i] > 0:
                fingerprint |= (1 << i)
        
        return format(fingerprint, '016x')
    
    def is_duplicate(self, simhash: str, threshold: float = 0.92) -> bool:
        """Check if chunk is duplicate using simhash."""
        if simhash in self.seen_hashes:
            return True
        
        # Check Hamming distance with existing hashes
        # (Simplified: exact match only for now)
        self.seen_hashes.add(simhash)
        return False
    
    def validate_chunk(self, text: str, metadata: Dict, quality_score: float) -> Tuple[bool, List[str]]:
        """Validate chunk: length, word count, tokens, quality, completeness."""
        errors = []
        
        # Check minimum length
        if len(text) < self.min_chars:
            errors.append(f"Below min chars: {len(text)} < {self.min_chars}")
        
        # Check minimum words
        word_count = len(text.split())
        if word_count < self.min_words:
            errors.append(f"Below min words: {word_count} < {self.min_words}")
        
        # Check token count
        token_count = metadata.get('token_count', 0)
        if token_count > self.hard_max_tokens:
            errors.append(f"Exceeds max tokens: {token_count} > {self.hard_max_tokens}")
        
        # Check quality score
        if quality_score < self.quality_threshold:
            errors.append(f"Low quality score: {quality_score} < {self.quality_threshold}")
        
        # Check for incomplete sentences
        if text and not text.rstrip()[-1] in '.!?':
            errors.append("Incomplete sentence ending")
        
        # Check for boilerplate (very short + low complexity)
        unique_words = len(set(text.lower().split()))
        if unique_words < 10 and len(text) < 200:
            errors.append("Likely boilerplate (low complexity)")
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    STOPWORDS = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could', 'may', 'might', 'must', 'can'}
    
    def extract_keywords(self, text: str, top_n: int = 5) -> List[str]:
        """Extract top keywords (frequency-based, stopword filtered)."""
        words = [w.lower() for w in text.split() if len(w) > 3 and w.isalpha() and w.lower() not in self.STOPWORDS]
        return [word for word, _ in Counter(words).most_common(top_n)]
    
    def create_metadata(
        self,
        text: str,
        chunk_id: str,
        doc_data: Dict,
        section: Optional[Section],
        page_num: int,
        char_span: Tuple[int, int],
        prev_chunk_id: Optional[str],
        next_chunk_id: Optional[str]
    ) -> ChunkMetadata:
        """Generate comprehensive metadata for chunk."""
        
        # Extract document metadata
        doc_meta = doc_data.get('metadata', {})
        doc_stats = doc_data.get('statistics', {})
        
        # Extract org/industry from filename or metadata
        filename = doc_data.get('filename', 'unknown')
        org = doc_meta.get('title', filename.replace('_', ' ').title())
        
        # Count sentences
        sentences = self.split_into_sentences(text)
        sentence_count = len(sentences)
        
        # Token count
        token_count = self.count_tokens(text)
        
        # Extract keywords
        keywords = self.extract_keywords(text)
        
        # Detect policy tags
        policy_tags = self.detect_policy_tags(text)
        
        # Compute hash
        simhash = self.compute_simhash(text)
        
        # Quality score
        temp_meta = {'token_count': token_count}
        quality_score = self.calculate_quality_score(text, temp_meta)
        
        # Determine content type
        page_data = doc_data.get('pages', {}).get(str(page_num), {})
        has_tables = page_data.get('has_tables', False)
        has_images = page_data.get('has_images', False)
        content_type = 'text'
        if has_tables:
            content_type = 'text_with_tables'
        
        # Section info
        section_path = section.get_breadcrumb(2) if section else "Unknown"
        section_title = section.title if section else "Unknown"
        section_index = section.index if section else ""
        
        # Extract year from metadata or filename
        creation_date = doc_meta.get('creation_date', '')
        year_match = re.search(r'20\d{2}', creation_date) if creation_date else None
        if year_match:
            doc_year = year_match.group()
        else:
            year_match = re.search(r'20\d{2}', filename)
            doc_year = year_match.group() if year_match else "unknown"
        
        metadata = ChunkMetadata(
            doc_id=filename,
            source_url=doc_data.get('source', ''),
            org=org,
            industry="HR/Employee",  # Could be extracted from doc
            doc_type="handbook",
            doc_title=doc_meta.get('title', filename),
            doc_year=doc_year,
            section_path=section_path,
            section_title=section_title,
            section_index=section_index,
            chunk_id=chunk_id,
            char_span=char_span,
            sentence_count=sentence_count,
            content_type=content_type,
            prev_chunk_id=prev_chunk_id,
            next_chunk_id=next_chunk_id,
            keywords=keywords,
            policy_tags=policy_tags,
            hash_64=simhash,
            created_at=datetime.now().isoformat(),
            token_count=token_count,
            page_number=page_num,
            has_tables=has_tables,
            has_images=has_images,
            quality_score=quality_score,
        )
        
        return metadata
    
    def process_document(self, json_path: str) -> Optional[str]:
        """Process document: detect sections, chunk, validate, save."""
        try:
            # Load document
            with open(json_path, 'r', encoding='utf-8') as f:
                doc_data = json.load(f)
            
            filename = doc_data.get('filename', os.path.basename(json_path))
            logger.info(f"Processing: {filename}")
            
            # Detect sections
            sections = self.detect_sections(doc_data.get('pages', {}))
            
            # Process pages and create chunks
            all_chunk_texts = []
            all_chunk_metadata = []
            char_offset = 0
            
            for page_num, page_data in sorted(doc_data.get('pages', {}).items(), key=lambda x: int(x[0])):
                text = page_data.get('text', '')
                if not text or len(text.strip()) < 20:
                    continue
                
                # Normalize text
                text = self.normalize_text(text)
                
                # Find current section
                current_section = None
                for section in reversed(sections):
                    if section.start_page <= int(page_num):
                        current_section = section
                        break
                
                # Create chunks for this page
                page_chunks = self.create_token_based_chunks(text, current_section, int(page_num))
                
                for chunk_text in page_chunks:
                    all_chunk_texts.append(chunk_text)
                    all_chunk_metadata.append({
                        'page': int(page_num),
                        'section': current_section,
                        'char_start': char_offset,
                        'char_end': char_offset + len(chunk_text)
                    })
                    char_offset += len(chunk_text)
            
            if not all_chunk_texts:
                logger.warning(f"No chunks created for {filename}")
                return None
            
            # Create Chunk objects with full metadata
            chunks = []
            for idx, chunk_text in enumerate(all_chunk_texts):
                meta_info = all_chunk_metadata[idx]
                
                chunk_id = f"{filename}_chunk_{idx:04d}"
                prev_chunk_id = f"{filename}_chunk_{idx-1:04d}" if idx > 0 else None
                next_chunk_id = f"{filename}_chunk_{idx+1:04d}" if idx < len(all_chunk_texts) - 1 else None
                
                metadata = self.create_metadata(
                    text=chunk_text,
                    chunk_id=chunk_id,
                    doc_data=doc_data,
                    section=meta_info['section'],
                    page_num=meta_info['page'],
                    char_span=(meta_info['char_start'], meta_info['char_end']),
                    prev_chunk_id=prev_chunk_id,
                    next_chunk_id=next_chunk_id
                )
                
                # Validate
                is_valid, errors = self.validate_chunk(chunk_text, asdict(metadata), metadata.quality_score)
                
                if is_valid:
                    # Check for duplicates
                    if not self.is_duplicate(metadata.hash_64):
                        chunk = Chunk(text=chunk_text, metadata=metadata)
                        chunks.append(chunk)
                    else:
                        self.stats['rejected_chunks'] += 1
                        logger.debug(f"Rejected duplicate chunk: {chunk_id}")
                else:
                    self.stats['rejected_chunks'] += 1
                    logger.debug(f"Rejected chunk {chunk_id}: {', '.join(errors)}")
            
            logger.info(f"Created {len(chunks)} valid chunks (rejected {self.stats['rejected_chunks']})")
            
            # Save chunks
            base_name = os.path.splitext(os.path.basename(json_path))[0]
            output_path = os.path.join(self.output_dir, f"{base_name}_chunks.jsonl")
            
            with open(output_path, 'w', encoding='utf-8') as f:
                for chunk in chunks:
                    f.write(json.dumps(chunk.to_dict(), ensure_ascii=False) + '\n')
            
            # Copy to validated
            validated_path = os.path.join(self.validated_dir, "chunks", f"{base_name}_chunks.jsonl")
            shutil.copy2(output_path, validated_path)
            
            # Update stats
            self.stats['total_chunks'] += len(chunks)
            self.stats['avg_quality_score'] = sum(c.metadata.quality_score for c in chunks) / len(chunks) if chunks else 0
            
            logger.info(f"Saved to: {validated_path}")
            return validated_path
            
        except Exception as e:
            logger.error(f"Error processing {json_path}: {e}", exc_info=True)
            return None
    
    def process_all(self) -> Dict[str, Any]:
        """Process all documents. Returns statistics."""
        json_files = list(Path(self.input_dir).glob("*.json"))
        
        if not json_files:
            logger.warning(f"No JSON files found in {self.input_dir}")
            return self.stats
        
        logger.info(f"Found {len(json_files)} files to process")
        self.stats['total_docs'] = len(json_files)
        
        output_files = []
        for json_path in tqdm(json_files, desc="Processing documents"):
            output_path = self.process_document(str(json_path))
            if output_path:
                output_files.append(output_path)
        
        logger.info(f"Successfully processed {len(output_files)}/{len(json_files)} documents")
        logger.info(f"Total chunks: {self.stats['total_chunks']}")
        logger.info(f"Avg quality score: {self.stats['avg_quality_score']:.3f}")
        
        return self.stats


def main():
    """Main preprocessing pipeline."""
    print("\n" + "="*70)
    print("Production Preprocessing Pipeline")
    print("="*70 + "\n")
    
    preprocessor = ProductionPreprocessor(
        target_tokens=220,
        hard_max_tokens=320,
        overlap_ratio=0.12,
        min_chars=180,
        min_words=50,
        quality_threshold=0.55
    )
    
    stats = preprocessor.process_all()
    
    print("\n" + "="*70)
    print("Preprocessing Complete")
    print("="*70)
    print(f"Documents processed: {stats['total_docs']}")
    print(f"Total chunks created: {stats['total_chunks']}")
    print(f"Chunks rejected: {stats['rejected_chunks']}")
    print(f"Average quality score: {stats['avg_quality_score']:.3f}")
    print(f"\nOutput: {VALIDATED_DATA_DIR}/chunks/")
    print(f"Logs: {LOGS_DIR}/preprocess.log")
    print("="*70 + "\n")
    
    return 0 if stats['total_chunks'] > 0 else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

