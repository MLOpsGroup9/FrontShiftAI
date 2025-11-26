"""
Company Management API - Add Company Pipeline
Handles adding new companies with automated pipeline processing
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, HttpUrl
import json
import subprocess
import os
from datetime import datetime
from typing import Optional
import uuid

from db.connection import get_db
from db.models import Company
from api.auth import get_current_user

router = APIRouter(prefix="/api/company", tags=["company_management"])

# Paths
URL_JSON_PATH = "/Users/sriks/Documents/Projects/FrontShiftAI/data_pipeline/data/url.json"
PIPELINE_SCRIPT = "/Users/sriks/Documents/Projects/FrontShiftAI/data_pipeline/scripts/pipeline_runner.py"
GCS_BUCKET = "gs://frontshiftai-data"
DATA_DIR = "/Users/sriks/Documents/Projects/FrontShiftAI/data_pipeline/data"

# In-memory task tracking (in production, use Redis or database)
processing_tasks = {}


class AddCompanyRequest(BaseModel):
    company_name: str
    domain: str
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


async def process_company_pipeline(
    task_id: str,
    company_name: str,
    domain: str,
    url: str,
    db: Session
):
    """
    Background task to:
    1. Update url.json
    2. Add to database
    3. Run pipeline
    4. Sync to GCS
    """
    try:
        # Update task status
        processing_tasks[task_id]["status"] = "running"
        processing_tasks[task_id]["started_at"] = datetime.now()
        
        # Step 1: Update url.json
        processing_tasks[task_id]["message"] = "Updating url.json..."
        
        with open(URL_JSON_PATH, 'r') as f:
            companies_data = json.load(f)
        
        # Add new company
        new_company = {
            "domain": domain,
            "company": company_name,
            "url": str(url)
        }
        companies_data.append(new_company)
        
        # Write back to file
        with open(URL_JSON_PATH, 'w') as f:
            json.dump(companies_data, f, indent=4)
        
        # Step 2: Add to database
        processing_tasks[task_id]["message"] = "Adding to database..."
        
        # Extract email domain from company name
        email_domain = company_name.lower().replace(" ", "").replace("&", "") + ".com"
        
        db_company = Company(
            name=company_name,
            domain=domain,
            email_domain=email_domain,
            url=str(url)
        )
        db.add(db_company)
        db.commit()
        
        # Step 3: Run pipeline
        processing_tasks[task_id]["message"] = "Running data pipeline..."
        
        # Set environment variable for subprocess
        env = os.environ.copy()
        
        result = subprocess.run(
            ["python", PIPELINE_SCRIPT],
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout
            env=env
        )
        
        if result.returncode != 0:
            raise Exception(f"Pipeline failed: {result.stderr}")
        
        # Step 4: Sync to GCS
        processing_tasks[task_id]["message"] = "Syncing to Google Cloud Storage..."
        
        # Use gsutil rsync
        sync_result = subprocess.run(
            ["gsutil", "-m", "rsync", "-r", DATA_DIR, GCS_BUCKET],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            env=env
        )
        
        if sync_result.returncode != 0:
            raise Exception(f"GCS sync failed: {sync_result.stderr}")
        
        # Success!
        processing_tasks[task_id]["status"] = "completed"
        processing_tasks[task_id]["message"] = "Company added successfully!"
        processing_tasks[task_id]["completed_at"] = datetime.now()
        
    except subprocess.TimeoutExpired:
        processing_tasks[task_id]["status"] = "failed"
        processing_tasks[task_id]["error"] = "Pipeline execution timeout"
        processing_tasks[task_id]["completed_at"] = datetime.now()
        
        # Rollback database
        db.rollback()
        
    except Exception as e:
        processing_tasks[task_id]["status"] = "failed"
        processing_tasks[task_id]["error"] = str(e)
        processing_tasks[task_id]["completed_at"] = datetime.now()
        
        # Rollback database
        db.rollback()


@router.post("/add", response_model=AddCompanyResponse)
async def add_company(
    request: AddCompanyRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add a new company to the system.
    This triggers:
    1. Update to url.json
    2. Database entry
    3. Pipeline processing
    4. GCS sync
    """
    verify_super_admin(current_user)
    
    # Check if company already exists
    existing = db.query(Company).filter(Company.name == request.company_name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Company already exists")
    
    # Create task ID
    task_id = str(uuid.uuid4())
    
    # Initialize task tracking
    processing_tasks[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "message": "Task queued for processing",
        "error": None,
        "started_at": None,
        "completed_at": None
    }
    
    # Add background task
    background_tasks.add_task(
        process_company_pipeline,
        task_id,
        request.company_name,
        request.domain,
        str(request.url),
        db
    )
    
    return AddCompanyResponse(
        message="Company processing started",
        task_id=task_id,
        company_name=request.company_name
    )


@router.get("/task-status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get the status of a company processing task"""
    verify_super_admin(current_user)
    
    if task_id not in processing_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return processing_tasks[task_id]