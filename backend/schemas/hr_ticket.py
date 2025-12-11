"""
Pydantic schemas for HR Ticket endpoints
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
from db.models import TicketCategory, MeetingType, TicketStatus, Urgency


# ==========================================
# REQUEST SCHEMAS
# ==========================================

class HRTicketChatRequest(BaseModel):
    """User sends message to create ticket"""
    message: str = Field(..., min_length=1, description="User's message describing their HR inquiry")


class PickTicketRequest(BaseModel):
    """Admin picks up a ticket"""
    ticket_id: str


class ScheduleMeetingRequest(BaseModel):
    """Admin schedules a meeting for a ticket"""
    ticket_id: str
    scheduled_datetime: datetime
    meeting_link: Optional[str] = None
    meeting_location: Optional[str] = None
    admin_notes: Optional[str] = None


class ResolveTicketRequest(BaseModel):
    """Admin resolves/closes a ticket"""
    ticket_id: str
    status: TicketStatus  # resolved or closed
    resolution_notes: Optional[str] = None


class AddNoteRequest(BaseModel):
    """Admin adds note to ticket"""
    ticket_id: str
    note: str


# ==========================================
# RESPONSE SCHEMAS
# ==========================================

class HRTicketResponse(BaseModel):
    """Complete ticket information"""
    id: str
    email: str
    company: str
    
    # Request details
    subject: str
    description: str
    category: TicketCategory
    meeting_type: MeetingType
    preferred_date: Optional[date]
    preferred_time_slot: Optional[str]
    urgency: Urgency
    
    # Queue management
    status: TicketStatus
    queue_position: Optional[int]
    created_at: datetime
    
    # Admin interaction
    assigned_to: Optional[str]
    admin_notes: Optional[str]
    picked_up_at: Optional[datetime]
    
    # Meeting details
    scheduled_datetime: Optional[datetime]
    meeting_link: Optional[str]
    meeting_location: Optional[str]
    
    # Resolution
    resolved_at: Optional[datetime]
    resolution_notes: Optional[str]
    
    updated_at: datetime

    class Config:
        from_attributes = True


class HRTicketChatResponse(BaseModel):
    """Response after user creates ticket via chat"""
    response: str
    ticket_created: bool
    ticket_id: Optional[str] = None
    queue_position: Optional[int] = None
    ticket_details: Optional[HRTicketResponse] = None


class HRTicketListResponse(BaseModel):
    """List of tickets"""
    tickets: List[HRTicketResponse]
    total_count: int


class TicketStatsResponse(BaseModel):
    """Admin dashboard statistics"""
    total_pending: int
    total_in_progress: int
    total_scheduled: int
    total_resolved_today: int
    total_closed_today: int
    average_resolution_time_hours: Optional[float]
    by_category: dict
    by_urgency: dict


class SimpleResponse(BaseModel):
    """Simple success message"""
    message: str
    ticket_id: Optional[str] = None


# ==========================================
# QUERY PARAMETERS (for documentation)
# ==========================================

class TicketQueueFilters(BaseModel):
    """Filters for admin queue"""
    status_filter: Optional[TicketStatus] = None
    category_filter: Optional[TicketCategory] = None
    urgency_filter: Optional[Urgency] = None
    sort_by: str = "created_at"  # created_at, urgency, category