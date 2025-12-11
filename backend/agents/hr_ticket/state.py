"""
State definition for HR Ticket Agent
"""
from typing import TypedDict, Optional, List
from datetime import date


class HRTicketState(TypedDict):
    """
    State that flows through the HR Ticket Agent workflow.
    Each node reads from and writes to this state.
    """
    # Input
    user_email: str
    company: str
    user_message: str
    
    # Parsed data from LLM
    intent: str  # "create_ticket", "check_status", "cancel_ticket"
    subject: Optional[str]
    description: Optional[str]
    category: Optional[str]  # Will be TicketCategory enum value
    meeting_type: Optional[str]  # Will be MeetingType enum value
    preferred_date: Optional[date]
    preferred_time_slot: Optional[str]  # "morning", "afternoon", "evening", "anytime"
    urgency: str  # "normal" or "urgent"
    
    # Validation
    is_valid: bool
    validation_errors: List[str]
    
    # Duplicate check
    has_open_tickets: bool
    open_ticket_ids: List[str]
    
    # Output
    ticket_id: Optional[str]
    queue_position: Optional[int]
    agent_response: str