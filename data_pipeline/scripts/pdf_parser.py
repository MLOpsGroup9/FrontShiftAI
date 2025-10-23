import os
import re
import sys
import json
import logging
import traceback
import warnings
import shutil
import pymupdf as fitz 
import cv2
import numpy as np 
import argparse
import pytesseract
import pdfplumber
from pathlib import Path
from PIL import Image
from typing import List, Dict, Optional
from abc import ABC, abstractmethod
from requests import RequestException
import requests

from dotenv import load_dotenv
load_dotenv()

"""This scripts loads the downloaded pdfs from the raw data folder, converts each pdf into markdown and stores the markdowns in a new folder called parsed. Every pdf will be converted to a single 
markdown, the tables will also be converted to markdown, the images will be captioned using a Vision Transformer but will first go through PyTessaract for OCR. This script also will involve
cleaning the markdown 
"""
BASE_DIR = Path(__file__).resolve().parents[1]  # one level up from scripts/
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

RAW_PDF_DIR = Path(os.getenv("RAW_DATA_DIR", DATA_DIR / "raw"))
PROCESSED_PDF_DIR = Path(os.getenv("PROCESSED_PDF_DIR", DATA_DIR / "parsed"))
LOG_DIR = Path(os.getenv("LOG_DIR", LOGS_DIR / "processed_pdf_log"))
PAGE_DELIMITER = os.getenv("PAGE_DELIMITER", "\n\n---\n\n")

RAW_PDF_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_PDF_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)


