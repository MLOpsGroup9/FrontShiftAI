import os
import json
from groq import Groq
import fitz  # PyMuPDF for PDFs
import docx  # for DOCX files
import math

# ========== CONFIG ==========
API_KEY = os.getenv("REDACTEDJxZsOM7xR2gtlFP63NhqWGdyb3FYzi3VZIEiE2SVSGXh6EDZq7ZL")  # or paste directly: "your_api_key_here"
MODEL = "openai/gpt-oss-20b"
OUTPUT_FILE = "qa_pairs.jsonl"
TARGET_QA_COUNT = 500
CHUNK_SIZE = 1500  # adjust based on model context length
QA_PER_CHUNK = 5   # approx, adjust for tuning
# ============================

client = Groq(api_key=API_KEY)


def read_text_from_file(path):
    """Read text from txt, pdf, or docx files"""
    ext = path.split(".")[-1].lower()

    if ext == "txt":
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    elif ext == "pdf":
        text = ""
        with fitz.open(path) as doc:
            for page in doc:
                text += page.get_text()
        return text

    elif ext == "docx":
        doc = docx.Document(path)
        return "\n".join([p.text for p in doc.paragraphs])

    else:
        raise ValueError("Unsupported file format. Use .txt, .pdf, or .docx")


def chunk_text(text, chunk_size=CHUNK_SIZE):
    """Split text into manageable chunks"""
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]


def generate_qa_from_chunk(chunk):
    """Call Groq API to get Q&A pairs for a chunk"""
    prompt = f"""
    You are an assistant that extracts factual Q&A pairs from a document.
    Generate {QA_PER_CHUNK} question-answer pairs from the text below.
    Each question should be concise and meaningful.
    Each answer should be directly grounded in the text.

    Return JSON ONLY in this format:
    [
      {{"question": "...", "answer": "..."}},
      ...
    ]

    Text:
    {chunk}
    """

    completion = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_completion_tokens=2048
    )

    return completion.choices[0].message.content


def generate_qa_dataset(path):
    text = read_text_from_file(path)
    chunks = chunk_text(text)

    total_chunks_needed = math.ceil(TARGET_QA_COUNT / QA_PER_CHUNK)
    chunks = chunks[:total_chunks_needed]

    print(f"Processing {len(chunks)} chunks...")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        for i, chunk in enumerate(chunks):
            print(f"⏳ Chunk {i + 1}/{len(chunks)}...")
            try:
                qa_json_str = generate_qa_from_chunk(chunk)
                qas = json.loads(qa_json_str)
                for qa in qas:
                    out.write(json.dumps(qa, ensure_ascii=False) + "\n")
            except Exception as e:
                print(f"⚠️ Error in chunk {i + 1}: {e}")

    print(f"\n✅ Saved all Q&A pairs to: {os.path.abspath(OUTPUT_FILE)}")


if __name__ == "__main__":
    doc_path = input("Enter the path of your document: ").strip()
    generate_qa_dataset(doc_path)
