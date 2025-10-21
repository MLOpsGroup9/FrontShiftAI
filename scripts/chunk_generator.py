"""
Chunk generation module: token-based chunking with quality scoring and validation.
Reads cleaned JSON from data/cleaned/, outputs validated chunks to data/validated/chunks/.
"""

import os
import sys
import json
import re
import logging
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any, Set
from dataclasses import dataclass, field, asdict
from collections import Counter
from datetime import datetime
from tqdm import tqdm
import tiktoken

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config import CLEANED_DATA_DIR, VALIDATED_DATA_DIR, LOGS_DIR

# Setup logging
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(os.path.join(LOGS_DIR, 'preprocessing'), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, 'preprocessing', 'preprocess.log')),
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
    start_position: int
    parent_path: str = ""
    
    def get_breadcrumb(self, depth: int = 2) -> str:
        """Get section breadcrumb path."""
        parts = [p for p in [self.parent_path, self.title] if p]
        return ' › '.join(parts[-depth:]) if parts else self.title


@dataclass
class ChunkMetadata:
    """Comprehensive chunk metadata schema with company field."""
    # Required fields
    doc_id: str
    company: str  # NEW: Company name
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
    """Container for chunk text and metadata."""
    text: str
    metadata: ChunkMetadata
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'text': self.text,
            'metadata': asdict(self.metadata)
        }