def _configure_tesseract() -> Optional[str]:
    """Resolve the Tesseract binary path and configure pytesseract."""
    candidates = [
        os.getenv("TESSERACT_CMD"),
        shutil.which("tesseract"),
        "/opt/homebrew/bin/tesseract",  
        "/usr/local/bin/tesseract",     
        "/usr/bin/tesseract",           
        "C:/Program Files/Tesseract-OCR/tesseract.exe",  
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


TESSERACT_PATH = _configure_tesseract()
TESSERACT_AVAILABLE = TESSERACT_PATH is not None

if not TESSERACT_AVAILABLE:
    logging.getLogger(__name__).warning(
        "Tesseract executable not detected. Set TESSERACT_CMD or update your PATH to enable OCR."
    )


class PDFExtractor(ABC):
    """Abstract base class for PDF Extraction."""
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.setup_logging()

    def setup_logging(self):
        """Set up logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(os.path.join(LOG_DIR, "processed_pdf.log"), encoding="utf-8"),
                logging.StreamHandler(),
            ],
        )
        self.logger = logging.getLogger(__name__)

    @abstractmethod
    def extract(self):
        """Abstract method for extracting content from PDF."""
        pass 


class MarkdownPDFExtractor(PDFExtractor):
    """Class for extracting markdown-formatted content from PDF."""

    BULLET_POINTS = "•◦▪▫●○"

    def __init__(self, pdf_path):
        super().__init__(pdf_path)
        self.pdf_filename = Path(pdf_path).stem
        parts = self.pdf_filename.split("_", 1)
        self.domain = parts[0] if len(parts) > 0 else "unknown_domain"
        self.company = parts[1] if len(parts) > 1 else "unknown_company"
        Path(PROCESSED_PDF_DIR)
        self.setup_image_captioning()

    def setup_image_captioning(self):
        """Set up the vision model API client."""
        self.api_base_url = os.getenv("VISION_MODEL_API_URL", "http://localhost:8000").rstrip("/")
        self.caption_endpoint = f"{self.api_base_url}/caption"
        self.health_endpoint = f"{self.api_base_url}/health"

        try:
            response = requests.get(self.health_endpoint, timeout=5)
            response.raise_for_status()
            self.logger.info(
                "Connected to vision captioning service at %s (device: %s)",
                self.api_base_url,
                response.json().get("device", "unknown"),
            )
        except RequestException as exc:
            self.logger.warning(
                "Vision captioning service unavailable at %s: %s",
                self.api_base_url,
                exc,
            )

    
    def extract(self):
        try:
            markdown_content, markdown_pages = self.extract_markdown()
            self.save_markdown(markdown_content)
            self.logger.info(
                f"Markdown content has been saved to {Path(PROCESSED_PDF_DIR)}/{self.pdf_path}.md"
            )
            return markdown_content, markdown_pages
        
        except Exception as e:
            self.logger.error(f"Error processing PDF: {e}")
            self.logger.exception(traceback.format_exc())
            return "", []
        

    def extract_markdown(self):
        """Main method to extract markdown from PDF."""
        try: 
            doc = fitz.open(self.pdf_path)
            markdown_content = ""
            markdown_pages = []
            tables = self.extract_tables()
            table_index = 0
            list_counter = 0
            in_code_block = False
            code_block_content = ""
            code_block_lang = None
            prev_line = ""

            for page_num, page in enumerate(doc):
                self.logger.info(f"Processing page {page_num + 1}")
                page_content = ""
                blocks = page.get_text("dict")["blocks"]
                page_height = page.rect.height
                links = self.extract_links(page)
                images = page.get_images()

                if 0 < len(images) <= 120:
                    for block in blocks:
                        if block["type"] == 0:
                            (
                                block_markdown,
                                list_counter,
                                in_code_block,
                                code_block_content,
                                code_block_lang,
                                prev_line,
                            ) = self.process_text_block(
                                block,
                                page_height,
                                links,
                                list_counter,
                                in_code_block,
                                code_block_content,
                                code_block_lang,
                                prev_line,
                            )
                            page_content += block_markdown
                        elif block["type"] == 1: 
                            page_content += self.process_image_block(page, block)

                else:
                    for block in blocks:
                        if block["type"] == 0:
                            (
                                block_markdown,
                                list_counter,
                                in_code_block,
                                code_block_content,
                                code_block_lang,
                                prev_line,
                            ) = self.process_text_block(
                                block,
                                page_height,
                                links,
                                list_counter,
                                in_code_block,
                                code_block_content,
                                code_block_lang,
                                prev_line,
                            )
                            page_content += block_markdown
                # Insert tables at their approximate positions
                while(
                    table_index < len(tables)
                    and tables[table_index]["page"] == page.number
                ):
                    page_content += (
                        "\n\n"
                        + self.table_to_markdown(tables[table_index]["content"])
                        + "\n\n"
                    )
                    table_index += 1

                markdown_pages.append(self.post_process_markdown(page_content))
                markdown_content += page_content + PAGE_DELIMITER


            markdown_content = self.post_process_markdown(markdown_content)
            return markdown_content, markdown_pages
        
        except Exception as e:
            self.logger.error(f"Error extracting markdown: {e}")
            self.logger.exception(traceback.format_exc())
            return "", []
        

    def extract_tables(self):
        """Extract tables from PDF using pdfplumber."""
        tables = []
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page_number, page in enumerate(pdf.pages):
                    page_tables = page.extract_tables()
                    if len(page_tables) > 128:
                        continue
                    for table in page_tables:
                        tables.append({"page": page_number, "content": table})
            self.logger.info(f"Extracted {len(tables)} tables from the PDF.")

        except Exception as e:
            self.logger.error(f"Error extracting tables: {e}")
            self.logger.exception(traceback.format_exc())
        return tables
    
    def table_to_markdown(self, table):
        """Convert a table to markdown format."""
        if not table:
            return ""
        
        try:
            table = [
                ["" if cell is None else str(cell).strip() for cell in row]
                for row in table
            ]
            col_widths = [max(len(cell) for cell in col) for col in zip(*table)]

            markdown = ""
            for i, row in enumerate(table):
                formatted_row = [
                    cell.ljust(col_widths[j]) for j, cell in enumerate(row)
                ]
                markdown += "| " + " | ".join(formatted_row) + " |\n"

                if i == 0:
                    markdown += (
                        "|" + "|".join(["-" * (width + 2) for width in col_widths]) + "|\n"
                    )

            return markdown
        
        except Exception as e:
            self.logger.error(f"Error converting table to markdown: {e}")
            self.logger.exception(traceback.format_exc())
            return ""
        
    def perform_ocr(self, image):
        """Perform OCR on the given image."""
        try:
            if not TESSERACT_AVAILABLE:
                self.logger.debug("Skipping OCR because Tesseract is unavailable.")
                return ""

            opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            ocr_result = pytesseract.image_to_data(
                opencv_image, output_type=pytesseract.Output.DICT
            )

            result = ""
            for word in ocr_result["text"]:
                if word.strip() != "":
                    result += word + " "

                if len(result) > 30:
                    break
            return result.strip()

        except Exception as e:
            self.logger.error(f"Error performing OCR: {e}")
            self.logger.exception(traceback.format_exc())
            return ""

    def caption_image(self, image: Image.Image, image_path: Path) -> str:
        """Generate a caption for the given image via OCR fallback or vision model API."""
        try:
            ocr_text = self.perform_ocr(image)
            if ocr_text:
                return ocr_text

            # Convert image to RGB if it's not already
            if image.mode != "RGB":
                image = image.convert("RGB")

            payload = {
                "image_path": str(image_path),
            }

            response = requests.post(self.caption_endpoint, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()

            caption = data.get("caption")
            if caption:
                return caption.strip()

            self.logger.warning(
                "Vision model API returned no caption for %s; falling back to filename.",
                image_path,
            )
            return ""
        except RequestException as exc:
            self.logger.error(
                "Error calling vision captioning service for %s: %s",
                image_path,
                exc,
            )
            return ""
        except Exception as e:
            self.logger.error(f"Error captioning image: {e}")
            self.logger.exception(traceback.format_exc())
            return ""

    def clean_text(self, text):
        """Clean the given text by removing extra spaces."""
        text = text.strip()
        text = re.sub(r"\s+", " ", text)
        return text

    def apply_formatting(self, text, flags):
        """Apply markdown formatting to the given text based on flags."""
        text = text.strip()
        if not text:
            return text

        is_bold = flags & 2**4
        is_italic = flags & 2**1
        is_monospace = flags & 2**3
        is_superscript = flags & 2**0
        is_subscript = flags & 2**5

        if is_monospace:
            text = f"`{text}`"
        elif is_superscript and not bool(re.search(r"\s+", text)):
            text = f"^{text}^"
        elif is_subscript and not bool(re.search(r"\s+", text)):
            text = f"~{text}~"

        if is_bold and is_italic:
            text = f"***{text}***"
        elif is_bold:
            text = f"**{text}**"
        elif is_italic:
            text = f"*{text}*"

        return f" {text} "

    def is_bullet_point(self, text):
        """Check if the given text is a bullet point."""
        return text.strip().startswith(tuple(self.BULLET_POINTS))

    def convert_bullet_to_markdown(self, text):
        """Convert a bullet point to markdown format."""
        text = re.sub(r"^\s*", "", text)
        return re.sub(rf"^[{re.escape(self.BULLET_POINTS)}]\s*", "- ", text)

    def is_numbered_list_item(self, text):
        """Check if the given text is a numbered list item."""
        return bool(re.match(r"^\d+\s{0,3}[.)]", text.strip()))

    def convert_numbered_list_to_markdown(self, text, list_counter):
        """Convert a numbered list item to markdown format."""
        text = re.sub(r"^\s*", "", text)
        return re.sub(r"^\d+\s{0,3}[.)]", f"{list_counter}. ", text)

    def is_horizontal_line(self, text):
        """Check if the given text represents a horizontal line."""
        return bool(re.match(r"^[_-]+$", text.strip()))

    def extract_links(self, page):
        """Extract links from the given page."""
        links = []
        try:
            for link in page.get_links():
                if link["kind"] == 2:  # URI link
                    links.append({"rect": link["from"], "uri": link["uri"]})
            self.logger.info(f"Extracted {len(links)} links from the page.")
        except Exception as e:
            self.logger.error(f"Error extracting links: {e}")
            self.logger.exception(traceback.format_exc())
        return links

    def detect_code_block(self, prev_line, current_line):
        """Detect if the current line starts a code block."""
        patterns = {
            "python": [
                (
                    r"^(?:from|import)\s+\w+",
                    r"^(?:from|import|def|class|if|for|while|try|except|with)\s",
                ),
                (r"^(?:def|class)\s+\w+", r"^\s{4}"),
                (r"^\s{4}", r"^\s{4,}"),
            ],
            "javascript": [
                (
                    r"^(?:function|const|let|var)\s+\w+",
                    r"^(?:function|const|let|var|if|for|while|try|catch|class)\s",
                ),
                (r"^(?:if|for|while)\s*\(", r"^\s{2,}"),
                (r"^\s{2,}", r"^\s{2,}"),
            ],
            "html": [
                (
                    r"^<(!DOCTYPE|html|head|body|div|p|a|script|style)",
                    r"^<(!DOCTYPE|html|head|body|div|p|a|script|style)",
                ),
                (r"^<\w+.*>$", r"^\s{2,}<"),
                (r"^\s{2,}<", r"^\s{2,}<"),
            ],
            "shell": [
                (r"^(?:\$|\#)\s", r"^(?:\$|\#)\s"),
                (r"^[a-z_]+\s*=", r"^[a-z_]+\s*="),
            ],
            "bash": [
                (
                    r"^(?:#!/bin/bash|alias|export|source)\s",
                    r"^(?:#!/bin/bash|alias|export|source|echo|read|if|for|while|case|function)\s",
                ),
                (r"^(?:if|for|while|case|function)\s", r"^\s{2,}"),
                (r"^\s{2,}", r"^\s{2,}"),
            ],
            "cpp": [
                (
                    r"^#include\s*<",
                    r"^(?:#include|using|namespace|class|struct|enum|template|typedef)\s",
                ),
                (r"^(?:class|struct|enum)\s+\w+", r"^\s{2,}"),
                (r"^\s{2,}", r"^\s{2,}"),
            ],
            "java": [
                (
                    r"^(?:import|package)\s+\w+",
                    r"^(?:import|package|public|private|protected|class|interface|enum)\s",
                ),
                (r"^(?:public|private|protected)\s+class\s+\w+", r"^\s{4,}"),
                (r"^\s{4,}", r"^\s{4,}"),
            ],
            "json": [
                (r"^\s*{", r'^\s*["{[]'),
                (r'^\s*"', r'^\s*["}],?$'),
                (r"^\s*\[", r"^\s*[}\]],?$"),
            ],
        }

        for lang, pattern_pairs in patterns.items():
            for prev_pattern, curr_pattern in pattern_pairs:
                if re.match(prev_pattern, prev_line.strip()) and re.match(
                    curr_pattern, current_line.strip()
                ):
                    return lang

        return None

    def process_text_block(
        self,
        block,
        page_height,
        links,
        list_counter,
        in_code_block,
        code_block_content,
        code_block_lang,
        prev_line,
    ):
        """Process a text block and convert it to markdown."""
        try:
            block_rect = block["bbox"]
            if block_rect[1] < 50 or block_rect[3] > page_height - 50:
                return (
                    "",
                    list_counter,
                    in_code_block,
                    code_block_content,
                    code_block_lang,
                    prev_line,
                )  # Skip headers and footers

            block_text = ""
            last_y1 = None
            last_font_size = None

            for line in block["lines"]:
                line_text = ""
                curr_font_size = [span["size"] for span in line["spans"]]

                for span in line["spans"]:
                    text = span["text"]
                    font_size = span["size"]
                    flags = span["flags"]
                    span_rect = span["bbox"]

                    if self.is_horizontal_line(text):
                        line_text += "\n---\n"
                        continue

                    text = self.clean_text(text)

                    if text.strip():
                        header_level = self.get_header_level(font_size)
                        if header_level > 0:
                            text = f"\n{'#' * header_level} {text}\n\n"

                        else:
                            is_bullet = self.is_bullet_point(text)
                            is_numbered = self.is_numbered_list_item(text)

                            if is_bullet or is_numbered:
                                if is_bullet:
                                    match = re.match(
                                        rf"^([{re.escape(self.BULLET_POINTS)}])\s*(.*)",
                                        text,
                                    )
                                    if match:
                                        marker, content = match.groups()
                                        formatted_content = (
                                            self.apply_formatting(content, flags).strip()
                                        )
                                        text = f"{marker} {formatted_content}"
                                    else:
                                        text = self.apply_formatting(text, flags)
                                else:
                                    match = re.match(
                                        r"^(\d+\s{0,3}[.)])\s*(.*)", text.strip()
                                    )
                                    if match:
                                        marker, content = match.groups()
                                        formatted_content = (
                                            self.apply_formatting(content, flags).strip()
                                        )
                                        text = f"{marker} {formatted_content}"
                                    else:
                                        text = self.apply_formatting(text, flags)
                            else:
                                text = self.apply_formatting(text, flags)

                    for link in links:
                        if fitz.Rect(span_rect).intersects(link["rect"]):
                            text = f"[{text.strip()}]({link['uri']})"
                            break

                    line_text += text

                if last_y1 is not None:
                    avg_last_font_size = (
                        sum(last_font_size) / len(last_font_size)
                        if last_font_size
                        else 0
                    )
                    avg_current_font_size = sum(curr_font_size) / len(curr_font_size)
                    font_size_changed = (
                        abs(avg_current_font_size - avg_last_font_size) > 1
                    )

                    if abs(line["bbox"][3] - last_y1) > 2 or font_size_changed:
                        block_text += "\n"

                block_text += self.clean_text(line_text) + " "
                last_font_size = curr_font_size
                last_y1 = line["bbox"][3]

            markdown_content = ""
            lines = block_text.split("\n")
            for i, line in enumerate(lines):
                clean_line = self.clean_text(line)

                if not in_code_block:
                    code_lang = self.detect_code_block(prev_line, clean_line)
                    if code_lang:
                        in_code_block = True
                        code_block_lang = code_lang
                        code_block_content = prev_line + "\n" + clean_line + "\n"
                        prev_line = clean_line
                        continue

                if in_code_block:
                    code_block_content += clean_line + "\n"
                    if (
                        i == len(lines) - 1
                        or self.detect_code_block(clean_line, lines[i + 1])
                        != code_block_lang
                    ):
                        markdown_content += (
                            f"```{code_block_lang}\n{code_block_content}```\n\n"
                        )
                        in_code_block = False
                        code_block_content = ""
                        code_block_lang = None
                else:
                    if self.is_bullet_point(clean_line):
                        markdown_content += "\n" + self.convert_bullet_to_markdown(
                            clean_line
                        )
                        list_counter = 0
                    elif self.is_numbered_list_item(clean_line):
                        list_counter += 1
                        markdown_content += (
                            "\n"
                            + self.convert_numbered_list_to_markdown(
                                clean_line, list_counter
                            )
                        )
                    else:
                        markdown_content += f"{clean_line}\n"
                        list_counter = 0

                prev_line = clean_line

            return (
                markdown_content + "\n",
                list_counter,
                in_code_block,
                code_block_content,
                code_block_lang,
                prev_line,
            )
        except Exception as e:
            self.logger.error(f"Error processing text block: {e}")
            self.logger.exception(traceback.format_exc())
            return (
                "",
                list_counter,
                in_code_block,
                code_block_content,
                code_block_lang,
                prev_line,
            )

    def process_image_block(self, page, block):
        """Process an image block and convert it to markdown."""
        try:
            image_rect = block["bbox"]
            zoom_x = 2.0  # horizontal zoom
            zoom_y = 2.0  # vertical zoom
            mat = fitz.Matrix(zoom_x, zoom_y)  # zoom factor 2 in each dimension
            pix = page.get_pixmap(clip=image_rect, matrix=mat, alpha=False)
            image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            if image.width < 20 or image.height < 20:
                return ""

            image_filename = (
                f"{self.pdf_filename}_image_{int(page.number)+1}_{block['number']}.png"
            )
            image_path = (
                Path(PROCESSED_PDF_DIR) / image_filename
            )  # Convert to Path object
            #image.save(image_path, "PNG", optimize=True, quality=95)

            caption = self.caption_image(image, image_path)
            if not caption:
                caption = (
                    f"{self.pdf_filename}_image_{int(page.number)+1}_{block['number']}"
                )

            return f"![{caption}]({image_path})\n\n"  # image_path is now a Path object
        except Exception as e:
            self.logger.error(f"Error processing image block: {e}")
            self.logger.exception(traceback.format_exc())
            return ""

    def get_header_level(self, font_size):
        """Determine header level based on font size."""
        if font_size > 24:
            return 1
        elif font_size > 20:
            return 2
        elif font_size > 18:
            return 3
        elif font_size > 16:
            return 4
        elif font_size > 14:
            return 5
        elif font_size > 12:
            return 6
        else:
            return 0

    def post_process_markdown(self, markdown_content):
        """Post-process the markdown content."""
        try:
            markdown_content = re.sub(
                r"\n{3,}", "\n\n", markdown_content
            )  # Remove excessive newlines
            markdown_content = re.sub(
                r"(\d+)\s*\n", "", markdown_content
            )  # Remove page numbers
            markdown_content = re.sub(
                r" +", " ", markdown_content
            )  # Remove multiple spaces
            markdown_content = re.sub(
                r"\s*(---\n)+", "\n\n---\n", markdown_content
            )  # Remove duplicate horizontal lines

            def remove_middle_headers(match):
                line = match.group(0)
                # Keep the initial header and remove all subsequent '#' characters
                return re.sub(
                    r"(^#{1,6}\s).*?(?=\n)",
                    lambda m: m.group(1)
                    + re.sub(r"#", "", m.group(0)[len(m.group(1)) :]),
                    line,
                )

            markdown_content = re.sub(
                r"^#{1,6}\s.*\n",
                remove_middle_headers,
                markdown_content,
                flags=re.MULTILINE,
            )  # Remove headers in the middle of lines
            return markdown_content
        except Exception as e:
            self.logger.error(f"Error post-processing markdown: {e}")
            self.logger.exception(traceback.format_exc())
            return markdown_content

    def save_markdown(self, markdown_content):
        """Save the markdown content to a file."""
        try:
            os.makedirs(Path(PROCESSED_PDF_DIR), exist_ok=True)
            output_path = Path(PROCESSED_PDF_DIR) / f"{self.domain}_{self.company}.md"
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            self.logger.info("Markdown content saved successfully.")
        except Exception as e:
            self.logger.error(f"Error saving markdown content: {e}")
            self.logger.exception(traceback.format_exc())



def convert_pdf_to_md(pdf_path: str, out_path: Optional[str] = None) -> Path:
    """
    Convert a PDF file to markdown and write to out_path.
    """
    pdf_path_obj = Path(pdf_path)
    default_dir = Path(PROCESSED_PDF_DIR)

    if out_path:
        out_path_obj = Path(out_path)
        if out_path_obj.suffix.lower() == ".md":
            target_path = out_path_obj
            target_dir = target_path.parent
            if target_dir == Path("."):
                target_dir = default_dir
        else:
            target_dir = out_path_obj
            target_path = target_dir / f"{pdf_path_obj.stem}.md"
    else:
        target_dir = default_dir
        target_path = target_dir / f"{pdf_path_obj.stem}.md"

    target_dir.mkdir(parents=True, exist_ok=True)

    extractor = MarkdownPDFExtractor(str(pdf_path_obj))
    markdown_content, markdown_pages = extractor.extract()
    try:
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        logging.info(f"Markdown written to {target_path}")
    except Exception as e:
        logging.error(f"Failed to write markdown to {target_path}: {e}")
    return target_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "pdf_path",
        nargs="?",  # optional
        help="Path to a single PDF file. If not provided, all PDFs in RAW_PDF_DIR will be processed.",
    )
    parser.add_argument(
        "--out",
        dest="out_path",
        help="Optional output file or directory. Defaults to PROCESSED_PDF_DIR.",
    )
    args = parser.parse_args()

    if args.pdf_path:
        convert_pdf_to_md(args.pdf_path, args.out_path)
    else:
        raw_dir = Path(RAW_PDF_DIR)
        pdf_files = list(raw_dir.glob("*.pdf"))
        if not pdf_files:
            print(f"No PDFs found in {raw_dir}")
            sys.exit(0)
        for pdf_file in pdf_files:
            convert_pdf_to_md(pdf_file)
