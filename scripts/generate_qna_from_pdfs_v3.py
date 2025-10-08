"""
FrontShiftAI – PDF → Q&A Dataset Generator (v2)
------------------------------------------------
Fixes:
  ✅ Wrong section bleed
  ✅ Average readable Q&A quality
"""

import os
import re
import json
import random
from typing import List
from PyPDF2 import PdfReader
import nltk
nltk.download("punkt", quiet=True)
from nltk.tokenize import sent_tokenize


# ---------------------------------------------------------
# 1️⃣ EXTRACT TEXT
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
    text = text.replace("\u2026", " ").replace("•", "-").replace("–", "-")
    text = re.sub(r"Page\s*\d+|\d+\s*/\s*\d+", "", text)
    text = re.sub(r"[•·]+", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


# ---------------------------------------------------------
# 3️⃣ DETECT SECTIONS (cleaned + merged)
# ---------------------------------------------------------
def detect_sections(text: str):
    lines = text.split("\n")
    sections = []
    current_title, current_body = None, []

    def finalize_section(title, body):
        if title and len(" ".join(body)) > 100:
            return (title.strip(), " ".join(body).strip())
        return None

    for line in lines:
        line = re.sub(r"[.•·…\u2026]+", "", line).strip()
        line = re.sub(r"\s*\d+$", "", line).strip()
        if not line:
            continue

        # Skip headers
        if re.search(r"(index|contents|mission|vision|table|foreword)", line, re.IGNORECASE):
            continue

        # Detect new heading
        if len(line.split()) <= 8 and not line.endswith(".") and (
            line.isupper() or line.istitle()
        ):
            # If previous body too short, merge with next one
            if current_title and len(" ".join(current_body)) > 50:
                section = finalize_section(current_title, current_body)
                if section:
                    sections.append(section)
            current_title, current_body = line, []
        else:
            current_body.append(line)

    if current_title and len(" ".join(current_body)) > 50:
        section = (current_title.strip(), " ".join(current_body).strip())
        sections.append(section)

    # Merge tiny sections (<80 chars) with the next
    merged_sections = []
    i = 0
    while i < len(sections):
        title, body = sections[i]
        if len(body) < 80 and i + 1 < len(sections):
            nxt_title, nxt_body = sections[i + 1]
            merged_sections.append((f"{title} / {nxt_title}", f"{body} {nxt_body}"))
            i += 2
        else:
            merged_sections.append((title, body))
            i += 1

    return merged_sections


# ---------------------------------------------------------
# 4️⃣ QUESTION TEMPLATES
# ---------------------------------------------------------
def get_question_templates(title: str) -> List[str]:
    t = title.lower()
    templates = [
        f"What is the policy on {t}?",
        f"Who is eligible for {t}?",
        f"How does {t} work?",
        f"What are the rules related to {t}?",
        f"When does {t} apply?",
        f"Are there any exceptions to {t}?",
        f"How can employees request {t}?",
        f"How much time or pay is given for {t}?",
    ]
    random.shuffle(templates)
    return templates[:4]


# ---------------------------------------------------------
# 5️⃣ SENTENCE SCORING
# ---------------------------------------------------------
def score_sentence(s: str) -> int:
    score = 0
    if re.search(r"\b(must|should|shall|required|entitled|eligible|prohibited)\b", s, re.IGNORECASE):
        score += 2
    if re.search(r"\b(hours|days|weeks|rate|approval|notify|leave|holiday|break|benefit)\b", s, re.IGNORECASE):
        score += 1
    if len(s.split()) > 8:
        score += 1
    return score


# ---------------------------------------------------------
# 6️⃣ Q&A EXTRACTION
# ---------------------------------------------------------
def extract_qna_from_section(title: str, content: str, source: str):
    sentences = sent_tokenize(content)
    if len(sentences) < 2:
        return []

    # Pick policy-relevant sentences only
    scored = [(s, score_sentence(s)) for s in sentences]
    top_sents = [s for s, sc in sorted(scored, key=lambda x: x[1], reverse=True) if sc > 1][:2]
    if not top_sents:
        return []

    context = " ".join(sentences[:5])
    qnas = []
    for t in get_question_templates(title):
        ans = top_sents[0].strip()
        if not ans or len(ans) < 30:
            continue
        qnas.append({
            "section": title.strip(),
            "question": t.capitalize().strip(),
            "answer": ans[0].upper() + ans[1:].strip(),
            "context": context.strip(),
            "source_doc": os.path.basename(source)
        })
    return qnas


# ---------------------------------------------------------
# 7️⃣ MAIN PIPELINE
# ---------------------------------------------------------
def generate_qna_from_pdfs(pdf_paths: List[str], output_path: str = "data/qna/qa.jsonl"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    all_qna = []

    for pdf in pdf_paths:
        if not os.path.exists(pdf):
            print(f"⚠️ Skipping missing file: {pdf}")
            continue

        print(f"\n📘 Processing: {pdf}")
        raw = extract_text_from_pdf(pdf)
        text = clean_text(raw)
        sections = detect_sections(text)
        print(f"   ➜ Found {len(sections)} cleaned sections")

        for title, content in sections:
            pairs = extract_qna_from_section(title, content, pdf)
            all_qna.extend(pairs)

    # Deduplicate
    seen, unique_qna = set(), []
    for qa in all_qna:
        key = (qa["question"].lower(), qa["answer"].lower())
        if key not in seen:
            seen.add(key)
            unique_qna.append(qa)

    with open(output_path, "w") as f:
        for qa in unique_qna:
            f.write(json.dumps(qa, ensure_ascii=False) + "\n")

    print(f"\n✅ Generated {len(unique_qna)} readable Q&A pairs")
    print(f"💾 Saved to: {output_path}")


# ---------------------------------------------------------
# 8️⃣ ENTRY POINT
# ---------------------------------------------------------
if __name__ == "__main__":
    pdf_files = [
        "data/raw/cmp-employee-handbook.pdf",
        "data/raw/8.-Employee-Handbook-v4.8.pdf",
        "data/raw/APL-Empl-Manual-Revised-12-22-16-fixed.pdf",
        "data/raw/EmployeeHandbook_20190926.pdf",
        "data/raw/Jacob-HAC-Employee-Handbook.pdf",
    ]
    generate_qna_from_pdfs(pdf_files, output_path="data/qna/qa.jsonl")