class ChunkGenerator:
    """Token-based chunk generation with quality scoring and validation."""
    
    def __init__(
        self,
        tokenizer_name: str = "cl100k_base",
        target_tokens: int = 900,
        hard_max_tokens: int = 1200,
        overlap_ratio: float = 0.11,
        input_dir: str = CLEANED_DATA_DIR,
        output_dir: str = VALIDATED_DATA_DIR,
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
        self.output_dir = os.path.join(output_dir, "chunks")
        
        # Initialize tokenizer
        try:
            self.tokenizer = tiktoken.get_encoding(tokenizer_name)
            logger.info(f"Loaded tokenizer: {tokenizer_name}")
        except Exception as e:
            logger.warning(f"Failed to load {tokenizer_name}, using cl100k_base: {e}")
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
        # Create directories
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(os.path.join(LOGS_DIR, 'preprocessing'), exist_ok=True)
        
        # Statistics
        self.stats = {
            'total_docs': 0,
            'total_chunks': 0,
            'rejected_chunks': 0,
            'avg_quality_score': 0.0,
        }
        
        # Chunk hash registry for deduplication
        self.seen_hashes: Set[str] = set()
    
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
    
    def create_token_based_chunks(self, text: str, section: Optional[Section] = None) -> List[str]:
        """Create 900-token chunks with 11% overlap (~100 tokens)."""
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
    
    def extract_company_name(self, filename: str, sections: List[Dict]) -> str:
        """Extract clean company name from filename or first section."""
        # Common document type words to filter out
        doc_words = {'handbook', 'policy', 'manual', 'guide', 'document', 'md', 'pdf', 
                     'employee', 'team', 'member', 'jan', 'feb', 'mar', 'apr', 'may', 'jun',
                     'jul', 'aug', 'sep', 'oct', 'nov', 'dec', 'effective', 'updated'}
        
        # Clean filename first - remove all extensions and common suffixes
        clean_fn = filename.replace('_cleaned.json', '').replace('.json', '').replace('.md', '')
        
        # Handle both underscore and hyphen separators
        name_parts = clean_fn.replace('_', ' ').replace('-', ' ').split()
        
        if len(name_parts) >= 1:
            # Capitalize words, but filter out common doc type words and dates
            filtered = []
            for w in name_parts:
                w_lower = w.lower()
                # Skip doc words, 4-digit years, and month abbreviations
                if w_lower not in doc_words and not (w.isdigit() and len(w) == 4):
                    filtered.append(w.capitalize())
            
            if filtered:
                # Rejoin and clean up
                clean_name = ' '.join(filtered[:4])  # Take first 4 words max
                return clean_name
        
        # Fallback to first section title if it looks like a company name
        if sections and len(sections) > 0:
            first_section = sections[0].get('title', '')
            # Look for short, meaningful titles
            if 2 <= len(first_section.split()) <= 5:
                return first_section
        
        # Last resort: just capitalize first word from filename
        first_word = clean_fn.split('_')[0].split('-')[0]
        return first_word.capitalize() if first_word else "Unknown Company"
    
    def infer_org_type(self, company: str, text: str, keywords: List[str]) -> str:
        """Infer organization type from company name, content, and keywords."""
        # Combine company name and text for analysis
        combined_text = f"{company} {text[:1000]}".lower()  # First 1000 chars
        
        # Define organization type patterns
        org_patterns = {
            'Financial Services': ['bank', 'financial', 'credit union', 'investment', 'insurance', 'mortgage'],
            'Construction': ['construction', 'builder', 'contractor', 'engineering', 'architect'],
            'Healthcare': ['hospital', 'medical', 'healthcare', 'clinic', 'health', 'patient'],
            'Technology': ['tech', 'software', 'digital', 'computing', 'IT', 'data'],
            'Manufacturing': ['manufacturing', 'factory', 'production', 'industrial'],
            'Retail': ['retail', 'store', 'shopping', 'merchandise'],
            'Hospitality': ['hotel', 'resort', 'restaurant', 'hospitality', 'lodging'],
            'Education': ['school', 'university', 'college', 'education', 'academic'],
            'Government': ['government', 'federal', 'state', 'municipal', 'public sector'],
            'Non-Profit': ['non-profit', 'nonprofit', 'foundation', 'charity'],
        }
        
        # Score each category
        scores = {}
        for org_type, patterns in org_patterns.items():
            score = sum(1 for pattern in patterns if pattern in combined_text)
            if score > 0:
                scores[org_type] = score
        
        # Return highest scoring type, or 'General Business' as default
        if scores:
            return max(scores, key=scores.get)
        return 'General Business'
    
    def create_metadata(
        self,
        text: str,
        chunk_id: str,
        filename: str,
        sections: List[Dict],
        current_section: Optional[Dict],
        char_span: Tuple[int, int],
        prev_chunk_id: Optional[str],
        next_chunk_id: Optional[str],
        overlap_tokens: int = 0
    ) -> ChunkMetadata:
        """Generate comprehensive metadata for chunk."""
        
        # Extract company name
        company = self.extract_company_name(filename, sections)
        
        # Count sentences
        sentences = self.split_into_sentences(text)
        sentence_count = len(sentences)
        
        # Token count
        token_count = self.count_tokens(text)
        
        # Extract keywords
        keywords = self.extract_keywords(text)
        
        # Infer organization type
        org_type = self.infer_org_type(company, text, keywords)
        
        # Detect policy tags
        policy_tags = self.detect_policy_tags(text)
        
        # Compute hash
        simhash = self.compute_simhash(text)
        
        # Quality score
        temp_meta = {'token_count': token_count}
        quality_score = self.calculate_quality_score(text, temp_meta)
        
        # Section info
        if current_section:
            section_title = current_section.get('title', 'Unknown')
            section_index = current_section.get('index', '')
            section_level = current_section.get('level', 1)
            parent_path = current_section.get('parent_path', '')
            section_path = ' › '.join([p for p in [parent_path, section_title] if p])
        else:
            section_title = "Unknown"
            section_index = ""
            section_path = "Unknown"
        
        # Extract year from filename
        year_match = re.search(r'20\d{2}', filename)
        doc_year = year_match.group() if year_match else "unknown"
        
        # Context previews (first/last 50 chars of prev/next chunks)
        context_prev = ""
        context_next = ""
        
        metadata = ChunkMetadata(
            doc_id=filename.replace('_cleaned.json', ''),
            company=company,
            source_url="",  # To be filled from external metadata if available
            org=org_type,  # Organization type (e.g., 'Financial Services', 'Construction')
            industry="HR/Employee",
            doc_type="handbook",
            doc_title=company,
            doc_year=doc_year,
            section_path=section_path,
            section_title=section_title,
            section_index=section_index,
            chunk_id=chunk_id,
            char_span=char_span,
            sentence_count=sentence_count,
            content_type='text',
            prev_chunk_id=prev_chunk_id,
            next_chunk_id=next_chunk_id,
            keywords=keywords,
            policy_tags=policy_tags,
            hash_64=simhash,
            created_at=datetime.now().isoformat(),
            token_count=token_count,
            overlap_with_prev=overlap_tokens,
            page_number=None,
            has_tables=False,
            has_images=False,
            quality_score=quality_score,
            context_preview_prev=context_prev,
            context_preview_next=context_next,
        )
        
        return metadata
    
    def process_cleaned_file(self, json_path: str) -> Optional[str]:
        """Process cleaned JSON: chunk text, generate metadata, validate, save."""
        try:
            # Load cleaned data
            with open(json_path, 'r', encoding='utf-8') as f:
                cleaned_data = json.load(f)
            
            filename = cleaned_data.get('filename', os.path.basename(json_path))
            text = cleaned_data.get('text', '')
            sections = cleaned_data.get('sections', [])
            
            logger.info(f"Processing: {filename}")
            
            if not text or len(text.strip()) < 100:
                logger.warning(f"Text too short: {filename}")
                return None
            
            # Create chunks
            chunk_texts = self.create_token_based_chunks(text)
            
            if not chunk_texts:
                logger.warning(f"No chunks created for {filename}")
                return None
            
            # Find section for each chunk based on character position
            def find_section_for_position(char_pos: int) -> Optional[Dict]:
                """Find the section that contains this character position."""
                current_section = None
                for section in sections:
                    if section['start_position'] <= char_pos:
                        current_section = section
                    else:
                        break
                return current_section
            
            # Create Chunk objects with full metadata
            chunks = []
            char_offset = 0
            overlap_tokens = int(self.target_tokens * self.overlap_ratio)
            
            for idx, chunk_text in enumerate(chunk_texts):
                chunk_id = f"{filename.replace('_cleaned.json', '')}_chunk_{idx:04d}"
                prev_chunk_id = f"{filename.replace('_cleaned.json', '')}_chunk_{idx-1:04d}" if idx > 0 else None
                next_chunk_id = f"{filename.replace('_cleaned.json', '')}_chunk_{idx+1:04d}" if idx < len(chunk_texts) - 1 else None
                
                char_start = char_offset
                char_end = char_offset + len(chunk_text)
                
                # Find current section
                current_section = find_section_for_position(char_start)
                
                metadata = self.create_metadata(
                    text=chunk_text,
                    chunk_id=chunk_id,
                    filename=filename,
                    sections=sections,
                    current_section=current_section,
                    char_span=(char_start, char_end),
                    prev_chunk_id=prev_chunk_id,
                    next_chunk_id=next_chunk_id,
                    overlap_tokens=overlap_tokens if idx > 0 else 0
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
                
                char_offset = char_end
            
            logger.info(f"Created {len(chunks)} valid chunks (rejected {self.stats['rejected_chunks']})")
            
            # Save chunks as JSONL
            base_name = os.path.splitext(os.path.basename(json_path))[0].replace('_cleaned', '')
            output_path = os.path.join(self.output_dir, f"{base_name}_chunks.jsonl")
            
            with open(output_path, 'w', encoding='utf-8') as f:
                for chunk in chunks:
                    f.write(json.dumps(chunk.to_dict(), ensure_ascii=False) + '\n')
            
            # Update stats
            self.stats['total_chunks'] += len(chunks)
            quality_scores = [c.metadata.quality_score for c in chunks]
            self.stats['avg_quality_score'] = sum(quality_scores) / len(quality_scores) if quality_scores else 0
            
            logger.info(f"Saved to: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error processing {json_path}: {e}", exc_info=True)
            return None
    
    def process_all(self) -> Dict[str, Any]:
        """Process all cleaned JSON files. Returns statistics."""
        json_files = list(Path(self.input_dir).glob("*_cleaned.json"))
        
        if not json_files:
            logger.warning(f"No cleaned JSON files found in {self.input_dir}")
            return self.stats
        
        logger.info(f"Found {len(json_files)} files to process")
        self.stats['total_docs'] = len(json_files)
        
        output_files = []
        for json_path in tqdm(json_files, desc="Generating chunks"):
            output_path = self.process_cleaned_file(str(json_path))
            if output_path:
                output_files.append(output_path)
        
        logger.info(f"Successfully processed {len(output_files)}/{len(json_files)} documents")
        logger.info(f"Total chunks: {self.stats['total_chunks']}")
        logger.info(f"Avg quality score: {self.stats['avg_quality_score']:.3f}")
        
        return self.stats


def main():
    """Main chunk generation pipeline."""
    print("\n" + "="*70)
    print("Chunk Generation Pipeline (900 tokens, 11% overlap)")
    print("="*70 + "\n")
    
    generator = ChunkGenerator(
        target_tokens=900,
        hard_max_tokens=1200,
        overlap_ratio=0.11,
        min_chars=180,
        min_words=50,
        quality_threshold=0.55
    )
    
    stats = generator.process_all()
    
    print("\n" + "="*70)
    print("Chunk Generation Complete!")
    print("="*70)
    print(f"Processed: {stats['total_docs']} documents")
    print(f"Generated chunks: {stats['total_chunks']}")
    print(f"Rejected chunks: {stats['rejected_chunks']}")
    print(f"Avg quality score: {stats['avg_quality_score']:.3f}")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()

