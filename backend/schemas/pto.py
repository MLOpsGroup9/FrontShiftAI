"""
Pydantic schemas for PTO (Paid Time Off) operations
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from enum import Enum


class PTOStatus(str, Enum):
    """PTO request status"""
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    CANCELLED = "cancelled"


class PTORequestCreate(BaseModel):
    """Schema for creating a PTO request"""
    start_date: date
    end_date: date
    reason: Optional[str] = None


class PTORequestResponse(BaseModel):
    """Schema for PTO request response"""
    id: str
    email: str
    company: str
    start_date: date
    end_date: date
    days_requested: float
    reason: Optional[str] = None
    status: PTOStatus
    admin_notes: Optional[str] = None
    approved_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PTOBalanceResponse(BaseModel):
    """Schema for PTO balance response"""
    email: str
    company: str
    year: int
    total_days: float
    used_days: float
    pending_days: float
    remaining_days: float
    
    class Config:
        from_attributes = True


class PTOApprovalRequest(BaseModel):
    """Schema for approving/denying PTO request"""
    request_id: str
    status: PTOStatus  # approved or denied
    admin_notes: Optional[str] = None


class AgentChatRequest(BaseModel):
    """Schema for agent chat request"""
    message: str


class AgentChatResponse(BaseModel):
    """Schema for agent chat response"""
    response: str
    request_created: bool = False
    request_id: Optional[str] = None
    balance_info: Optional[dict] = None