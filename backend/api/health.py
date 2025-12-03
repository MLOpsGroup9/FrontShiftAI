"""Health check endpoint for Cloud Run"""
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from db.connection import SessionLocal

router = APIRouter()

@router.get("/health")
async def health_check():
    """Health check for Cloud Run and monitoring"""
    try:
        # Check database connection
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        
        return {
            "status": "healthy",
            "database": "connected",
            "service": "backend"
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e),
                "service": "backend"
            }
        )