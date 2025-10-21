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
import traceback
import warnings
import shutil
import argparse
from typing import Dict, List, Optional, Tuple, Any
from tqdm import tqdm
from pathlib import Path
from datetime import datetime
from collections import Counter
import numpy as np
import cv2
import pytesseract
import pdfplumber
from PIL import Image
import torch
from transformers import VisionEncoderDecoderModel, ViTImageProcessor, AutoTokenizer

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

# Secondary artifact directory for Markdown and images
MD_FILES_DIR = os.path.join(os.path.dirname(EXTRACTED_DATA_DIR), "md_files")
os.makedirs(MD_FILES_DIR, exist_ok=True)
PAGE_DELIMITER = "\n\n---\n\n"


def _configure_tesseract() -> Optional[str]:
    """Resolve the Tesseract binary path and configure pytesseract."""
    candidates = [
        os.getenv("TESSERACT_CMD"),
        shutil.which("tesseract"),
        "/opt/homebrew/bin/tesseract",  # common Homebrew path on Apple Silicon
        "/usr/local/bin/tesseract",     # common Homebrew path on Intel Macs
        "/usr/bin/tesseract",           # common Linux path
        "C:/Program Files/Tesseract-OCR/tesseract.exe",  # Windows default
        "C:/Program Files (x86)/Tesseract-OCR/tesseract.exe",
    ]

    for candidate in candidates:
        if not candidate:
            continue
        resolved = Path(candidate).expanduser()
        if resolved.is_file() and os.access(resolved, os.X_OK):
            pytesseract.pytesseract.tesseract_cmd = str(resolved)
            return str(resolved)
    return None


_TESSERACT_PATH = _configure_tesseract()
if not _TESSERACT_PATH:
    logger.warning("Tesseract executable not detected. OCR captions will be skipped. Install Tesseract for better image captions.")


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


