"""
RAG query schemas
"""
from pydantic import BaseModel
from typing import List, Dict

class RAGQueryRequest(BaseModel):
    query: str
    top_k: int = 5

class RAGQueryResponse(BaseModel):
    answer: str
    sources: List[Dict]
    query: str
    company: str