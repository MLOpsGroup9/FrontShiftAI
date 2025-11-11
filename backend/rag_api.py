"""
FastAPI backend service for RAG queries using Inception Labs Mercury model.
This service wraps the RAG pipeline from ml_pipeline to provide REST API endpoints.
Uses Inception Labs API which is compatible with OpenAI's API interface.
"""
import os
import sys
import json
from pathlib import Path
from typing import Optional, List, Dict
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import uvicorn


load_dotenv()


# Add project root to path
current_file = Path(__file__).resolve()
# rag_api.py is in backend_api/, so go up 1 level to reach project root
project_root = current_file.parents[1]  # Go up to project root
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import and patch rag_query_utils to use dynamic project root
import ml_pipeline.rag.rag_query_utils as rag_utils

# Update PROJECT_ROOT and CHROMA_DIR to use current project root
rag_utils.PROJECT_ROOT = project_root
rag_utils.CHROMA_DIR = project_root / "data_pipeline" / "data" / "vector_db"

from ml_pipeline.rag.rag_query_utils import retrieve_context

# # Optional local LLaMA inference support
# try:
#     from llama_cpp import Llama
#     LLAMA_AVAILABLE = True
# except ImportError:
#     LLAMA_AVAILABLE = False
#     Llama = None  # type: ignore

# Import requests for Inception Labs API calls
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("Error: requests library is required. Install with: pip install requests")
    sys.exit(1)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan event manager for startup/shutdown hooks."""
    print("🚀 FrontShiftAI RAG API starting...")
    if INCEPTION_API_KEY:
        print(f"📦 Using Inception Labs Mercury model: {MERCURY_MODEL}")
        print(f"🌐 API Base: {INCEPTION_API_BASE}")
    else:
        print("⚠️  Warning: INCEPTION_API_KEY not set.")
        print("   Get your API key from: https://platform.inceptionlabs.ai/")
        print("   Set it with: export INCEPTION_API_KEY=your_api_key")

    try:
        yield
    finally:
        print("👋 FrontShiftAI RAG API shutting down...")

app = FastAPI(title="FrontShiftAI RAG API", version="1.0.0", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inception Labs Mercury API Configuration
INCEPTION_API_BASE = os.getenv("INCEPTION_API_BASE", "https://api.inceptionlabs.ai/v1")
INCEPTION_API_KEY = os.getenv("INCEPTION_API_KEY", None)
MERCURY_MODEL = os.getenv("MERCURY_MODEL", "mercury")  # Options: mercury-v1, mercury-coder-small, etc.

# # Local LLaMA configuration (optional)
# LLAMA_MODEL_PATH = os.getenv("LLAMA_MODEL_PATH", str(project_root / "models" / "Meta-Llama-3-8B-Instruct.Q4_K_M.gguf"))
# LLAMA_CONTEXT = int(os.getenv("LLAMA_CONTEXT", "8192"))
# LLAMA_THREADS = int(os.getenv("LLAMA_THREADS", str(os.cpu_count() or 4)))
# LLAMA_MAX_TOKENS = int(os.getenv("LLAMA_MAX_TOKENS", "1024"))

# llama_model: Optional[Llama] = None

# Validate API key
if not INCEPTION_API_KEY:
    print("⚠️  Warning: INCEPTION_API_KEY not set. Please set it to use the Mercury model.")
    print("   Get your API key from: https://platform.inceptionlabs.ai/")
    print("   Set it with: export INCEPTION_API_KEY=your_api_key")

SYSTEM_PROMPT = """
This is FrontShiftAI — an intelligent HR assistant built to help employees understand company policies, leave entitlements, benefits, and workplace procedures. FrontShiftAI's knowledge comes *only* from official company documents, employee handbooks, and policy manuals. It does **not** use external sources or speculation.

### Your Goals:
- Answer employee HR questions using the provided company handbook context.
- Maintain a **professional, concise, and factual** tone.
- Only use information from the given context.
- If information isn't available, say:
  "This information isn't available in the provided company handbook."
- Avoid speculation, repetition, and unnecessary politeness.
- Stop once you have fully answered the question.

