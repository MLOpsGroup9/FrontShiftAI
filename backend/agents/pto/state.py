"""
PTO Agent State Definition
Tracks data flow through the LangGraph workflow
"""
from typing import TypedDict, Optional, List, Annotated
from datetime import date
import operator


class PTOAgentState(TypedDict):
    """
    State that flows through the PTO agent graph
    Each node can read and update this state
    """
    
    # Input from user
    user_email: str
    company: str
    user_message: str
    
    # Parsed request data (extracted by LLM)
    start_date: Optional[date]
    end_date: Optional[date]
    reason: Optional[str]
    intent: Optional[str]  # "request_pto", "check_balance", "view_requests", "general_query"
    
    # Validation results
    is_valid: bool
    validation_errors: Annotated[List[str], operator.add]  # Accumulate errors
    
    # Date calculations
    total_business_days: Optional[float]
    holiday_dates: Annotated[List[date], operator.add]
    blackout_conflicts: Annotated[List[str], operator.add]
    
    # Balance check
    current_balance: Optional[float]
    used_days: Optional[float]
    pending_days: Optional[float]
    remaining_days: Optional[float]
    has_sufficient_balance: bool
    
    # Conflict check
    has_conflicts: bool
    conflicting_requests: Annotated[List[dict], operator.add]
    
    # Request creation
    request_id: Optional[str]
    request_created: bool
    
    # Final response
    agent_response: str
    should_end: bool  # Signal to end the workflow
    
    # Error handling
    error_message: Optional[str]