"""
RAG module for FrontShiftAI HR Assistant.
"""

import os
import sys
import time
import warnings
from pathlib import Path
from typing import List, Dict, Tuple

# Suppress TensorFlow warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
warnings.filterwarnings('ignore')
os.environ['PYTHONWARNINGS'] = 'ignore'

try:
    import tensorflow as tf
    tf.get_logger().setLevel('ERROR')
    import logging
    logging.getLogger('tensorflow').setLevel('ERROR')
    logging.getLogger('tf_keras').setLevel('ERROR')
except ImportError:
    pass

from llama_cpp import Llama

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR / "data_pipeline"))
from utils.logger import get_logger
from loader import ChunkDataLoader

logger = get_logger("rag_system")

# --- Configuration ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = Path(os.getenv("LLAMA_MODEL_PATH", str(PROJECT_ROOT / "models" / "Meta-Llama-3-8B-Instruct.Q4_K_M.gguf")))

# --- Initialize Loader ---
loader = ChunkDataLoader()

# --- Initialize LLaMA Model ---
llm = None

def initialize_llm():
    """Initialize LLaMA model with error handling."""
    global llm
    if llm is None:
        try:
            logger.info("Loading LLaMA 3 model...")
            llm = Llama(
                model_path=str(MODEL_PATH),
                n_ctx=8192,
                n_threads=4,
                temperature=0.7,
                top_p=0.9,
                max_tokens=1024,
                stop=["---", "Thank", "👋"],
                verbose=False
            )
            logger.info("LLaMA model loaded and ready")
        except Exception as e:
            logger.error(f"Failed to load LLaMA model: {e}", exc_info=True)
            raise
    return llm

# --- System Prompt ---
SYSTEM_PROMPT = """
This is FrontShiftAI — an intelligent HR assistant built to help employees understand company policies,
leave entitlements, benefits, and workplace procedures. The assistant only uses official company
documents, employee handbooks, and policy manuals.

### Your Goals:

- Answer employee HR questions using **only** the provided context from company handbooks.

- Maintain a **professional, concise, and factual** tone.

- **Do not speculate, invent, or use information outside the provided context.**

- If information isn't available in the context, explicitly state:

  "This information isn't available in the provided company handbook."

- Stop once the answer is complete. Do not add unnecessary politeness or repetition.

### Formatting Guidelines:

- Use **bold** for key terms and important concepts
- Use numbered or bulleted lists for steps, benefits, or procedures
- Use short headers (##) for structure when needed
- Keep paragraphs concise and focused
"""

def retrieve_context(query: str, company_name: str = None, top_k: int = 4) -> Tuple[List[str], List[dict], float]:
    """Retrieve context chunks using ChunkDataLoader."""
    start_time = time.time()
    documents, metadatas, _ = loader.retrieve(
        query=query,
        company_name=company_name,
        top_k=top_k,
        include_distances=False
    )
    latency = (time.time() - start_time) * 1000
    return documents, metadatas, latency

def stream_response(prompt: str) -> str:
    """Stream LLM response token-by-token."""
    model = initialize_llm()
    print("\n🤖 HR Assistant:\n", end="", flush=True)
    
    response_stream = model.create_completion(
        prompt=prompt,
        max_tokens=1024,
        temperature=0.6,
        top_p=0.9,
        repeat_penalty=1.1,
        stream=True,
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
                time.sleep(0.01)
    
    print("\n")
    return "".join(full_output).strip()

def rag_query(user_query: str, company_name: str = None, top_k: int = 4):
    """Execute RAG query: retrieve context and generate response."""
    retrieved_docs, metadatas, latency = retrieve_context(user_query, company_name, top_k)
    
    if not retrieved_docs:
        return "No relevant context found in the company handbook.", [], latency
    
    context = "\n\n".join(retrieved_docs)
    if len(context) > 6000:
        context = context[:6000] + "..."
    
    prompt = f"""{SYSTEM_PROMPT.strip()}

### CONTEXT:

{context}

### QUESTION:

{user_query}

### ANSWER:"""
    
    print(f"⏱  Retrieval: {latency:.1f} ms | 📄 Context: {len(retrieved_docs)} chunks")
    answer = stream_response(prompt)
    
    return answer, metadatas, latency

if __name__ == "__main__":
    try:
        print("\n💬 FrontShiftAI HR Assistant — type 'exit' to quit.\n")
        company_name = input("🏢 Enter company name (optional): ").strip() or None
        
        while True:
            query = input("\n🧠 Ask HR Assistant: ").strip()
            if query.lower() in {"exit", "quit"}:
                print("👋 Goodbye!")
                break
            
            if not query:
                continue
            
            answer, metas, _ = rag_query(query, company_name, top_k=4)
            
            print("\n📄 Source Documents:")
            for i, m in enumerate(metas, 1):
                company = m.get('company', 'unknown')
                doc_id = m.get('doc_id', 'unknown')
                chunk_id = m.get('chunk_id', '?')
                section = m.get('section_title', '')
                section_str = f" | {section}" if section else ""
                print(f"  {i}. {company} | {doc_id}{section_str} (chunk {chunk_id})")
            print("-" * 60)
    
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        sys.exit(1)

