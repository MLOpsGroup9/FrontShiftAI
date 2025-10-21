"""
Text preprocessing module: normalize, clean, and detect sections in markdown files.
Reads .md files from data/extracted/, outputs cleaned markdown to data/cleaned/.
"""

import os
import sys
import re
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from tqdm import tqdm

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config import EXTRACTED_DATA_DIR, CLEANED_DATA_DIR, LOGS_DIR

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


@dataclass
class Section:
    """Section/heading information with hierarchy."""
    title: str
    level: int
    index: str
    start_position: int  # Character position in text
    parent_path: str = ""
    
    def get_breadcrumb(self, depth: int = 2) -> str:
        """Get section breadcrumb path."""
        parts = [p for p in [self.parent_path, self.title] if p]
        return ' › '.join(parts[-depth:]) if parts else self.title


class TextPreprocessor:
    """Normalize and clean markdown text, detect sections."""
    
    def __init__(
        self,
        input_dir: str = EXTRACTED_DATA_DIR,
        output_dir: str = CLEANED_DATA_DIR
    ):
        self.input_dir = input_dir
        self.output_dir = output_dir
        
        # Create directories
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(LOGS_DIR, 'preprocessing'), exist_ok=True)
        
        # Section detection patterns
        self.section_patterns = {
            'numbered': re.compile(r'^(\d+(?:\.\d+)*)\s+([A-Z].+)', re.MULTILINE),
            'allcaps': re.compile(r'^[A-Z0-9][A-Z0-9\s&/\-]{3,}$', re.MULTILINE),
            'markdown_header': re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE),
        }
        
        # Statistics
        self.stats = {
            'total_docs': 0,
            'total_sections': 0,
            'cleaned_chars': 0,
        }
    
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
    
    def detect_sections(self, text: str) -> List[Section]:
        """Detect numbered, ALL-CAPS, and markdown header sections."""
        sections = []
        section_stack = []  # Track hierarchy
        
        lines = text.split('\n')
        char_position = 0
        
        for line in lines:
            line_stripped = line.strip()
            
            if not line_stripped:
                char_position += len(line) + 1  # +1 for newline
                continue
            
            # Check for markdown headers (# Title, ## Subtitle, etc.)
            md_match = self.section_patterns['markdown_header'].match(line_stripped)
            if md_match:
                hashes = md_match.group(1)
                title = md_match.group(2).strip()
                level = len(hashes)
                
                # Update section stack
                while section_stack and section_stack[-1].level >= level:
                    section_stack.pop()
                
                parent_path = ' › '.join([s.title for s in section_stack])
                
                section = Section(
                    title=title,
                    level=level,
                    index="",
                    start_position=char_position,
                    parent_path=parent_path
                )
                sections.append(section)
                section_stack.append(section)
                char_position += len(line) + 1
                continue
            
            # Check for numbered sections (1.2.3 Title)
            num_match = self.section_patterns['numbered'].match(line_stripped)
            if num_match:
                index = num_match.group(1)
                title = num_match.group(2).strip()
                level = index.count('.') + 1
                
                # Update section stack
                while section_stack and section_stack[-1].level >= level:
                    section_stack.pop()
                
                parent_path = ' › '.join([s.title for s in section_stack])
                
                section = Section(
                    title=title,
                    level=level,
                    index=index,
                    start_position=char_position,
                    parent_path=parent_path
                )
                sections.append(section)
                section_stack.append(section)
                char_position += len(line) + 1
                continue
            
            # Check for ALL CAPS sections
            if self.section_patterns['allcaps'].match(line_stripped) and len(line_stripped) > 5:
                # Treat as level 1 section
                level = 1
                
                # Clear stack for top-level
                section_stack = []
                
                section = Section(
                    title=line_stripped,
                    level=level,
                    index="",
                    start_position=char_position,
                    parent_path=""
                )
                sections.append(section)
                section_stack.append(section)
            
            char_position += len(line) + 1  # +1 for newline
        
        logger.info(f"Detected {len(sections)} sections")
        return sections
    
    def process_markdown_file(self, md_path: str) -> Optional[str]:
        """Process single markdown file: normalize text, detect sections, save cleaned output."""
        try:
            filename = os.path.basename(md_path)
            logger.info(f"Processing: {filename}")
            
            # Read markdown
            with open(md_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            if not text or len(text.strip()) < 50:
                logger.warning(f"Empty or too short: {filename}")
                return None
            
            # Normalize text
            normalized_text = self.normalize_text(text)
            
            # Detect sections
            sections = self.detect_sections(normalized_text)
            
            # Prepare output
            base_name = os.path.splitext(filename)[0]
            output_data = {
                'filename': filename,
                'text': normalized_text,
                'sections': [asdict(s) for s in sections],
                'stats': {
                    'char_count': len(normalized_text),
                    'section_count': len(sections),
                }
            }
            
            # Save cleaned markdown + metadata as JSON
            output_path = os.path.join(self.output_dir, f"{base_name}_cleaned.json")
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            # Update stats
            self.stats['total_sections'] += len(sections)
            self.stats['cleaned_chars'] += len(normalized_text)
            
            logger.info(f"Saved cleaned text to: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error processing {md_path}: {e}", exc_info=True)
            return None
    
    def process_all(self) -> Dict:
        """Process all markdown files in input directory."""
        md_files = list(Path(self.input_dir).glob("*.md"))
        
        if not md_files:
            logger.warning(f"No .md files found in {self.input_dir}")
            return self.stats
        
        logger.info(f"Found {len(md_files)} markdown files to process")
        self.stats['total_docs'] = len(md_files)
        
        output_files = []
        for md_path in tqdm(md_files, desc="Processing markdown files"):
            output_path = self.process_markdown_file(str(md_path))
            if output_path:
                output_files.append(output_path)
        
        logger.info(f"Successfully processed {len(output_files)}/{len(md_files)} files")
        logger.info(f"Total sections detected: {self.stats['total_sections']}")
        logger.info(f"Total cleaned characters: {self.stats['cleaned_chars']:,}")
        
        return self.stats


def main():
    """Main text preprocessing pipeline."""
    print("\n" + "="*70)
    print("Text Preprocessing Pipeline (Markdown)")
    print("="*70 + "\n")
    
    # Use md_files directory for markdown input
    md_files_dir = os.path.join(os.path.dirname(EXTRACTED_DATA_DIR), "md_files")
    
    preprocessor = TextPreprocessor(
        input_dir=md_files_dir,
        output_dir=CLEANED_DATA_DIR
    )
    
    stats = preprocessor.process_all()
    
    print("\n" + "="*70)
    print("Text Preprocessing Complete!")
    print("="*70)
    print(f"Processed: {stats['total_docs']} documents")
    print(f"Sections detected: {stats['total_sections']}")
    print(f"Characters cleaned: {stats['cleaned_chars']:,}")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()

