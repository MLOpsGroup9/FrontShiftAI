import json
from pathlib import Path
from tqdm import tqdm
from llama_cpp import Llama
import re

MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "Meta-Llama-3-8B-Instruct.Q4_K_M.gguf"
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
CHUNKS_FILE = DATA_DIR / "extracted" / "combined_chunks.json"
OUTPUT_FILE = DATA_DIR / "generated" / "qna_pairs_test.json"  # save test output separately
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

# Load model
llm = Llama(
    model_path=str(MODEL_PATH),
    n_ctx=4096,
    n_threads=4,
    temperature=0.7,
    top_p=0.9,
    max_tokens=512,
    verbose=False
)

# Load chunks
with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
    chunks = json.load(f)

total_chunks = len(chunks)
print(f"Loaded {total_chunks} chunks total")

# --- Select subset 25 → 75 ---
start_idx, end_idx = 25, 75
subset = chunks[start_idx:end_idx + 1]
print(f"Testing with chunks {start_idx} → {end_idx} ({len(subset)} chunks)\n")

# --- Generate Q&A ---
qna_pairs = []

for i, chunk in enumerate(tqdm(subset, desc="Generating Q&A (test subset)")):
    text = chunk["text"].strip()[:1200]
    if len(text) < 150:
        continue

    prompt = f"""
You are a helpful HR assistant. Read the text below and create 2 to 3 question-answer pairs.
Only output JSON list like this:
[
  {{"question": "Question 1", "answer": "Answer 1"}},
  {{"question": "Question 2", "answer": "Answer 2"}}
]

Text:
{text}
"""

    try:
        output = llm(prompt=prompt)
        response = output["choices"][0]["text"].strip()

        # Try to locate JSON array in model output
        json_match = re.search(r"\[.*\]", response, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
            for pair in parsed:
                if "question" in pair and "answer" in pair:
                    qna_pairs.append({
                        "document_name": chunk["metadata"]["document_name"],
                        "chunk_id": chunk["metadata"]["chunk_id"],
                        "question": pair["question"],
                        "answer": pair["answer"]
                    })
        else:
            print(f"⚠️ No valid JSON found for chunk {start_idx + i}")

    except Exception as e:
        print(f"⚠️ Error on chunk {start_idx + i}: {e}")
        continue

# Save output
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(qna_pairs, f, indent=2, ensure_ascii=False)

print(f"\n✅ Generated {len(qna_pairs)} Q&A pairs (chunks {start_idx} → {end_idx})")
print(f"📄 Saved at {OUTPUT_FILE}")
