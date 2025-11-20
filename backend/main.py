"""
FrontShiftAI FastAPI Application
Main entry point for the backend API
"""
import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import uvicorn

# Load environment variables
load_dotenv()

# Ensure project root is in Python path
current_file = Path(__file__).resolve()
project_root = current_file.parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import routers
from api import auth, rag, admin
from api.pto_agent import router as pto_router  # NEW: PTO Agent router

# ----------------------------
# Lifespan Events
# ----------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 FrontShiftAI API starting up...")
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
    version="2.0.0",
    description="Multi-company RAG system with AI agents",
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
# Register Routers
# ----------------------------
app.include_router(auth.router)
app.include_router(rag.router)
app.include_router(admin.router)
app.include_router(pto_router)  # NEW: PTO Agent routes

# ----------------------------
# Health Check
# ----------------------------
@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "version": "2.0.0",
        "message": "FrontShiftAI API is running"
    }

@app.get("/")
def root():
    return {
        "message": "Welcome to FrontShiftAI API",
        "docs": "/docs",
        "health": "/health"
    }

# Set lifespan
app.router.lifespan_context = lifespan

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