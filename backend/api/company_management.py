"""
Company Management API - Add Company Pipeline
Handles adding new companies with automated pipeline processing
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, HttpUrl
import uuid
from datetime import datetime, timezone
from typing import Optional

from db.connection import get_db
from db.models import Company, Task
from api.auth import get_current_user
from jobs.tasks import process_company_pipeline_task

router = APIRouter(prefix="/api/company", tags=["company_management"])

class AddCompanyRequest(BaseModel):
    company_name: str
    domain: str
    email_domain: str  # Added manual entry
    url: HttpUrl


class AddCompanyResponse(BaseModel):
    message: str
    task_id: str
    company_name: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str  # pending, running, completed, failed
    message: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


def verify_super_admin(current_user: dict):
    """Verify user is super admin"""
    if current_user.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Super admin access required")


@router.post("/add", response_model=AddCompanyResponse)
async def add_company(
    request: AddCompanyRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add a new company to the system.
    This triggers a background Celery task.
    """
    verify_super_admin(current_user)
    
    # Check if company already exists
    existing = db.query(Company).filter(Company.name == request.company_name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Company already exists")
    
    # Create task ID
    task_id = str(uuid.uuid4())
    
    # Create Task record in DB
    new_task = Task(
        id=task_id,
        status="pending",
        message="Task queued for processing",
        task_type="company_ingestion",
        payload=str(request.model_dump())
    )
    db.add(new_task)
    
    # Add company to DB immediately (so we have the record)
    # Use provided email domain
    email_domain = request.email_domain.lower().strip()
    if not email_domain.startswith('.'):
        if '@' in email_domain:
             email_domain = email_domain.split('@')[-1] # take part after @
        # If it doesn't represent a domain structure, we assume user knows what they are doing or we enforce it.
        # Let's just ensure it's saved as provided but clean.

    
    db_company = Company(
        name=request.company_name,
        domain=request.domain,
        email_domain=email_domain,
        url=str(request.url)
    )
    db.add(db_company)
    db.commit()
    
    # Trigger Celery task
    process_company_pipeline_task.delay(
        task_id,
        request.company_name,
        request.domain,
        str(request.url)
    )
    
    return AddCompanyResponse(
        message="Company processing started",
        task_id=task_id,
        company_name=request.company_name
    )


@router.get("/task-status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the status of a company processing task"""
    verify_super_admin(current_user)
    
    task = db.query(Task).filter(Task.id == task_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskStatusResponse(
        task_id=task.id,
        status=task.status,
        message=task.message,
        error=task.error,
        started_at=task.started_at,
        completed_at=task.completed_at
    )


@router.delete("/delete", response_model=AddCompanyResponse)
async def delete_company(
    company_name: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a company and trigger rebuild.
    """
    verify_super_admin(current_user)
    
    # Check if company exists
    company = db.query(Company).filter(Company.name == company_name).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Create task ID
    task_id = str(uuid.uuid4())
    
    # Create Task record in DB
    new_task = Task(
        id=task_id,
        status="pending",
        message="Deletion task queued",
        task_type="company_deletion",
        payload=str({"company_name": company_name})
    )
    db.add(new_task)
    
    # Delete from DB immediately
    db.delete(company)
    db.commit()
    
    # Trigger Celery task (we reuse the same generic pipeline task wrapper or create a new one)
    # Ideally should be a separate task, but for now we can use a new task function
    from jobs.tasks import process_delete_company_task
    process_delete_company_task.delay(task_id, company_name)
    
    return AddCompanyResponse(
        message="Company deletion started",
        task_id=task_id,
        company_name=company_name
    )