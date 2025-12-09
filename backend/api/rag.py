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
                "query": request.query,
                "top_k": request.top_k,
                "metric_type": "rag_query_start"
            }
        )

        # Run RAG pipeline with timing
        rag_company_filter = company_name if current_user["role"] != "super_admin" else None

        pipeline_start = time.time()
        result = pipeline.run(
            query=request.query,
            top_k=request.top_k,
            company_name=rag_company_filter,
        )
        pipeline_duration = time.time() - pipeline_start

        answer = result.answer
        metadata = result.metadata
        timings = result.timings or {}

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

        total_duration = time.time() - start_time

        # Calculate detailed breakdown
        retrieval_time = timings.get("retrieval", 0.0)
        generation_time = timings.get("generation", 0.0)
        cache_hit = timings.get("cache_hit", 0.0) == 1.0
        overhead_time = total_duration - pipeline_duration

        logger.info(
            "RAG Query completed",
            extra={
                "user_email": current_user['email'],
                "company": company_name,
                "query": request.query,
                "total_duration_seconds": total_duration,
                "pipeline_duration_seconds": pipeline_duration,
                "retrieval_duration_seconds": retrieval_time,
                "generation_duration_seconds": generation_time,
                "overhead_duration_seconds": overhead_time,
                "cache_hit": cache_hit,
                "sources_count": len(sources),
                "top_k": request.top_k,
                "metric_type": "rag_query_complete"
            }
        )

        return RAGQueryResponse(
            answer=answer,
            sources=sources,
            query=request.query,
            company=company_name or "All Companies",
            duration_seconds=total_duration,
            retrieval_duration_seconds=retrieval_time,
            generation_duration_seconds=generation_time,
            cache_hit=cache_hit
        )

    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            "RAG Query failed",
            extra={
                "user_email": current_user.get('email'),
                "company": current_user.get("company"),
                "query": request.query,
                "duration_seconds": duration,
                "error": str(e),
                "metric_type": "rag_query_error"
            },
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))
