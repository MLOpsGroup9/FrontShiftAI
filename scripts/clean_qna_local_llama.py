"""
FrontShiftAI – LLaMA-3 Local Q&A Cleaner + Labeler (Limited to 50)
------------------------------------------------------------------
Temporary version that only cleans the first 50 Q&A pairs for testing.
The original full version is kept below as commented code.
"""

import os, json, re
from llama_cpp import Llama

# 🔹 Load local model
llm = Llama(
    model_path="models/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf",
    n_ctx=4096,
    n_threads=8,      # adjust per CPU cores
    n_gpu_layers=35,  # set 0 if CPU-only
)

def clean_and_label(record):
    prompt = f"""
You are an HR policy text editor and classifier.
Given a real Q&A pair from an employee handbook:

1. Fix grammar and readability for the question and answer.
2. Do NOT add or remove facts — keep the meaning identical.
3. Assign a topic label from this list:
   ["leave", "pay", "conduct", "benefits", "safety", "general"]

Return a compact JSON object:
{{
  "question": "...",
  "answer": "...",
  "topic": "..."
}}

Q: {record['question']}
A: {record['answer']}
"""
    response = llm(prompt, max_tokens=256, temperature=0)
    text = response["choices"][0]["text"].strip()

    try:
        data = json.loads(re.search(r"\{.*\}", text, re.S).group())
        record.update(data)
    except Exception:
        record["topic"] = "general"
    return record


def process_file(input_path="data/qna/qa.jsonl",
                 output_path="data/qna/qa_cleaned_local_50.jsonl"):
    cleaned = []
    with open(input_path, "r") as f:
        for i, line in enumerate(f, 1):
            if i > 50:  # 🔹 limit processing to first 50 Q&As
                print("⏹️  Stopped after processing 50 Q&A pairs (test run).")
                break

            rec = json.loads(line)
            rec = clean_and_label(rec)
            cleaned.append(rec)
            if i % 10 == 0:
                print(f"🧹 Cleaned {i} Q&As...")

    with open(output_path, "w") as out:
        for rec in cleaned:
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"\n✅ Cleaned & labeled {len(cleaned)} records (limited run)")
    print(f"💾 Saved to {output_path}")


if __name__ == "__main__":
    process_file()


# ----------------------------------------------------------
# 🗒️ Original Full Version (Commented Out)
# ----------------------------------------------------------

# def process_file(input_path="data/qna/qa.jsonl",
#                  output_path="data/qna/qa_cleaned_local.jsonl"):
#     cleaned = []
#     with open(input_path, "r") as f:
#         for i, line in enumerate(f, 1):
#             rec = json.loads(line)
#             rec = clean_and_label(rec)
#             cleaned.append(rec)
#             if i % 10 == 0:
#                 print(f"🧹 Cleaned {i} Q&As...")
#
#     with open(output_path, "w") as out:
#         for rec in cleaned:
#             out.write(json.dumps(rec, ensure_ascii=False) + "\n")
#
#     print(f"\n✅ Cleaned & labeled {len(cleaned)} records")
#     print(f"💾 Saved to {output_path}")
#
# if __name__ == "__main__":
#     process_file()
