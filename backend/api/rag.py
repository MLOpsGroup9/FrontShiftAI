"""
RAG query API endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from schemas import RAGQueryRequest, RAGQueryResponse
from services import normalize_metadata_company_name
from api.auth import get_current_user
from chat_pipeline.rag.pipeline import RAGPipeline

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
    try:
        company_name = current_user.get("company")
        
        if current_user["role"] != "super_admin" and not company_name:
            raise HTTPException(
                status_code=403,
                detail="No company associated with this user"
            )
        
        print(f"🔍 RAG Query from {current_user['email']} ({company_name}): {request.query}")
        
        # Run RAG pipeline
        result = pipeline.run(
            query=request.query,
            top_k=request.top_k * 3 if current_user["role"] != "super_admin" else request.top_k,
            company_name=None,
        )
        
        answer = result.answer
        metadata = result.metadata
        
        print(f"📊 Retrieved {len(metadata)} documents before filtering")
        
        # Manual filtering by company for non-super-admins
        if current_user["role"] != "super_admin" and company_name:
            filtered_metadata = []
            for meta in metadata:
                meta_company = meta.get("company", "")
                if normalize_metadata_company_name(meta_company, company_name):
                    filtered_metadata.append(meta)
            
            if filtered_metadata:
                metadata = filtered_metadata[:request.top_k]
                print(f"✅ Filtered to {len(metadata)} results for {company_name}")
        
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
        
        return RAGQueryResponse(
            answer=answer,
            sources=sources,
            query=request.query,
            company=company_name or "All Companies",
        )
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))