"""
PTO Agent API Routes
Handles agent chat and PTO management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
import logging

from db.connection import get_db
from db.models import User, PTORequest, PTOBalance, PTOStatus
from schemas.pto import (
    AgentChatRequest,
    AgentChatResponse,
    PTORequestResponse,
    PTOBalanceResponse,
    PTOApprovalRequest
)
from api.auth import get_current_user
from agents.pto.agent import PTOAgent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pto", tags=["PTO Agent"])


@router.post("/chat", response_model=AgentChatResponse)
async def chat_with_agent(
    request: AgentChatRequest,
    current_user: dict = Depends(get_current_user),  # Changed from User
    db: Session = Depends(get_db)
):
    """
    Chat with PTO agent
    User can request PTO, check balance, view requests, or ask questions
    """
    try:
        # Initialize agent
        agent = PTOAgent(db)
        
        # Execute agent workflow
        result = await agent.execute(
            user_email=current_user["email"],  # Dictionary access
            company=current_user["company"],   # Dictionary access
            message=request.message
        )
        
        return AgentChatResponse(
            response=result["response"],
            request_created=result.get("request_created", False),
            request_id=result.get("request_id"),
            balance_info=result.get("balance_info")
        )
        
    except Exception as e:
        logger.error(f"Error in PTO agent chat: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process your request. Please try again."
        )


@router.get("/balance", response_model=PTOBalanceResponse)
def get_my_balance(
    current_user: dict = Depends(get_current_user),  # Changed from User
    db: Session = Depends(get_db)
):
    """
    Get current user's PTO balance
    """
    balance = db.query(PTOBalance).filter(
        PTOBalance.email == current_user["email"],  # Dictionary access
        PTOBalance.year == 2025
    ).first()
    
    if not balance:
        # Create default balance
        balance = PTOBalance(
            email=current_user["email"],
            company=current_user["company"],
            year=2025,
            total_days=15.0,
            used_days=0.0,
            pending_days=0.0
        )
        db.add(balance)
        db.commit()
        db.refresh(balance)
    
    return PTOBalanceResponse(
        email=balance.email,
        company=balance.company,
        year=balance.year,
        total_days=balance.total_days,
        used_days=balance.used_days,
        pending_days=balance.pending_days,
        remaining_days=balance.remaining_days
    )


@router.get("/requests", response_model=List[PTORequestResponse])
def get_my_requests(
    current_user: dict = Depends(get_current_user),  # Changed from User
    db: Session = Depends(get_db)
):
    """
    Get current user's PTO requests
    """
    requests = db.query(PTORequest).filter(
        PTORequest.email == current_user["email"]  # Dictionary access
    ).order_by(PTORequest.created_at.desc()).all()
    
    return [PTORequestResponse.model_validate(req) for req in requests]


@router.get("/admin/requests", response_model=List[PTORequestResponse])
def get_all_requests(
    status_filter: str = None,
    current_user: dict = Depends(get_current_user),  # Changed from User
    db: Session = Depends(get_db)
):
    """
    Get all PTO requests for company (Admin only)
    """
    if current_user["role"] != "company_admin":  # Dictionary access
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only company admins can view all requests"
        )
    
    query = db.query(PTORequest).filter(
        PTORequest.company == current_user["company"]  # Dictionary access
    )
    
    if status_filter:
        query = query.filter(PTORequest.status == status_filter)
    
    requests = query.order_by(PTORequest.created_at.desc()).all()
    
    return [PTORequestResponse.model_validate(req) for req in requests]


@router.post("/admin/approve")
def approve_or_deny_request(
    approval: PTOApprovalRequest,
    current_user: dict = Depends(get_current_user),  # Changed from User
    db: Session = Depends(get_db)
):
    """
    Approve or deny a PTO request (Admin only)
    """
    if current_user["role"] != "company_admin":  # Dictionary access
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only company admins can approve/deny requests"
        )
    
    # Get the request
    pto_request = db.query(PTORequest).filter(
        PTORequest.id == approval.request_id,
        PTORequest.company == current_user["company"]  # Dictionary access
    ).first()
    
    if not pto_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found"
        )
    
    if pto_request.status != PTOStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request has already been reviewed"
        )
    
    # Update request status
    pto_request.status = approval.status
    pto_request.admin_notes = approval.admin_notes
    pto_request.approved_by = current_user["email"]  # Dictionary access
    pto_request.reviewed_at = func.now()
    
    # Update user's balance
    balance = db.query(PTOBalance).filter(
        PTOBalance.email == pto_request.email,
        PTOBalance.year == 2025
    ).first()
    
    if balance:
        # Remove from pending
        balance.pending_days -= pto_request.days_requested
        
        if approval.status == PTOStatus.APPROVED:
            # Add to used days
            balance.used_days += pto_request.days_requested
        # If denied, just remove from pending (days return to available)
    
    db.commit()
    
    return {
        "message": f"Request {approval.status.value} successfully",
        "request_id": approval.request_id
    }


@router.get("/admin/balances", response_model=List[PTOBalanceResponse])
def get_all_balances(
    current_user: dict = Depends(get_current_user),  # Changed from User
    db: Session = Depends(get_db)
):
    """
    Get PTO balances for all employees in company (Admin only)
    """
    if current_user["role"] != "company_admin":  # Dictionary access
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only company admins can view all balances"
        )
    
    balances = db.query(PTOBalance).filter(
        PTOBalance.company == current_user["company"],  # Dictionary access
        PTOBalance.year == 2025
    ).all()
    
    return [PTOBalanceResponse.model_validate(bal) for bal in balances]


@router.put("/admin/balance/{email}")
def update_employee_balance(
    email: str,
    total_days: float,
    current_user: dict = Depends(get_current_user),  # Changed from User
    db: Session = Depends(get_db)
):
    """
    Update an employee's total PTO allocation (Admin only)
    """
    if current_user["role"] != "company_admin":  # Dictionary access
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only company admins can update balances"
        )
    
    balance = db.query(PTOBalance).filter(
        PTOBalance.email == email,
        PTOBalance.company == current_user["company"],  # Dictionary access
        PTOBalance.year == 2025
    ).first()
    
    if not balance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Balance record not found"
        )
    
    balance.total_days = total_days
    db.commit()
    
    return {
        "message": "Balance updated successfully",
        "email": email,
        "new_total": total_days
    }


@router.post("/admin/reset-balance/{email}")
def reset_employee_balance(
    email: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Reset an employee's used and pending days to 0 (Admin only)
    Useful for new year or corrections
    """
    if current_user["role"] != "company_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only company admins can reset balances"
        )
    
    balance = db.query(PTOBalance).filter(
        PTOBalance.email == email,
        PTOBalance.company == current_user["company"],
        PTOBalance.year == 2025
    ).first()
    
    if not balance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Balance record not found"
        )
    
    # Reset used and pending to 0
    old_used = balance.used_days
    old_pending = balance.pending_days
    
    balance.used_days = 0.0
    balance.pending_days = 0.0
    
    db.commit()
    
    return {
        "message": f"Balance reset successfully for {email}",
        "email": email,
        "previous_used": old_used,
        "previous_pending": old_pending,
        "new_used": 0.0,
        "new_pending": 0.0,
        "available_now": balance.remaining_days
    }


