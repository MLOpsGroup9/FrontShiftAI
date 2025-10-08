"""
FrontShiftAI – PDF → Q&A Dataset Generator
------------------------------------------
Usage:
    python generate_qna_from_pdfs.py

Inputs:
    - List of PDF file paths (edit pdf_files[] or pass as CLI args)
Outputs:
    - data/qna/qa.jsonl : consolidated Q&A dataset

Dependencies:
    pip install PyPDF2 nltk
    python -m nltk.downloader punkt
"""

import os
import re
import json
import random
from typing import List
from PyPDF2 import PdfReader
import nltk
nltk.download('punkt_tab')
from nltk.tokenize import sent_tokenize


# ---------------------------------------------------------
# 1️⃣ EXTRACT TEXT FROM PDF
# ---------------------------------------------------------
def extract_text_from_pdf(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    text = []
    for page in reader.pages:
        try:
            content = page.extract_text()
            if content:
                text.append(content)
        except Exception as e:
            print(f"⚠️ Error reading {pdf_path}: {e}")
    return "\n".join(text)


# ---------------------------------------------------------
# 2️⃣ CLEAN TEXT
# ---------------------------------------------------------
def clean_text(text: str) -> str:
    text = re.sub(r"Page\s*\d+|\d+\s*/\s*\d+", "", text)
    text = re.sub(r"\n+", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


# ---------------------------------------------------------
# 3️⃣ DETECT SECTIONS (HEADINGS)
# ---------------------------------------------------------
def detect_sections(text: str):
    sections = []
    lines = text.split("\n")
    current_title = None
    current_body = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Short uppercase/title lines likely indicate new section
        if len(line.split()) <= 8 and not line.endswith(".") and (
            line.isupper() or line.istitle()
        ):
            if current_title and current_body:
                sections.append((current_title, " ".join(current_body)))
            current_title = line
            current_body = []
        else:
            current_body.append(line)

    if current_title and current_body:
        sections.append((current_title, " ".join(current_body)))

    return sections


# ---------------------------------------------------------
# 4️⃣ QUESTION TEMPLATE GENERATOR
# ---------------------------------------------------------
def get_question_templates(title: str) -> List[str]:
    title_lower = title.lower()

    templates = [
        # --- General Policy ---
        f"What is the policy on {title_lower}?",
        f"What does the company say about {title_lower}?",
        f"Can you explain the {title_lower} policy?",
        f"What are the guidelines for {title_lower}?",
        f"What are the rules related to {title_lower}?",
        f"Is there a policy covering {title_lower}?",

        # --- Eligibility & Applicability ---
        f"Who is eligible for {title_lower}?",
        f"Who does the {title_lower} policy apply to?",
        f"Who is covered under {title_lower}?",
        f"Does {title_lower} apply to part-time or full-time employees?",
        f"When does {title_lower} apply?",
        f"Under what conditions does {title_lower} apply?",
        f"Are any employees excluded from {title_lower}?",

        # --- Process / Procedure ---
        f"How does {title_lower} work?",
        f"How can employees request {title_lower}?",
        f"What steps must be followed for {title_lower}?",
        f"How should employees report or record {title_lower}?",
        f"Who should employees contact regarding {title_lower}?",
        f"What documentation is required for {title_lower}?",

        # --- Benefits / Entitlements ---
        f"What benefits are provided under {title_lower}?",
        f"How much time or pay is given for {title_lower}?",
        f"Are employees compensated for {title_lower}?",

        # --- Restrictions / Exceptions ---
        f"Are there any exceptions to {title_lower}?",
        f"What actions are prohibited under {title_lower}?",
        f"What happens if an employee violates the {title_lower} policy?",
        f"Are prior approvals required for {title_lower}?",
    ]

    # Domain-specific enrichment
    if any(k in title_lower for k in ["leave", "vacation", "absence", "holiday"]):
        templates += [
            f"How many days of {title_lower} are allowed?",
            f"Is {title_lower} paid or unpaid?",
            f"Can unused {title_lower} be carried over?",
        ]
    elif any(k in title_lower for k in ["pay", "wage", "salary", "bonus"]):
        templates += [
            f"How is {title_lower} calculated?",
            f"When is {title_lower} paid?",
            f"Is overtime included in {title_lower}?",
        ]
    elif any(k in title_lower for k in ["conduct", "behavior", "discipline", "ethics"]):
        templates += [
            f"What behaviors violate the {title_lower} policy?",
            f"What are the consequences of violating {title_lower}?",
        ]

    # Sample 6 random templates for variety
    random.shuffle(templates)
    return templates[:6]


# ---------------------------------------------------------
# 5️⃣ Q&A EXTRACTION FROM SECTION
# ---------------------------------------------------------
def extract_qna_from_section(title: str, content: str, source: str):
    qna_pairs = []
    sentences = sent_tokenize(content)

    # Policy-relevant sentences
    policy_sents = [
        s for s in sentences
        if re.search(
            r"\b(must|should|will|required|entitled|eligible|prohibited|hours|days|rate|approval|notify|leave|holiday|break|bonus|disciplinary|violate)\b",
            s,
            re.IGNORECASE,
        )
    ]
    if not policy_sents:
        return []

    context = " ".join(sentences[:5])
    templates = get_question_templates(title)

    for t in templates:
        for s in policy_sents[:2]:  # only first two to limit redundancy
            qna_pairs.append({
                "section": title,
                "question": t,
                "answer": s.strip(),
                "context": context.strip(),
                "source_doc": os.path.basename(source)
            })
    return qna_pairs


# ---------------------------------------------------------
# 6️⃣ MAIN PIPELINE
# ---------------------------------------------------------
def generate_qna_from_pdfs(pdf_paths: List[str], output_path: str = "data/qna/qa.jsonl"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    all_qna = []

    for pdf in pdf_paths:
        print(f"📘 Processing: {pdf}")
        text = extract_text_from_pdf(pdf)
        cleaned = clean_text(text)
        sections = detect_sections(cleaned)
        print(f"   ➜ Found {len(sections)} sections")

        for title, content in sections:
            pairs = extract_qna_from_section(title, content, pdf)
            all_qna.extend(pairs)

    # Deduplicate
    seen = set()
    unique_qna = []
    for qa in all_qna:
        key = (qa["question"].lower(), qa["answer"].lower())
        if key not in seen:
            seen.add(key)
            unique_qna.append(qa)

    with open(output_path, "w") as f:
        for qa in unique_qna:
            f.write(json.dumps(qa) + "\n")

    print(f"\n✅ Generated {len(unique_qna)} unique Q&A pairs")
    print(f"💾 Saved to: {output_path}")


# ---------------------------------------------------------
# 7️⃣ ENTRY POINT
# ---------------------------------------------------------
if __name__ == "__main__":
    # Supply up to 5 PDFs here
    pdf_files = [
        "data/raw/cmp-employee-handbook.pdf",
        "data/raw/8.-Employee-Handbook-v4.8.pdf",
        "data/raw/APL-Empl-Manual-Revised-12-22-16-fixed.pdf",
        "data/raw/EmployeeHandbook_20190926.pdf",
        "data/raw/Jacob-HAC-Employee-Handbook.pdf",
    ]
    generate_qna_from_pdfs(pdf_files, output_path="data/qna/qa.jsonl")
