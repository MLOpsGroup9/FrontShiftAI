"""
Extracts text from PDFs with advanced cleaning, metadata extraction, and validation.
Uses PyMuPDF for complex layouts. Handles headers/footers, boilerplate removal.
"""

import fitz
import os
import sys
import re
import json
import logging
from typing import Dict, List, Optional, Tuple
from tqdm import tqdm
from pathlib import Path
from datetime import datetime
from collections import Counter

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config import RAW_DATA_DIR, EXTRACTED_DATA_DIR, LOGS_DIR

# Setup logging
os.makedirs(LOGS_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, 'data_extraction.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class PDFExtractor:
    """PDF text extractor with cleaning and validation."""
    
    def __init__(self, input_dir: str = RAW_DATA_DIR, output_dir: str = EXTRACTED_DATA_DIR):
        self.input_dir = input_dir
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Common header/footer patterns in HR handbooks
        self.boilerplate_patterns = [
            r'Page \d+ of \d+',
            r'^\d+\s*$',  # Page numbers alone
            r'Confidential|Proprietary|Internal Use Only',
            r'Employee Handbook|Company Policy',
            r'©.*?\d{4}',  # Copyright notices
            r'Updated:.*?\d{4}',
            r'Revised:.*?\d{4}',
            r'Version \d+\.\d+',
            r'Document ID:.*?',
            r'Classification:.*?',
        ]
        
    def extract_pdf_metadata(self, pdf_doc: fitz.Document, pdf_path: str) -> Dict:
        """Extract PDF metadata (author, title, dates, etc.)."""
        metadata = pdf_doc.metadata or {}
        
        # Get PDF version safely
        try:
            pdf_version = pdf_doc.pdf_version() if hasattr(pdf_doc, 'pdf_version') else getattr(pdf_doc, 'version', 'unknown')
        except:
            pdf_version = 'unknown'
        
        return {
            "source_path": pdf_path,
            "filename": os.path.basename(pdf_path),
            "file_size_mb": os.path.getsize(pdf_path) / (1024 * 1024),
            "total_pages": len(pdf_doc),
            "pdf_version": pdf_version,
            "is_encrypted": pdf_doc.is_encrypted,
            "title": metadata.get('title', ''),
            "author": metadata.get('author', ''),
            "subject": metadata.get('subject', ''),
            "keywords": metadata.get('keywords', ''),
            "creator": metadata.get('creator', ''),
            "producer": metadata.get('producer', ''),
            "creation_date": metadata.get('creationDate', ''),
            "modification_date": metadata.get('modDate', ''),
            "extraction_timestamp": datetime.now().isoformat(),
        }
    
    def detect_header_footer(self, pages_text: List[str]) -> Tuple[List[str], List[str]]:
        """Detect recurring headers/footers by analyzing first/last lines."""
        if len(pages_text) < 3:
            return [], []
        
        # Single pass: collect first/last 3 lines from each page
        first_lines, last_lines = zip(*[
            (('\n'.join(lines[:3]), '\n'.join(lines[-3:])) if len(lines := text.strip().split('\n')) >= 3 else ('', ''))
            for text in pages_text
        ]) if pages_text else ([], [])
        
        # Find patterns appearing in >50% of pages
        threshold = len(pages_text) * 0.5
        return (
            [h for h, count in Counter(first_lines).items() if count > threshold and h],
            [f for f, count in Counter(last_lines).items() if count > threshold and f]
        )
    
    def remove_boilerplate(self, text: str, headers: List[str], footers: List[str]) -> str:
        """Remove headers, footers, and boilerplate patterns in one pass."""
        # Remove all patterns in single iteration
        for pattern in [*headers, *footers]:
            text = text.replace(pattern, '')
        for pattern in self.boilerplate_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        return text.strip()
    
    def clean_text(self, text: str) -> str:
        """Clean text: fix Unicode, OCR issues, normalize whitespace, remove junk lines."""
        if not text:
            return ""
        
        # Remove zero-width characters and other invisible chars
        text = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', text)
        
        # Fix common OCR issues
        text = text.replace('ﬁ', 'fi').replace('ﬂ', 'fl')
        text = text.replace(''', "'").replace(''', "'")
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace('–', '-').replace('—', '-')
        
        # Remove excessive whitespace but preserve paragraph breaks
        text = re.sub(r' +', ' ', text)  # Multiple spaces to single
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Multiple newlines to double
        
        # Remove lines with only special characters
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            # Keep line if it has at least 3 alphanumeric characters
            if len(re.findall(r'[a-zA-Z0-9]', line)) >= 3:
                cleaned_lines.append(line.strip())
        
        text = '\n'.join(cleaned_lines)
        
        # Remove trailing/leading whitespace
        text = text.strip()
        
        return text
    
    def extract_page_content(self, page: fitz.Page, page_num: int) -> Dict:
        """Extract text, detect tables/images, count words/chars."""
        try:
            text = page.get_text("text")
            words = text.split()
            images = page.get_images()
            
            return {
                "page_number": page_num,
                "text": text,
                "char_count": len(text),
                "word_count": len(words),
                "has_tables": '\t' in text or '   ' in text,
                "has_images": bool(images),
                **({"image_count": len(images)} if images else {})
            }
        except Exception as e:
            logger.error(f"Error extracting content from page {page_num}: {e}")
            return {"page_number": page_num, "text": "", "char_count": 0, "word_count": 0, 
                    "has_tables": False, "has_images": False}
    
    def validate_extraction(self, data: Dict) -> Tuple[bool, List[str]]:
        """Validate extraction: check required fields, content, empty pages."""
        errors = []
        
        # Check required fields
        required_fields = ["source", "filename", "total_pages", "pages"]
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")
        
        # Validate pages
        if "pages" in data:
            if not data["pages"]:
                errors.append("No pages extracted")
            
            # Check for minimum content
            total_text = sum(len(page.get("text", "")) for page in data["pages"].values())
            if total_text < 100:
                errors.append(f"Insufficient text extracted: {total_text} chars")
            
            # Check for too many empty pages
            empty_pages = sum(1 for page in data["pages"].values() if len(page.get("text", "")) < 10)
            if empty_pages > len(data["pages"]) * 0.5:
                errors.append(f"Too many empty pages: {empty_pages}/{len(data['pages'])}")
        
        # Validate metadata
        if "metadata" in data:
            if data["metadata"].get("total_pages", 0) <= 0:
                errors.append("Invalid page count in metadata")
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def extract_text(self, pdf_path: str) -> Dict[int, Dict]:
        """Extract and clean text from all PDF pages."""
        pages_content = {}
        
        try:
            # Open PDF
            pdf_doc = fitz.open(pdf_path)
            
            if pdf_doc.is_encrypted:
                logger.warning(f"PDF is encrypted: {pdf_path}")
                # Try to decrypt with empty password
                if not pdf_doc.authenticate(""):
                    logger.error(f"Cannot decrypt PDF: {pdf_path}")
                    return {}
            
            # Extract all pages first for header/footer detection
            all_texts = []
            for page_num in range(len(pdf_doc)):
                page = pdf_doc[page_num]
                text = page.get_text("text")
                all_texts.append(text)
            
            # Detect headers and footers
            headers, footers = self.detect_header_footer(all_texts)
            
            # Process each page
            for page_num in tqdm(range(len(pdf_doc)), desc=f"Extracting {os.path.basename(pdf_path)}"):
                page = pdf_doc[page_num]
                
                # Extract page content
                content = self.extract_page_content(page, page_num + 1)
                
                # Clean and remove boilerplate
                if content["text"]:
                    content["text"] = self.remove_boilerplate(content["text"], headers, footers)
                    content["text"] = self.clean_text(content["text"])
                
                # Update counts after cleaning
                content["char_count"] = len(content["text"])
                content["word_count"] = len(content["text"].split())
                
                # Only store pages with actual content
                if content["char_count"] > 10:
                    pages_content[page_num + 1] = content
            
            pdf_doc.close()
            logger.info(f"Extracted {len(pages_content)} pages with content from {pdf_path}")
            
        except fitz.FileDataError as e:
            logger.error(f"Corrupt PDF file {pdf_path}: {e}")
        except Exception as e:
            logger.error(f"Error processing {pdf_path}: {e}", exc_info=True)
        
        return pages_content
    
    def process_pdf(self, pdf_path: str) -> Optional[str]:
        """Full pipeline: extract, clean, validate, save to JSON."""
        try:
            # Open PDF for metadata extraction
            pdf_doc = fitz.open(pdf_path)
            
            # Extract metadata
            metadata = self.extract_pdf_metadata(pdf_doc, pdf_path)
            
            pdf_doc.close()
            
            # Extract page content
            pages_content = self.extract_text(pdf_path)
            
            if not pages_content:
                logger.warning(f"No content extracted from {pdf_path}")
                return None
            
            # Calculate statistics
            total_words = sum(page["word_count"] for page in pages_content.values())
            total_chars = sum(page["char_count"] for page in pages_content.values())
            pages_with_tables = sum(1 for page in pages_content.values() if page.get("has_tables"))
            pages_with_images = sum(1 for page in pages_content.values() if page.get("has_images"))
            
            # Build output via dict comprehension
            filename = Path(pdf_path).stem
            num_pages = len(pages_content)
            
            data = {
                "source": pdf_path,
                "filename": filename,
                "total_pages": num_pages,
                "metadata": metadata,
                "statistics": {
                    "total_words": total_words,
                    "total_chars": total_chars,
                    "avg_words_per_page": total_words / num_pages if num_pages else 0,
                    "pages_with_tables": pages_with_tables,
                    "pages_with_images": pages_with_images,
                },
                "pages": {
                    str(num): {k: v for k, v in content.items() if k != 'image_count' or v}
                    for num, content in pages_content.items()
                }
            }
            
            # Validate before saving
            is_valid, errors = self.validate_extraction(data)
            
            if not is_valid:
                logger.error(f"Validation failed for {pdf_path}: {', '.join(errors)}")
                return None
            
            # Save with minimal, clean JSON (no extra whitespace)
            output_path = os.path.join(self.output_dir, f"{filename}.json")
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
            
            logger.info(f"Saved {len(pages_content)} pages ({total_words} words) to {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to process {pdf_path}: {e}", exc_info=True)
            return None
    
    def process_all(self, max_retries: int = 2) -> Dict[str, any]:
        """Process all PDFs with retry logic for failures."""
        pdf_files = list(Path(self.input_dir).glob("*.pdf"))
        
        if not pdf_files:
            logger.warning(f"No PDF files found in {self.input_dir}")
            return {
                "total_files": 0,
                "successful": 0,
                "failed": 0,
                "output_files": [],
                "failed_files": []
            }
        
        logger.info(f"Found {len(pdf_files)} PDF files to process")
        
        output_files = []
        failed_files = []
        
        # First attempt
        for pdf_path in pdf_files:
            output_path = self.process_pdf(str(pdf_path))
            if output_path:
                output_files.append(output_path)
            else:
                failed_files.append(str(pdf_path))
        
        # Retry failed files
        if failed_files and max_retries > 0:
            logger.info(f"Retrying {len(failed_files)} failed files...")
            retry_failed = []
            
            for retry_attempt in range(max_retries):
                for pdf_path in failed_files[:]:  # Copy list to modify during iteration
                    logger.info(f"Retry {retry_attempt + 1}/{max_retries} for {pdf_path}")
                    output_path = self.process_pdf(pdf_path)
                    if output_path:
                        output_files.append(output_path)
                        failed_files.remove(pdf_path)
                
                if not failed_files:
                    break
        
        logger.info(f"Successfully processed {len(output_files)}/{len(pdf_files)} PDFs")
        
        if failed_files:
            logger.error(f"Failed to process {len(failed_files)} files: {failed_files}")
        
        return {
            "total_files": len(pdf_files),
            "successful": len(output_files),
            "failed": len(failed_files),
            "output_files": output_files,
            "failed_files": failed_files
        }


def main():
    """Main extraction pipeline."""
    print("\n" + "="*70)
    print("PDF Data Extraction Pipeline")
    print("="*70 + "\n")
    
    extractor = PDFExtractor()
    results = extractor.process_all()
    
    print("\n" + "="*70)
    print("Extraction Complete")
    print("="*70)
    print(f"Total PDFs: {results['total_files']}")
    print(f"Successful: {results['successful']}")
    print(f"Failed: {results['failed']}")
    
    if results['failed'] > 0:
        print("\nFailed files:")
        for failed_file in results['failed_files']:
            print(f"  - {failed_file}")
    
    print(f"\nOutput: {EXTRACTED_DATA_DIR}")
    print(f"Logs: {os.path.join(LOGS_DIR, 'data_extraction.log')}")
    print("="*70 + "\n")
    
    return 0 if results['failed'] == 0 else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

