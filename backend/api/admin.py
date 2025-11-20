"""
Admin API endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from schemas import CreateUserRequest, UpdatePasswordRequest, DeleteUserRequest
from services import (
    get_all_company_admins, get_all_companies,
    get_users_by_company, add_user, delete_user, update_user_password
)
from api.auth import get_current_user
from db import get_db

router = APIRouter(prefix="/api/admin", tags=["Admin"])

def require_admin(current_user: dict, required_role: str = "company_admin"):
    """Check if user has admin permissions"""
    user_role = current_user.get("role")
    
    if required_role == "super_admin" and user_role != "super_admin":
        raise HTTPException(status_code=403, detail="Super admin access required")
    
    if required_role == "company_admin" and user_role not in ["super_admin", "company_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")

@router.get("/company-admins")
async def get_company_admins(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all company admins (Super Admin only)"""
    require_admin(current_user, "super_admin")
    admins = get_all_company_admins(db)
    return {"admins": admins}

@router.get("/all-companies")
async def get_all_companies_admin(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all companies (Super Admin only)"""
    require_admin(current_user, "super_admin")
    companies = get_all_companies(db)
    return {"companies": companies}

@router.post("/add-company-admin")
async def add_company_admin(
    request: CreateUserRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a new company admin (Super Admin only)"""
    require_admin(current_user, "super_admin")
    
    success, message = add_user(
        email=request.email,
        password=request.password,
        company=request.company,
        name=request.name,
        role="company_admin",
        db=db
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message, "email": request.email}

@router.delete("/delete-company-admin")
async def delete_company_admin(
    request: DeleteUserRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a company admin (Super Admin only)"""
    require_admin(current_user, "super_admin")
    
    success, message = delete_user(request.email, db)
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message}

@router.get("/company-users")
async def get_company_users(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all users in admin's company (Company Admin only)"""
    require_admin(current_user, "company_admin")
    
    company = current_user.get("company")
    if not company:
        raise HTTPException(status_code=400, detail="No company associated with this admin")
    
    users = get_users_by_company(company, db)
    return {"users": users, "company": company}

@router.post("/add-user")
async def add_company_user(
    request: CreateUserRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a new user to admin's company (Company Admin only)"""
    require_admin(current_user, "company_admin")
    
    if current_user["role"] == "company_admin":
        company = current_user.get("company")
        if not company:
            raise HTTPException(status_code=400, detail="No company associated with this admin")
    else:
        # Super admin can specify company
        company = request.company
    
    success, message = add_user(
        email=request.email,
        password=request.password,
        company=company,
        name=request.name,
        role="user",
        db=db
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message, "email": request.email}

@router.delete("/delete-user")
async def delete_company_user(
    request: DeleteUserRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a user from admin's company (Company Admin only)"""
    require_admin(current_user, "company_admin")
    
    # Verify user belongs to admin's company
    if current_user["role"] == "company_admin":
        company = current_user.get("company")
        users = get_users_by_company(company, db)
        user_emails = [u["email"] for u in users]
        
        if request.email not in user_emails:
            raise HTTPException(
                status_code=403,
                detail="Cannot delete users from other companies"
            )
    
    success, message = delete_user(request.email, db)
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message}

@router.put("/update-password")
async def update_password(
    request: UpdatePasswordRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user password (Admin only)"""
    require_admin(current_user, "company_admin")
    
    success, message = update_user_password(request.email, request.new_password, db)
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message}

@router.get("/companies")
def get_companies(db: Session = Depends(get_db)):
    """Get list of all available companies"""
    companies = get_all_companies(db)
    return {"companies": companies}