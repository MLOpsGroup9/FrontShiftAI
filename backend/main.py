"""
FrontShiftAI FastAPI Application
Main entry point for the backend API
"""
import os
import sys
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import uvicorn

# Load environment variables
load_dotenv()

# Setup logging
logger = logging.getLogger(__name__)

# Ensure project root is in Python path
current_file = Path(__file__).resolve()
project_root = current_file.parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import routers
from api import auth, rag, admin, health
from api.unified_agent import router as unified_agent_router
from api.pto_agent import router as pto_router
from api.hr_ticket_agent import router as hr_ticket_router
from api.company_management import router as company_management_router

# Import monitoring middleware
from monitoring.middleware import MonitoringMiddleware

# Import ChromaDB setup from chat_pipeline
from chat_pipeline.rag.data_loader import ensure_chroma_store

# ----------------------------
# Lifespan Events
# ----------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 FrontShiftAI API starting up...")
    
    # Ensure ChromaDB is available in production
    try:
        if os.getenv("ENVIRONMENT") == "production":
            logger.info("Ensuring ChromaDB is available...")
            ensure_chroma_store()
            logger.info("ChromaDB ready")
    except Exception as e:
        logger.error(f"ChromaDB setup failed: {e}")
        # Don't fail startup - allow service to start for debugging
    
    # Initialize database
    from db import init_db
    from db.seed import seed_initial_data
    init_db()
    seed_initial_data()
    
    yield
    
    print("👋 FrontShiftAI API shutting down...")

# ----------------------------
# FASTAPI APP
# ----------------------------
app = FastAPI(
    title="FrontShiftAI API",
    version="2.1.0",
    description="Multi-company RAG system with unified AI agents",
    lifespan=lifespan
)

# ----------------------------
# CORS SETTINGS
# ----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------
# MONITORING MIDDLEWARE
# ----------------------------
app.add_middleware(MonitoringMiddleware)

# ----------------------------
# Register Routers
# ----------------------------
app.include_router(auth.router)
app.include_router(rag.router)
app.include_router(admin.router)
app.include_router(health.router, tags=["health"])

# Unified Agent (User-facing chat)
app.include_router(unified_agent_router)

# Individual Agent Routers (Admin endpoints only)
app.include_router(pto_router)
app.include_router(hr_ticket_router)
app.include_router(company_management_router)

# ----------------------------
# Root Endpoint
# ----------------------------
@app.get("/")
def root():
    return {
        "message": "Welcome to FrontShiftAI API",
        "docs": "/docs",
        "health": "/health",
        "chat_endpoint": "/api/chat/message"
    }

# ----------------------------
# Run server directly
# ----------------------------
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )