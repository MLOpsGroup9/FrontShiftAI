"""Pydantic schemas for Website Extraction Agent"""
from pydantic import BaseModel
from typing import Optional, List


class WebsiteSearchRequest(BaseModel):
    message: str


class WebsiteSearchResponse(BaseModel):
    response: str
    found_answer: bool
    answer: Optional[str] = None
    source_urls: List[str] = []
    confidence: float = 0.0
    suggest_hr_ticket: bool = False

