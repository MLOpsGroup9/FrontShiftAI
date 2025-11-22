"""
Utility functions for HR Ticket Agent
"""
from sqlalchemy.orm import Session
from db.models import HRTicket, TicketStatus, User, UserRole
from typing import Tuple, List, Dict, Optional
from datetime import date, datetime
import uuid


def check_open_tickets(db: Session, user_email: str, company: str) -> Tuple[bool, List[str]]:
    """
    Check if user has any open tickets (pending, in_progress, or scheduled).
    
    Returns:
        Tuple of (has_open_tickets, list_of_ticket_ids)
    """
    open_statuses = [TicketStatus.PENDING, TicketStatus.IN_PROGRESS, TicketStatus.SCHEDULED]
    
    open_tickets = db.query(HRTicket).filter(
        HRTicket.email == user_email,
        HRTicket.company == company,
        HRTicket.status.in_(open_statuses)
    ).all()
    
    has_open = len(open_tickets) > 0
    ticket_ids = [ticket.id for ticket in open_tickets]
    
    return has_open, ticket_ids


def calculate_queue_position(db: Session, company: str) -> int:
    """
    Calculate the queue position for a new ticket.
    Position is based on number of pending tickets + 1.
    """
    pending_count = db.query(HRTicket).filter(
        HRTicket.company == company,
        HRTicket.status == TicketStatus.PENDING
    ).count()
    
    return pending_count + 1


def create_ticket_in_db(
    db: Session,
    email: str,
    company: str,
    subject: str,
    description: str,
    category: str,
    meeting_type: str,
    urgency: str,
    preferred_date: Optional[date] = None,
    preferred_time_slot: Optional[str] = None
) -> Tuple[str, int]:
    """
    Create a new HR ticket in the database.
    
    Returns:
        Tuple of (ticket_id, queue_position)
    """
    from db.models import TicketCategory, MeetingType, Urgency
    
    ticket_id = str(uuid.uuid4())
    queue_position = calculate_queue_position(db, company)
    
    new_ticket = HRTicket(
        id=ticket_id,
        email=email,
        company=company,
        subject=subject,
        description=description,
        category=TicketCategory(category),
        meeting_type=MeetingType(meeting_type),
        urgency=Urgency(urgency),
        preferred_date=preferred_date,
        preferred_time_slot=preferred_time_slot,
        status=TicketStatus.PENDING,
        queue_position=queue_position
    )
    
    db.add(new_ticket)
    db.commit()
    db.refresh(new_ticket)
    
    return ticket_id, queue_position


def get_ticket_by_id(db: Session, ticket_id: str, company: str) -> Optional[HRTicket]:
    """Get a ticket by ID, ensuring it belongs to the company"""
    return db.query(HRTicket).filter(
        HRTicket.id == ticket_id,
        HRTicket.company == company
    ).first()


def get_user_tickets(db: Session, email: str, company: str) -> List[HRTicket]:
    """Get all tickets for a user"""
    return db.query(HRTicket).filter(
        HRTicket.email == email,
        HRTicket.company == company
    ).order_by(HRTicket.created_at.desc()).all()


def validate_date(preferred_date: Optional[date]) -> Tuple[bool, Optional[str]]:
    """
    Validate preferred date if provided.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if preferred_date is None:
        return True, None
    
    if preferred_date < date.today():
        return False, "Preferred date cannot be in the past"
    
    return True, None


def is_company_admin(db: Session, email: str, company: str) -> bool:
    """Check if user is a company admin for the given company"""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return False
    
    return user.role == UserRole.COMPANY_ADMIN and user.company == company


def get_ticket_stats(db: Session, company: str) -> Dict:
    """
    Get statistics for admin dashboard.
    """
    from sqlalchemy import func
    
    # Count by status
    total_pending = db.query(HRTicket).filter(
        HRTicket.company == company,
        HRTicket.status == TicketStatus.PENDING
    ).count()
    
    total_in_progress = db.query(HRTicket).filter(
        HRTicket.company == company,
        HRTicket.status == TicketStatus.IN_PROGRESS
    ).count()
    
    total_scheduled = db.query(HRTicket).filter(
        HRTicket.company == company,
        HRTicket.status == TicketStatus.SCHEDULED
    ).count()
    
    # Resolved/closed today
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    total_resolved_today = db.query(HRTicket).filter(
        HRTicket.company == company,
        HRTicket.status == TicketStatus.RESOLVED,
        HRTicket.resolved_at >= today_start
    ).count()
    
    total_closed_today = db.query(HRTicket).filter(
        HRTicket.company == company,
        HRTicket.status == TicketStatus.CLOSED,
        HRTicket.resolved_at >= today_start
    ).count()
    
    # Count by category
    category_counts = db.query(
        HRTicket.category,
        func.count(HRTicket.id)
    ).filter(
        HRTicket.company == company,
        HRTicket.status.in_([TicketStatus.PENDING, TicketStatus.IN_PROGRESS, TicketStatus.SCHEDULED])
    ).group_by(HRTicket.category).all()
    
    by_category = {str(cat): count for cat, count in category_counts}
    
    # Count by urgency
    urgency_counts = db.query(
        HRTicket.urgency,
        func.count(HRTicket.id)
    ).filter(
        HRTicket.company == company,
        HRTicket.status.in_([TicketStatus.PENDING, TicketStatus.IN_PROGRESS, TicketStatus.SCHEDULED])
    ).group_by(HRTicket.urgency).all()
    
    by_urgency = {str(urg): count for urg, count in urgency_counts}
    
    # Calculate average resolution time (in hours)
    resolved_tickets = db.query(HRTicket).filter(
        HRTicket.company == company,
        HRTicket.status.in_([TicketStatus.RESOLVED, TicketStatus.CLOSED]),
        HRTicket.resolved_at.isnot(None)
    ).all()
    
    avg_resolution_time = None
    if resolved_tickets:
        total_time = sum([
            (ticket.resolved_at - ticket.created_at).total_seconds() / 3600
            for ticket in resolved_tickets
        ])
        avg_resolution_time = round(total_time / len(resolved_tickets), 2)
    
    return {
        "total_pending": total_pending,
        "total_in_progress": total_in_progress,
        "total_scheduled": total_scheduled,
        "total_resolved_today": total_resolved_today,
        "total_closed_today": total_closed_today,
        "average_resolution_time_hours": avg_resolution_time,
        "by_category": by_category,
        "by_urgency": by_urgency
    }