class MarkdownPDFGenerator:
    """
    Layout-aware Markdown generator (secondary artifact):
    - Tables via pdfplumber -> Markdown tables
    - Images cropped and saved; captions via OCR fallback, then ViT-GPT2 if available
    - Hyperlinks preserved
    - Heuristic code-block detection with language fences
    """
    BULLET_POINTS = "•◦▪▫●○"

    def __init__(self, pdf_path: str, output_dir: Optional[str] = None, logger_instance: Optional[logging.Logger] = None):
        self.pdf_path = pdf_path
        self.pdf_filename = Path(pdf_path).stem
        self.output_dir = Path(output_dir or MD_FILES_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger_instance or logger

        # Image captioning with transformers (GPU/CPU aware)
        try:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.processor = ViTImageProcessor.from_pretrained("nlpconnect/vit-gpt2-image-captioning")
            self.model = VisionEncoderDecoderModel.from_pretrained("nlpconnect/vit-gpt2-image-captioning").to(self.device)
            self.tokenizer = AutoTokenizer.from_pretrained("nlpconnect/vit-gpt2-image-captioning")
            self.logger.info(f"Image captioning model ready (device: {self.device}).")
        except Exception as e:
            self.logger.warning(f"Transformers captioning unavailable ({e}). Falling back to OCR only.")
            self.processor = None
            self.model = None
            self.tokenizer = None

    def extract_links(self, page: fitz.Page) -> List[Dict]:
        """Extract hyperlinks from page."""
        links = []
        try:
            for link in page.get_links():
                if link.get("kind") == 2 and "uri" in link and "from" in link:
                    links.append({"rect": fitz.Rect(link["from"]), "uri": link["uri"]})
        except Exception as e:
            self.logger.debug(f"Link extraction error: {e}")
        return links

    def detect_code_block(self, prev_line: str, current_line: str) -> Optional[str]:
        """Heuristic code block detection; returns language or None."""
        patterns = {
            "python": [
                (r"^(?:from|import)\s+\w+", r"^(?:from|import|def|class|if|for|while|try|except|with)\s"),
                (r"^(?:def|class)\s+\w+", r"^\s{4}"),
                (r"^\s{4}", r"^\s{4,}"),
            ],
            "javascript": [
                (r"^(?:function|const|let|var)\s+\w+", r"^(?:function|const|let|var|if|for|while|try|catch|class)\s"),
                (r"^(?:if|for|while)\s*\(", r"^\s{2,}"),
                (r"^\s{2,}", r"^\s{2,}"),
            ],
            "html": [
                (r"^<(!DOCTYPE|html|head|body|div|p|a|script|style)", r"^<(!DOCTYPE|html|head|body|div|p|a|script|style)"),
                (r"^<\w+.*>$", r"^\s{2,}<"),
                (r"^\s{2,}<", r"^\s{2,}<"),
            ],
            "shell": [
                (r"^(?:\$|\#)\s", r"^(?:\$|\#)\s"),
                (r"^[a-z_]+\s*=", r"^[a-z_]+\s*="),
            ],
            "bash": [
                (r"^(?:#!/bin/bash|alias|export|source)\s", r"^(?:#!/bin/bash|alias|export|source|echo|read|if|for|while|case|function)\s"),
                (r"^(?:if|for|while|case|function)\s", r"^\s{2,}"),
                (r"^\s{2,}", r"^\s{2,}"),
            ],
            "cpp": [
                (r"^#include\s*<", r"^(?:#include|using|namespace|class|struct|enum|template|typedef)\s"),
                (r"^(?:class|struct|enum)\s+\w+", r"^\s{2,}"),
                (r"^\s{2,}", r"^\s{2,}"),
            ],
            "java": [
                (r"^(?:import|package)\s+\w+", r"^(?:import|package|public|private|protected|class|interface|enum)\s"),
                (r"^(?:public|private|protected)\s+class\s+\w+", r"^\s{4,}"),
                (r"^\s{4,}", r"^\s{4,}"),
            ],
            "json": [
                (r"^\s*{", r'^\s*["{[]'),
                (r'^\s*"', r'^\s*["}],?$'),
                (r"^\s*\[", r"^\s*[}\]],?$"),
            ],
        }
        for lang, pairs in patterns.items():
            for prev_pat, curr_pat in pairs:
                if re.match(prev_pat, prev_line.strip() or "") and re.match(curr_pat, current_line.strip() or ""):
                    return lang
        return None

    def is_bullet_point(self, text: str) -> bool:
        """Check if text starts with a bullet character."""
        return text.strip().startswith(tuple(self.BULLET_POINTS))

    def convert_bullet_to_markdown(self, text: str) -> str:
        """Convert bullet to Markdown list item."""
        text = re.sub(r"^\s*", "", text)
        return re.sub(rf"^[{re.escape(self.BULLET_POINTS)}]\s*", "- ", text)

    def is_numbered_list_item(self, text: str) -> bool:
        """Check if text is numbered list."""
        return bool(re.match(r"^\d+\s{0,3}[.)]", text.strip()))

    def convert_numbered_list_to_markdown(self, text: str, list_counter: int) -> str:
        """Convert numbered list to Markdown."""
        text = re.sub(r"^\s*", "", text)
        return re.sub(r"^\d+\s{0,3}[.)]", f"{list_counter}. ", text)

    def is_horizontal_line(self, text: str) -> bool:
        """Check if line is horizontal rule."""
        return bool(re.match(r"^[_-]+$", text.strip()))

    def clean_text(self, text: str) -> str:
        """Clean text: strip, normalize whitespace, and fix encoding issues."""
        text = text.strip()
        
        # Fix UTF-8 encoding issues (bullets and special chars)
        text = text.replace('\u2022', '•')  # bullet point
        text = text.replace('\u2019', "'")  # right single quotation
        text = text.replace('\u2018', "'")  # left single quotation  
        text = text.replace('\u201c', '"')  # left double quotation
        text = text.replace('\u201d', '"')  # right double quotation
        text = text.replace('\u2013', '–')  # en dash
        text = text.replace('\u2014', '—')  # em dash
        text = text.replace('\u2026', '...')  # ellipsis
        
        # Normalize whitespace
        text = re.sub(r"\s+", " ", text)
        return text

    def perform_ocr(self, image) -> str:
        """Perform OCR on image; return text or empty string."""
        if not _TESSERACT_PATH:
            return ""
        try:
            opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            ocr_result = pytesseract.image_to_data(opencv_image, output_type=pytesseract.Output.DICT)
            words = [w for w in ocr_result.get("text", []) if w and w.strip()]
            return " ".join(words[:30]).strip()
        except Exception:
            return ""

    def caption_image(self, image: Image.Image) -> str:
        """Generate caption for image: OCR first, then model if available."""
        # Prefer OCR; fallback to image captioning if available
        ocr_text = self.perform_ocr(image)
        if ocr_text:
            return ocr_text
        if not (self.processor and self.model and self.tokenizer):
            return ""
        try:
            if image.mode != "RGB":
                image = image.convert("RGB")
            inputs = self.processor(images=image, return_tensors="pt")
            pixel_values = inputs.pixel_values.to(self.device) if self.device else inputs.pixel_values
            generated_ids = self.model.generate(pixel_values, max_length=30)
            caption = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
            return caption.strip()
        except Exception:
            return ""

    def table_to_markdown(self, table: List[List[Optional[str]]]) -> str:
        """Convert table to GitHub-style Markdown table with better cell cleaning."""
        if not table:
            return ""
        
        try:
            # Clean and normalize cells - preserve bullet structure
            cleaned_table = []
            for row in table:
                cleaned_row = []
                for cell in row:
                    if cell is None:
                        cleaned_row.append("")
                    else:
                        # Convert to string and strip
                        cell_text = str(cell).strip()
                        
                        # Check if cell has bullets - preserve them with line breaks
                        if '•' in cell_text or '\u2022' in cell_text:
                            # Replace newlines before bullets with space + bullet for better formatting
                            cell_text = cell_text.replace('\n•', ' •').replace('\n\u2022', ' •')
                            cell_text = cell_text.replace('\u2022', '•')
                        
                        # Replace other newlines with spaces
                        cell_text = cell_text.replace('\n', ' ').replace('\r', ' ')
                        
                        # Collapse multiple spaces
                        cell_text = ' '.join(cell_text.split())
                        
                        # Apply UTF-8 cleaning
                        cell_text = self.clean_text(cell_text)
                        
                        cleaned_row.append(cell_text)
                cleaned_table.append(cleaned_row)
            
            if not cleaned_table:
                return ""
            
            # Calculate column widths
            col_widths = [max(len(cell) for cell in col) for col in zip(*cleaned_table)]
            
            # Build markdown
            markdown = ""
            for i, row in enumerate(cleaned_table):
                formatted_row = [cell.ljust(col_widths[j]) for j, cell in enumerate(row)]
                markdown += "| " + " | ".join(formatted_row) + " |\n"
                
                # Add separator after header row
                if i == 0:
                    markdown += "|" + "|".join(["-" * (width + 2) for width in col_widths]) + "|\n"
            
            return markdown
            
        except Exception as e:
            self.logger.error(f"Error converting table to markdown: {e}")
            self.logger.debug(traceback.format_exc())
            return ""

    def extract_tables(self) -> List[Dict]:
        """Extract tables from PDF using pdfplumber (default settings like comparison code)."""
        tables = []
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    # Use default table extraction (works best for most PDFs)
                    page_tables = page.extract_tables()
                    
                    # Skip pages with excessive tables (likely errors)
                    if len(page_tables) > 128:
                        self.logger.debug(f"Page {page_num} has {len(page_tables)} tables, skipping")
                        continue
                    
                    for table in page_tables:
                        # Filter out empty or malformed tables
                        if table and len(table) > 0:
                            # Check if table has meaningful content
                            non_empty_rows = [row for row in table if any(cell and str(cell).strip() for cell in row)]
                            if len(non_empty_rows) >= 2:  # At least header + 1 data row
                                tables.append({"page": page_num, "content": table})
                
                self.logger.info(f"Extracted {len(tables)} tables from PDF")
        except Exception as e:
            self.logger.error(f"Table extraction error: {e}")
            self.logger.debug(traceback.format_exc())
        return tables

    def process_image_block(self, page: fitz.Page, block: Dict) -> str:
        """Process image block: extract, save, caption."""
        try:
            rect = block["bbox"]
            pix = page.get_pixmap(clip=fitz.Rect(rect), matrix=fitz.Matrix(2.0, 2.0), alpha=False)
            image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            if image.width < 20 or image.height < 20:
                return ""
            image_filename = f"{self.pdf_filename}_image_{int(page.number)+1}_{block.get('number', 0)}.png"
            image_path = self.output_dir / image_filename
            image.save(image_path, "PNG", optimize=True, quality=95)
            
            # Try to generate a caption
            caption = self.caption_image(image)
            if not caption:
                # Better fallback than just filename - add descriptive text
                page_num = int(page.number) + 1
                caption = f"Image from page {page_num}"
            
            return f"![{caption}]({image_path})\n\n"
        except Exception as e:
            self.logger.debug(f"Image block processing error: {e}")
            return ""

    def get_header_level(self, font_size: float) -> int:
        """Determine header level from font size."""
        return 1 if font_size > 24 else 2 if font_size > 20 else 3 if font_size > 18 else 4 if font_size > 16 else 5 if font_size > 14 else 6 if font_size > 12 else 0

    def process_text_block(self, block: Dict, page_height: float, links: List[Dict], list_counter: int, in_code_block: bool, code_block_content: str, code_block_lang: Optional[str], prev_line: str):
        """Process text block: convert to Markdown with links, code blocks, lists."""
        try:
            block_rect = block["bbox"]
            # Skip likely headers/footers by position
            if block_rect[1] < 50 or block_rect[3] > page_height - 50:
                return ("", list_counter, in_code_block, code_block_content, code_block_lang, prev_line)

            block_text = ""
            last_y1 = None
            last_font_sizes = None

            for line in block.get("lines", []):
                line_text = ""
                curr_font_sizes = [span.get("size", 0) for span in line.get("spans", [])]

                for span in line.get("spans", []):
                    text = span.get("text", "")
                    font_size = span.get("size", 0)
                    flags = span.get("flags", 0)
                    span_rect = span.get("bbox", block_rect)

                    if self.is_horizontal_line(text):
                        line_text += "\n---\n"
                        continue

                    text = self.clean_text(text)
                    if text:
                        header_level = self.get_header_level(font_size)
                        if header_level > 0:
                            text = f"\n{'#' * header_level} {text}\n\n"
                        else:
                            # Check for bold text (flags & 16 or flags & 20)
                            is_bold = bool(flags & 16) or bool(flags & 20)
                            
                            if self.is_bullet_point(text):
                                m = re.match(rf"^([{re.escape(self.BULLET_POINTS)}])\s*(.*)", text)
                                if m:
                                    _, content = m.groups()
                                    text = f"- {self.clean_text(content)}"
                            elif self.is_numbered_list_item(text):
                                m = re.match(r"^(\d+\s{0,3}[.)])\s*(.*)", text)
                                if m:
                                    _, content = m.groups()
                                    list_counter += 1
                                    text = f"{list_counter}. {self.clean_text(content)}"
                            elif is_bold and not self.is_horizontal_line(text):
                                # Wrap bold text in markdown bold syntax
                                text = f"**{text}**"

                    # Check for hyperlinks
                    for link in links:
                        try:
                            if fitz.Rect(span_rect).intersects(link["rect"]):
                                text = f"[{text.strip()}]({link['uri']})"
                                break
                        except Exception:
                            pass

                    line_text += f" {text} "

                if last_y1 is not None:
                    avg_last = (sum(last_font_sizes) / len(last_font_sizes)) if last_font_sizes else 0
                    avg_curr = (sum(curr_font_sizes) / len(curr_font_sizes)) if curr_font_sizes else 0
                    font_changed = abs(avg_curr - avg_last) > 1
                    if abs(line.get('bbox', block_rect)[3] - last_y1) > 2 or font_changed:
                        block_text += "\n"

                block_text += self.clean_text(line_text) + " "
                last_font_sizes = curr_font_sizes
                last_y1 = line.get('bbox', block_rect)[3]

            markdown_content = ""
            lines = block_text.split("\n")
            for i, line in enumerate(lines):
                clean_line = self.clean_text(line)
                if not in_code_block:
                    lang = self.detect_code_block(prev_line, clean_line)
                    if lang:
                        in_code_block = True
                        code_block_lang = lang
                        code_block_content = (prev_line + "\n" if prev_line else "") + clean_line + "\n"
                        prev_line = clean_line
                        continue

                if in_code_block:
                    code_block_content += clean_line + "\n"
                    next_lang = self.detect_code_block(clean_line, lines[i + 1]) if i < len(lines) - 1 else None
                    if next_lang != code_block_lang:
                        markdown_content += f"```{code_block_lang}\n{code_block_content}```\n\n"
                        in_code_block = False
                        code_block_content = ""
                        code_block_lang = None
                else:
                    if self.is_bullet_point(clean_line):
                        markdown_content += "\n" + self.convert_bullet_to_markdown(clean_line)
                        list_counter = 0
                    elif self.is_numbered_list_item(clean_line):
                        list_counter += 1
                        markdown_content += "\n" + self.convert_numbered_list_to_markdown(clean_line, list_counter)
                    else:
                        markdown_content += f"{clean_line}\n"
                        list_counter = 0

                prev_line = clean_line

            return (markdown_content + "\n", list_counter, in_code_block, code_block_content, code_block_lang, prev_line)
        except Exception as e:
            self.logger.debug(f"Text block processing error: {e}")
            return ("", list_counter, in_code_block, code_block_content, code_block_lang, prev_line)

    def post_process_markdown(self, content: str) -> str:
        """Post-process Markdown: remove excessive newlines, page numbers, etc."""
        try:
            content = re.sub(r"\n{3,}", "\n\n", content)
            content = re.sub(r"(\d+)\s*\n", "", content)
            content = re.sub(r" +", " ", content)
            content = re.sub(r"\s*(---\n)+", "\n\n---\n", content)
            return content
        except Exception:
            return content

    def extract_markdown(self) -> Tuple[str, List[str]]:
        """Extract full Markdown from PDF with tables, images, links, code blocks."""
        try:
            doc = fitz.open(self.pdf_path)
            tables = self.extract_tables()
            table_index = 0

            markdown_content = ""
            markdown_pages: List[str] = []

            # Get table bounding boxes for each page to exclude from text extraction
            table_bboxes_by_page = {}
            try:
                with pdfplumber.open(self.pdf_path) as pdf:
                    for page_num, plumber_page in enumerate(pdf.pages):
                        page_tables = plumber_page.find_tables()
                        if page_tables:
                            table_bboxes_by_page[page_num] = [table.bbox for table in page_tables if table.bbox]
            except Exception as e:
                self.logger.warning(f"Could not get table bboxes: {e}")

            for page in doc:
                page_content = ""
                blocks = page.get_text("dict").get("blocks", [])
                page_height = page.rect.height
                links = self.extract_links(page)
                images = page.get_images()
                
                # Get table bboxes for this page
                page_table_bboxes = table_bboxes_by_page.get(page.number, [])

                list_counter = 0
                in_code_block = False
                code_block_content = ""
                code_block_lang = None
                prev_line = ""

                if 0 < len(images) <= 120:
                    for block in blocks:
                        if block.get("type") == 0:
                            # Check if block is within a table region
                            block_bbox = block.get("bbox", [])
                            is_in_table = False
                            if block_bbox and len(block_bbox) == 4:
                                for table_bbox in page_table_bboxes:
                                    # Check if block overlaps with table (with small tolerance)
                                    if (block_bbox[0] >= table_bbox[0] - 5 and 
                                        block_bbox[2] <= table_bbox[2] + 5 and
                                        block_bbox[1] >= table_bbox[1] - 5 and
                                        block_bbox[3] <= table_bbox[3] + 5):
                                        is_in_table = True
                                        break
                            
                            if not is_in_table:
                                block_md, list_counter, in_code_block, code_block_content, code_block_lang, prev_line = self.process_text_block(
                                    block, page_height, links, list_counter, in_code_block, code_block_content, code_block_lang, prev_line
                                )
                                page_content += block_md
                        elif block.get("type") == 1:
                            page_content += self.process_image_block(page, block)
                else:
                    for block in blocks:
                        if block.get("type") == 0:
                            # Check if block is within a table region
                            block_bbox = block.get("bbox", [])
                            is_in_table = False
                            if block_bbox and len(block_bbox) == 4:
                                for table_bbox in page_table_bboxes:
                                    # Check if block overlaps with table (with small tolerance)
                                    if (block_bbox[0] >= table_bbox[0] - 5 and 
                                        block_bbox[2] <= table_bbox[2] + 5 and
                                        block_bbox[1] >= table_bbox[1] - 5 and
                                        block_bbox[3] <= table_bbox[3] + 5):
                                        is_in_table = True
                                        break
                            
                            if not is_in_table:
                                block_md, list_counter, in_code_block, code_block_content, code_block_lang, prev_line = self.process_text_block(
                                    block, page_height, links, list_counter, in_code_block, code_block_content, code_block_lang, prev_line
                                )
                                page_content += block_md

                while table_index < len(tables) and tables[table_index]["page"] == page.number:
                    page_content += "\n\n" + self.table_to_markdown(tables[table_index]["content"]) + "\n\n"
                    table_index += 1

                page_md = self.post_process_markdown(page_content)
                markdown_pages.append(page_md)
                markdown_content += page_md + PAGE_DELIMITER

            markdown_content = self.post_process_markdown(markdown_content)
            return markdown_content, markdown_pages
        except Exception as e:
            self.logger.error(f"Markdown extraction error: {e}", exc_info=True)
            return "", []

    def save_markdown(self, markdown_content: str, out_path: Optional[str] = None) -> Path:
        """Save Markdown content to file."""
        out_path = Path(out_path) if out_path else (self.output_dir / f"{self.pdf_filename}.md")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        return out_path

    def convert_pdf_to_md(self, out_path: Optional[str] = None) -> Path:
        """Main entry: extract and save Markdown."""
        md, _ = self.extract_markdown()
        return self.save_markdown(md, out_path)


def convert_pdf_to_md(pdf_path: str, out_path: Optional[str] = None) -> Optional[str]:
    """
    Secondary artifact generator: Convert a PDF to Markdown (links, images, tables, code blocks).
    Leaves primary JSON pipeline untouched.
    """
    try:
        generator = MarkdownPDFGenerator(pdf_path, output_dir=MD_FILES_DIR, logger_instance=logger)
        out = generator.convert_pdf_to_md(out_path)
        logger.info(f"Markdown written to {out}")
        return str(out)
    except Exception as e:
        logger.error(f"Failed to generate Markdown for {pdf_path}: {e}", exc_info=True)
        return None


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


def main_md(argv: Optional[List[str]] = None) -> int:
    """
    Optional CLI for Markdown generation without affecting primary JSON flow.
    Usage: python scripts/data_extraction.py --md <pdf_path> [--out <file_or_dir>]
    """
    parser = argparse.ArgumentParser(description="Convert a single PDF to Markdown (secondary artifact).")
    parser.add_argument("--md", dest="pdf_path", help="Path to PDF to convert to Markdown.")
    parser.add_argument("--out", dest="out_path", help="Optional output file or directory for Markdown.")
    args = parser.parse_args(argv)
    
    if not args.pdf_path:
        print("Provide --md <pdf_path> to generate Markdown.")
        return 2
    
    result = convert_pdf_to_md(args.pdf_path, args.out_path)
    return 0 if result else 1


if __name__ == "__main__":
    # Check if --md flag is present for Markdown generation
    if "--md" in sys.argv:
        exit_code = main_md()
    else:
        exit_code = main()
    sys.exit(exit_code)

