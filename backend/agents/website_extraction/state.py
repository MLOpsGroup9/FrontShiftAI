"""Website Extraction Agent State Definition"""
from typing import TypedDict, Optional, List


class WebsiteExtractionState(TypedDict):
    # Input
    user_email: str
    company: str
    user_message: str
    original_query: Optional[str]
    triggered_by: str
    
    # Query Parsing
    search_topic: Optional[str]
    search_keywords: List[str]
    search_query: Optional[str]
    info_type: Optional[str]
    
    # Domain Resolution
    company_url: Optional[str]
    company_domain: Optional[str]
    domain_found: bool
    
    # Brave Search Results
    brave_results: List[dict]
    search_successful: bool
    search_error: Optional[str]
    
    # Result Analysis
    ranked_results: List[dict]
    best_match: Optional[dict]
    confidence_score: float
    found_answer: bool
    
    # Output
    answer: Optional[str]
    source_urls: List[str]
    suggest_hr_ticket: bool
    hr_ticket_suggestion: Optional[str]
    
    # Final Response
    agent_response: str
    
    # Metadata
    search_time_ms: Optional[float]
    error_message: Optional[str]