@router.post("/admin/reset-all-balances")
def reset_all_balances(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Reset used and pending days for ALL employees in the company to 0 (Admin only)
    Useful for new fiscal year
    """
    if current_user["role"] != "company_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only company admins can reset all balances"
        )
    
    # Get all balances for this company
    balances = db.query(PTOBalance).filter(
        PTOBalance.company == current_user["company"],
        PTOBalance.year == 2025
    ).all()
    
    if not balances:
        return {
            "message": "No balance records found",
            "employees_reset": 0
        }
    
    # Reset all
    reset_count = 0
    for balance in balances:
        balance.used_days = 0.0
        balance.pending_days = 0.0
        reset_count += 1
    
    db.commit()
    
    return {
        "message": f"Successfully reset balances for {reset_count} employees",
        "company": current_user["company"],
        "employees_reset": reset_count,
        "year": 2025
    }


@router.delete("/admin/balance/{email}")
def delete_employee_balance(
    email: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete an employee's PTO balance record (Admin only)
    """
    if current_user["role"] != "company_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only company admins can delete balances"
        )
    
    balance = db.query(PTOBalance).filter(
        PTOBalance.email == email,
        PTOBalance.company == current_user["company"],
        PTOBalance.year == 2025
    ).first()
    
    if not balance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Balance record not found"
        )
    
    db.delete(balance)
    db.commit()
    
    return {
        "message": f"Balance deleted successfully for {email}",
        "email": email
    }