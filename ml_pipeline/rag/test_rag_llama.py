# test_rag_llama.py
import chromadb
from chromadb.utils import embedding_functions
from llama_cpp import Llama
import sys, os, time
from pathlib import Path

current_file = Path(__file__).resolve()
project_root = current_file.parents[2]  # /Users/sriks/Documents/Projects/FrontShiftAI
sys.path.append(str(project_root))

data_dir = project_root / "data_pipeline" / "data"
CHROMA_DIR = data_dir / "vector_db"
MODEL_PATH = project_root / "models" / "Meta-Llama-3-8B-Instruct.Q4_K_M.gguf"

from ml_pipeline.rag.rag_query_utils import retrieve_context

print("🦙 Loading LLaMA 3 model...")
llm = Llama(
    model_path=str(MODEL_PATH),
    n_ctx=8192,
    n_threads=4,
    temperature=0.7,          # slightly more stable
    top_p=0.9,
    max_tokens=1024,          # limit output length
    stop=["---", "Thank", "👋"],  # stop repeating endings
    verbose=False
)
print("✅ Model loaded")

# ----------------------------------------------------------------------
# Connect to ChromaDB
# ----------------------------------------------------------------------
client = chromadb.PersistentClient(path=str(CHROMA_DIR))
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)
collection = client.get_collection("frontshift_handbooks", embedding_function=embedding_fn)
print(f"✅ Loaded ChromaDB collection with {collection.count()} chunks")

# ----------------------------------------------------------------------
# System Prompt
# ----------------------------------------------------------------------
system_prompt = """
This is FrontShiftAI — an intelligent HR assistant built to help employees understand company policies, leave entitlements, benefits, and workplace procedures. FrontShiftAI’s knowledge comes *only* from official company documents, employee handbooks, and policy manuals. It does **not** use external sources or speculation.

### Your Goals:
- Answer employee HR questions using the provided company handbook context.
- Maintain a **professional, concise, and factual** tone.
- Only use information from the given context.
- If information isn’t available, say:
  "This information isn’t available in the provided company handbook."
- Avoid speculation, repetition, and unnecessary politeness.
- Stop once you have fully answered the question.

Use markdown for clarity:
- **Bold** key terms
- Lists for steps or benefits
- Short headers for structure
"""

# ----------------------------------------------------------------------
# Streaming Response Generator
# ----------------------------------------------------------------------
def stream_response(prompt):
    """Stream the model output token-by-token as it's generated."""
    print("\n🤖 HR Assistant:\n", end="", flush=True)
    response_stream = llm.create_completion(
        prompt=prompt,
        max_tokens=1024,
        temperature=0.6,
        top_p=0.9,
        repeat_penalty=1.1,
        stream=True,  # <- key for live token streaming
        stop=["---", "Thank", "😊", "👋"]
    )

    full_output = []
    for chunk in response_stream:
        if "choices" in chunk and len(chunk["choices"]) > 0:
            token = chunk["choices"][0].get("text", "")
            if token:
                sys.stdout.write(token)
                sys.stdout.flush()
                full_output.append(token)
                time.sleep(0.01)  # optional: delay for readability

    print("\n")  # spacing after model output
    return "".join(full_output).strip()

# ----------------------------------------------------------------------
# RAG Query
# ----------------------------------------------------------------------
def rag_query(user_query: str, company_name: str = None, top_k: int = 4):
    """Retrieve context from Chroma and stream the model response."""
    retrieved_docs, metadatas = retrieve_context(user_query, company_name, top_k)

    if not retrieved_docs:
        return "No relevant context found in the company handbook.", []

    context = "\n\n".join(retrieved_docs)
    if len(context) > 6000:
        context = context[:6000] + "..."

    prompt = f"""{system_prompt.strip()}

### CONTEXT:
{context}

### QUESTION:
{user_query}

### ANSWER:"""

    print(f"🧮 Approx prompt length: {len(prompt.split())} tokens")
    answer = stream_response(prompt)
    return answer, metadatas

# ----------------------------------------------------------------------
# CLI Interface
# ----------------------------------------------------------------------
if __name__ == "__main__":
    print("\n💬 FrontShiftAI HR Assistant — type 'exit' to quit.\n")
    company_name = input("🏢 Enter company name (e.g., Crouse, Jacob, Alta Peruvian): ").strip()

    while True:
        query = input("🧠 Ask HR Assistant: ").strip()
        if query.lower() in {"exit", "quit"}:
            print("👋 Goodbye!")
            break

        answer, metas = rag_query(query, company_name=company_name)

        # print final sources
        print("\n📄 Source Documents:")
        for m in metas:
            print(f" - {m.get('company', 'unknown')} | {m.get('filename', 'unknown')} (chunk {m.get('chunk_id', '?')})")
        print("-" * 60)