Use markdown for clarity:
- **Bold** key terms
- Lists for steps or benefits
- Short headers for structure
"""


def generate_response(prompt: str) -> str:
    """
    Generate response using Inception Labs Mercury model via their API.
    The API is compatible with OpenAI's chat completions interface.
    """
    if not INCEPTION_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Inception Labs API key not configured. Set INCEPTION_API_KEY environment variable."
        )
    
    if not REQUESTS_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="requests library not available. Install with: pip install requests"
        )
    
    try:
        # Inception Labs API endpoint (OpenAI-compatible)
        api_url = f"{INCEPTION_API_BASE}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {INCEPTION_API_KEY}",
            "Content-Type": "application/json",
        }
        
        # Prepare request payload (OpenAI chat completions format)
        payload = {
            "model": MERCURY_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 1024,
            "temperature": 0.7,
            "top_p": 0.9,
        }
        
        # Make API request
        response = requests.post(
            api_url,
            json=payload,
            headers=headers,
            timeout=60
        )
        
        # Check for errors
        response.raise_for_status()
        result = response.json()
        
        # Extract the generated text from OpenAI-compatible response
        if "choices" in result and len(result["choices"]) > 0:
            message = result["choices"][0].get("message", {})
            return message.get("content", "").strip()
        elif "content" in result:
            return result["content"].strip()
        else:
            # Fallback: log the response for debugging
            print(f"Warning: Unexpected response format: {json.dumps(result, indent=2)}")
            raise HTTPException(
                status_code=500,
                detail="Unexpected response format from Inception Labs API"
            )
            
    except requests.exceptions.HTTPError as e:
        error_detail = "Unknown error"
        try:
            error_response = e.response.json()
            error_detail = error_response.get("error", {}).get("message", str(e))
        except:
            error_detail = str(e)
        
        raise HTTPException(
            status_code=e.response.status_code if e.response else 500,
            detail=f"Inception Labs API error: {error_detail}"
        )
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error connecting to Inception Labs API: {str(e)}"
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error generating response: {str(e)}"
        )


# def generate_response_llama(prompt: str) -> str:
#     """Generate a response using the local LLaMA 3 model (optional)."""
#     global llama_model

#     if not LLAMA_AVAILABLE:
#         raise HTTPException(status_code=503, detail="llama_cpp not installed. Install with: pip install llama-cpp-python")

#     model_path = Path(LLAMA_MODEL_PATH)
#     if not model_path.exists():
#         raise HTTPException(status_code=503, detail=f"LLaMA model not found at {model_path}")

#     if llama_model is None:
#         try:
#             print(f"🦙 Loading LLaMA model from {model_path} ...")
#             llama_model = Llama(
#                 model_path=str(model_path),
#                 n_ctx=LLAMA_CONTEXT,
#                 n_threads=LLAMA_THREADS,
#                 max_tokens=LLAMA_MAX_TOKENS,
#                 temperature=0.7,
#                 top_p=0.9,
#                 verbose=False,
#             )
#             print("✅ LLaMA model ready")
#         except Exception as exc:
#             llama_model = None
#             raise HTTPException(status_code=500, detail=f"Failed to load LLaMA model: {exc}")

#     if llama_model is None:
#         raise HTTPException(status_code=500, detail="LLaMA model is not initialized")

#     try:
#         completion = llama_model.create_completion(
#             prompt=prompt,
#             max_tokens=LLAMA_MAX_TOKENS,
#             temperature=0.6,
#             top_p=0.9,
#             repeat_penalty=1.1,
#             stop=["---", "Thank", "👋"],
#         )
#         if "choices" in completion and completion["choices"]:
#             return completion["choices"][0].get("text", "").strip()
#         raise HTTPException(status_code=500, detail="Unexpected response from LLaMA model")
#     except Exception as exc:
#         raise HTTPException(status_code=500, detail=f"Error generating response with LLaMA: {exc}")


# Request/Response models
class RAGQueryRequest(BaseModel):
    query: str
    company_name: Optional[str] = None
    top_k: int = 4


class RAGQueryResponse(BaseModel):
    answer: str
    sources: List[Dict]
    query: str
    company_name: Optional[str] = None


# @app.on_event("startup")
# async def startup_event():
#     """Initialize on startup."""
#     print("🚀 FrontShiftAI RAG API starting...")
#     if INCEPTION_API_KEY:
#         print(f"📦 Using Inception Labs Mercury model: {MERCURY_MODEL}")
#         print(f"🌐 API Base: {INCEPTION_API_BASE}")
#     else:
#         print("⚠️  Warning: INCEPTION_API_KEY not set.")
#         print("   Get your API key from: https://platform.inceptionlabs.ai/")
#         print("   Set it with: export INCEPTION_API_KEY=your_api_key")


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "model_type": "Inception Labs Mercury",
        "model": MERCURY_MODEL,
        "api_base": INCEPTION_API_BASE,
        "api_key_configured": INCEPTION_API_KEY is not None,
        "api_key_set": bool(INCEPTION_API_KEY),
    }


@app.post("/api/rag/query", response_model=RAGQueryResponse)
def rag_query(request: RAGQueryRequest):
    """
    Process a RAG query and return the answer with sources using Mercury model.
    """
    try:
        # Retrieve context from ChromaDB
        retrieved_docs, metadatas = retrieve_context(
            request.query,
            request.company_name,
            request.top_k
        )

        if not retrieved_docs:
            return RAGQueryResponse(
                answer="No relevant context found in the company handbook.",
                sources=[],
                query=request.query,
                company_name=request.company_name
            )

        # Build context
        context = "\n\n".join(retrieved_docs)
        if len(context) > 6000:
            context = context[:6000] + "..."

        # Build prompt
        prompt = f"""{SYSTEM_PROMPT.strip()}

### CONTEXT:
{context}

### QUESTION:
{request.query}

### ANSWER:"""

        # Generate response using Mercury (default)
        answer = generate_response(prompt)
        # To experiment with the local LLaMA model instead, uncomment the next line.
        # answer = generate_response_llama(prompt)

        # Format sources
        sources = [
            {
                "company": meta.get("company", "unknown"),
                "filename": meta.get("filename", "unknown"),
                "chunk_id": meta.get("chunk_id", "?")
            }
            for meta in metadatas
        ]

        return RAGQueryResponse(
            answer=answer,
            sources=sources,
            query=request.query,
            company_name=request.company_name
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error processing RAG query: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
