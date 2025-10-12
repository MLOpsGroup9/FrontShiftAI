from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions
from llama_cpp import Llama

# -------------------------------------------------
# PATHS
# -------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[1]
CHROMA_DIR = BASE_DIR / "data" / "vector_db"
MODEL_PATH = BASE_DIR / "models" / "Meta-Llama-3-8B-Instruct.Q4_K_M.gguf"

# -------------------------------------------------
# LOAD MODEL
# -------------------------------------------------
print("🦙 Loading LLaMA 3 model...")
llm = Llama(
    model_path=str(MODEL_PATH),
    n_ctx=8192,          # expanded context window
    n_threads=4,
    temperature=0.6,
    top_p=0.9,
    max_tokens=2048,     # longer answers
    stop=[],             # disable early stopping
    verbose=False
)
print("✅ Model loaded")

# -------------------------------------------------
# CONNECT TO CHROMA
# -------------------------------------------------
client = chromadb.PersistentClient(path=str(CHROMA_DIR))
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)
collection = client.get_collection("frontshift_policies", embedding_function=embedding_fn)
print(f"✅ Loaded ChromaDB collection with {collection.count()} chunks")

# -------------------------------------------------
# SYSTEM PROMPT (HR-TUNED)
# -------------------------------------------------
system_prompt = """
This is FrontShiftAI — an intelligent HR assistant built to help employees understand company
policies, leave entitlements, benefits, and workplace procedures.

FrontShiftAI’s knowledge comes *only* from official company documents, employee handbooks,
and policy manuals. It does **not** use external sources or speculation.

Guidelines for responses:
- Maintain a **professional, clear, and supportive HR tone**.
- Base answers strictly on the provided document context.
- If information isn’t available, say:
  "This information isn’t available in the provided company handbook."
- Never invent numbers, rules, or details.
- If policies vary by company, clearly state that.
- Keep factual answers short, and policy explanations structured.
- Use markdown for readability:
  - **Bold** key terms
  - Lists for steps or conditions
  - Short headers for organization
- Always finish your sentences completely.
- Do not restate the entire context — summarize what’s relevant.

FrontShiftAI’s mission is to provide grounded, accurate, and empathetic HR guidance.
"""

# -------------------------------------------------
# AUTO-CONTINUE GENERATION LOGIC
# -------------------------------------------------
def generate_full_response(prompt, max_tokens=2048, continue_if_cut=True):
    """Ensures complete output even if the model stops early."""
    full_output = ""
    attempt = 0

    while attempt < 3:  # up to 3 continuation rounds
        response = llm(
            prompt=prompt + full_output,
            max_tokens=max_tokens,
            temperature=0.6,
            top_p=0.9,
            repeat_penalty=1.1,  # helps prevent looping
            stop=[]
        )
        text = response["choices"][0]["text"].strip()
        full_output += " " + text

        # if the model finishes naturally, break
        if full_output.strip().endswith(('.', '!', '?')) or not continue_if_cut:
            break

        attempt += 1  # try to finish if it's cut off

    # final cleanup
    full_output = full_output.strip()
    if not full_output.endswith(('.', '!', '?')):
        full_output = full_output.rsplit('.', 1)[0] + '.'

    return full_output


# -------------------------------------------------
# RAG PIPELINE
# -------------------------------------------------
def rag_query(user_query: str, top_k: int = 4):
    # Retrieve top chunks
    results = collection.query(query_texts=[user_query], n_results=top_k)
    retrieved_docs = results["documents"][0]
    metadatas = results["metadatas"][0]

    # Build context
    context = "\n\n".join(retrieved_docs)
    if len(context) > 6000:
        context = context[:6000] + "..."

    # Construct the full prompt
    prompt = f"""{system_prompt.strip()}

CONTEXT:
{context}

USER QUESTION:
{user_query}

Provide a clear, professional, and complete HR-style answer. Always finish your thought.

FINAL ANSWER:
"""

    print(f"🧮 Approx prompt length: {len(prompt.split())} tokens")

    # Generate complete response
    answer = generate_full_response(prompt)

    return answer, metadatas


# -------------------------------------------------
# INTERACTIVE CHAT LOOP
# -------------------------------------------------
if __name__ == "__main__":
    print("\n💬 FrontShiftAI HR Assistant — type 'exit' to quit.\n")

    while True:
        query = input("🧠 Ask HR Assistant: ").strip()
        if query.lower() in {"exit", "quit"}:
            print("👋 Goodbye!")
            break

        answer, metas = rag_query(query)
        print("\n🤖 HR Assistant:\n", answer)
        print("\n📄 Source Documents:")
        for m in metas:
            print(f" - {m.get('filename', 'unknown')} (chunk {m.get('chunk_id', '?')})")
        print("-" * 60)
