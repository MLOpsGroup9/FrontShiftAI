"""
RAG query schemas
"""
from pydantic import BaseModel
from typing import List, Dict, Optional

class RAGQueryRequest(BaseModel):
    query: str
    top_k: int = 5

class RAGQueryResponse(BaseModel):
    answer: str
    sources: List[Dict]
    query: str
    company: str
    duration_seconds: Optional[float] = None
    retrieval_duration_seconds: Optional[float] = None
    generation_duration_seconds: Optional[float] = None
    cache_hit: Optional[bool] = None