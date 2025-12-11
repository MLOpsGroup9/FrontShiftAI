"""
PTO Agent Tools
Helper functions for PTO operations
"""
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import json
import logging
from sqlalchemy.orm import Session

from db.models import PTOBalance, PTORequest, CompanyHoliday, CompanyBlackoutDate, PTOStatus
from agents.utils.llm_client import get_llm_client

logger = logging.getLogger(__name__)


def calculate_business_days(start_date: date, end_date: date, holidays: List[date]) -> float:
    """
    Calculate business days between two dates excluding weekends and holidays
    
    Args:
        start_date: Start date
        end_date: End date
        holidays: List of holiday dates to exclude
        
    Returns:
        Number of business days (float to support half days)
    """
    if start_date > end_date:
        return 0.0
    
    business_days = 0.0
    current_date = start_date
    
    while current_date <= end_date:
        # Skip weekends (5=Saturday, 6=Sunday)
        if current_date.weekday() < 5:
            # Skip holidays
            if current_date not in holidays:
                business_days += 1.0
        current_date += timedelta(days=1)
    
    return business_days


def get_company_holidays(db: Session, company: str, year: int) -> List[date]:
    """
    Get all company holidays for a given year
    
    Args:
        db: Database session
        company: Company name
        year: Year to get holidays for
        
    Returns:
        List of holiday dates
    """
    holidays = db.query(CompanyHoliday).filter(
        CompanyHoliday.company == company
    ).all()
    
    holiday_dates = []
    for holiday in holidays:
        if holiday.holiday_date.year == year:
            holiday_dates.append(holiday.holiday_date)
    
    return holiday_dates


def check_blackout_periods(
    db: Session, 
    company: str, 
    start_date: date, 
    end_date: date
) -> Tuple[bool, List[str]]:
    """
    Check if requested dates fall within blackout periods
    
    Args:
        db: Database session
        company: Company name
        start_date: Request start date
        end_date: Request end date
        
    Returns:
        Tuple of (has_conflicts, list of conflict descriptions)
    """
    blackouts = db.query(CompanyBlackoutDate).filter(
        CompanyBlackoutDate.company == company
    ).all()
    
    conflicts = []
    
    for blackout in blackouts:
        # Check if requested dates overlap with blackout period
        if (start_date <= blackout.end_date and end_date >= blackout.start_date):
            conflicts.append(
                f"{blackout.period_name} ({blackout.start_date} to {blackout.end_date}): {blackout.reason}"
            )
    
    return len(conflicts) > 0, conflicts


def get_pto_balance(db: Session, email: str, year: int = 2025) -> Optional[Dict[str, Any]]:
    """
    Get PTO balance for a user
    
    Args:
        db: Database session
        email: User email
        year: Year to get balance for
        
    Returns:
        Dictionary with balance information or None
    """
    balance = db.query(PTOBalance).filter(
        PTOBalance.email == email,
        PTOBalance.year == year
    ).first()
    
    if not balance:
        return None
    
    return {
        "total_days": balance.total_days,
        "used_days": balance.used_days,
        "pending_days": balance.pending_days,
        "remaining_days": balance.remaining_days
    }


def check_conflicting_requests(
    db: Session,
    email: str,
    start_date: date,
    end_date: date
) -> Tuple[bool, List[Dict]]:
    """
    Check for overlapping PTO requests for the same user
    
    Args:
        db: Database session
        email: User email
        start_date: Request start date
        end_date: Request end date
        
    Returns:
        Tuple of (has_conflicts, list of conflicting requests)
    """
    # Get pending or approved requests that overlap
    requests = db.query(PTORequest).filter(
        PTORequest.email == email,
        PTORequest.status.in_([PTOStatus.PENDING, PTOStatus.APPROVED]),
        PTORequest.start_date <= end_date,
        PTORequest.end_date >= start_date
    ).all()
    
    conflicts = []
    for req in requests:
        conflicts.append({
            "id": req.id,
            "start_date": req.start_date.isoformat(),
            "end_date": req.end_date.isoformat(),
            "status": req.status.value,
            "days": req.days_requested
        })
    
    return len(conflicts) > 0, conflicts


async def parse_user_intent(user_message: str) -> Dict[str, Any]:
    """
    Use LLM to parse user message and extract intent and details
    
    Args:
        user_message: User's message
        
    Returns:
        Dictionary with parsed intent and extracted data
    """
    llm_client = get_llm_client()
    
    system_prompt = """You are a PTO (Paid Time Off) request assistant. 
    Analyze the user's message and extract:
    1. Intent: "request_pto", "check_balance", "view_requests", or "general_query"
    2. If requesting PTO: start_date, end_date, reason
    3. Dates should be in YYYY-MM-DD format
    
    Respond ONLY with valid JSON in this format:
    {
        "intent": "request_pto",
        "start_date": "2025-12-20",
        "end_date": "2025-12-27",
        "reason": "vacation"
    }
    
    For check_balance or view_requests, just return the intent.
    Today's date is: """ + datetime.now().strftime("%Y-%m-%d")
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]
    
    try:
        response = llm_client.chat(messages, json_mode=True, temperature=0.3)
        if response:
            parsed = json.loads(response)
            return parsed
        return {"intent": "general_query"}
    except Exception as e:
        logger.error(f"Error parsing user intent: {e}")
        return {"intent": "general_query", "error": str(e)}


def format_date_range(start_date: date, end_date: date) -> str:
    """Format date range for display"""
    return f"{start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}"