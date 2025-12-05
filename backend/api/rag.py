"""
RAG query API endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from schemas import RAGQueryRequest, RAGQueryResponse
from services import normalize_metadata_company_name
from api.auth import get_current_user
from chat_pipeline.rag.pipeline import RAGPipeline
import logging
import time

# Configure structured logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rag", tags=["RAG"])

# Create RAG pipeline instance
pipeline = RAGPipeline()

@router.post("/query", response_model=RAGQueryResponse)
async def rag_query(
    request: RAGQueryRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    RAG query endpoint - requires authentication
    Automatically filters results by user's company
    """
    start_time = time.time()
    try:
        company_name = current_user.get("company")
        
        if current_user["role"] != "super_admin" and not company_name:
            raise HTTPException(
                status_code=403,
                detail="No company associated with this user"
            )
        
        logger.info(
            "RAG Query initiated",
            extra={
                "user_email": current_user['email'],
                "company": company_name,
                "query": request.query
            }
        )
        
        # Run RAG pipeline
        rag_company_filter = company_name if current_user["role"] != "super_admin" else None
        
        result = pipeline.run(
            query=request.query,
            top_k=request.top_k,
            company_name=rag_company_filter,
        )
        
        answer = result.answer
        metadata = result.metadata
        
        # Format sources
        sources = [
            {
                "company": m.get("company", "unknown"),
                "filename": m.get("filename", "unknown"),
                "chunk_id": m.get("chunk_id", "?"),
                "text": m.get("text", ""),
                "doc_title": m.get("doc_title", ""),
                "section_title": m.get("section_title", ""),
            }
            for m in metadata
        ]
        
        duration = time.time() - start_time
        logger.info(
            "RAG Query completed",
            extra={
                "user_email": current_user['email'],
                "company": company_name,
                "duration_seconds": duration,
                "sources_count": len(sources)
            }
        )
        
        return RAGQueryResponse(
            answer=answer,
            sources=sources,
            query=request.query,
            company=company_name or "All Companies",
        )
    
    except Exception as e:
        logger.error(f"RAG Query failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))