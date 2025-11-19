import os
import sys
from pathlib import Path
from typing import Optional, List, Dict
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv
import uvicorn
import jwt

# Load environment variables
load_dotenv()

# Ensure project root is in Python path
current_file = Path(__file__).resolve()
project_root = current_file.parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import your RAG pipeline and company mapping
from chat_pipeline.rag.pipeline import RAGPipeline
from auth_service import validate_credentials, get_company_from_email, get_all_companies

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Create RAG pipeline instance
pipeline = RAGPipeline()

# Security
security = HTTPBearer()

# ----------------------------
# FASTAPI APP
# ----------------------------
app = FastAPI(
    title="FrontShiftAI RAG API",
    version="1.0.0",
)

# ----------------------------
# CORS SETTINGS
# ----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------
# Lifespan Events
# ----------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 RAG API starting up...")
    
    # Initialize database
    from database import init_db, seed_initial_data
    init_db()
    seed_initial_data()
    
    yield
    print("👋 RAG API shutting down...")

app.router.lifespan_context = lifespan

# ----------------------------
# Request/Response Models
# ----------------------------
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    company: Optional[str] = None
    email: str
    role: str

class RAGQueryRequest(BaseModel):
    query: str
    top_k: int = 5

class RAGQueryResponse(BaseModel):
    answer: str
    sources: List[Dict]
    query: str
    company: str

class UserInfo(BaseModel):
    email: str
    company: Optional[str] = None
    role: str

# ----------------------------
# JWT Token Functions
# ----------------------------
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        company: str = payload.get("company")
        role: str = payload.get("role")
        if email is None or role is None:
            return None
        return {"email": email, "company": company, "role": role}
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    user_data = decode_access_token(token)
    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    return user_data

# ----------------------------
# Health Check
# ----------------------------
@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "pipeline_ready": True,
    }

# ----------------------------
# Authentication Endpoints
# ----------------------------
@app.post("/api/auth/login", response_model=LoginResponse)
def login(request: LoginRequest):
    """
    Login endpoint - validates credentials and returns JWT token
    """
    try:
        # Validate credentials
        is_valid, company, role = validate_credentials(request.email, request.password)
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": request.email, "company": company, "role": role},
            expires_delta=access_token_expires
        )
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            company=company,
            email=request.email,
            role=role
        )
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/auth/me", response_model=UserInfo)
async def get_user_info(current_user: dict = Depends(get_current_user)):
    """
    Get current user information from token
    """
    return UserInfo(
        email=current_user["email"],
        company=current_user.get("company"),
        role=current_user["role"]
    )

@app.get("/api/companies")
def get_companies():
    """
    Get list of all available companies (for reference)
    """
    companies = get_all_companies()
    return {"companies": companies}

# ----------------------------
# Main RAG Query Endpoint (Protected)
# ----------------------------
@app.post("/api/rag/query", response_model=RAGQueryResponse)
async def rag_query(
    request: RAGQueryRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    RAG query endpoint - requires authentication
    Automatically filters results by user's company
    """
    try:
        # Get user's company from token
        company_name = current_user.get("company")
        
        # Super admin can access all companies, otherwise filter by user's company
        if current_user["role"] != "super_admin" and not company_name:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No company associated with this user"
            )
        
        print(f"🔍 RAG Query from {current_user['email']} ({company_name}): {request.query}")
        
        # Run RAG pipeline
        result = pipeline.run(
            query=request.query,
            top_k=request.top_k,
        )
        
        answer = result.answer
        metadata = result.metadata
        
        # Format sources for frontend
        sources = [
            {
                "company": m.get("company", "unknown"),
                "filename": m.get("filename", "unknown"),
                "chunk_id": m.get("chunk_id", "?"),
                "text": m.get("text", ""),
                "doc_title": m.get("doc_title", ""),
                "section_title": m.get("section_title", ""),
            }
            for m in metadata
        ]
        
        return RAGQueryResponse(
            answer=answer,
            sources=sources,
            query=request.query,
            company=company_name or "All Companies",
        )
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    
# ----------------------------
# Admin Endpoints
# ----------------------------

# Pydantic models for admin operations
class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    company: Optional[str] = None
    role: str = "user"

class UpdatePasswordRequest(BaseModel):
    email: EmailStr
    new_password: str

class DeleteUserRequest(BaseModel):
    email: EmailStr

# Helper function to check admin permissions
def require_admin(current_user: dict, required_role: str = "company_admin"):
    """Check if user has admin permissions"""
    user_role = current_user.get("role")
    
    if required_role == "super_admin" and user_role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )
    
    if required_role == "company_admin" and user_role not in ["super_admin", "company_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

# Super Admin: Get all company admins
@app.get("/api/admin/company-admins")
async def get_company_admins(current_user: dict = Depends(get_current_user)):
    """Get all company admins (Super Admin only)"""
    require_admin(current_user, "super_admin")
    
    from auth_service import get_all_company_admins
    admins = get_all_company_admins()
    return {"admins": admins}

# Super Admin: Get all companies
@app.get("/api/admin/all-companies")
async def get_all_companies_admin(current_user: dict = Depends(get_current_user)):
    """Get all companies (Super Admin only)"""
    require_admin(current_user, "super_admin")
    
    companies = get_all_companies()
    return {"companies": companies}

# Super Admin: Add company admin
@app.post("/api/admin/add-company-admin")
async def add_company_admin(
    request: CreateUserRequest,
    current_user: dict = Depends(get_current_user)
):
    """Add a new company admin (Super Admin only)"""
    require_admin(current_user, "super_admin")
    
    from auth_service import add_user
    success, message = add_user(
        email=request.email,
        password=request.password,
        company=request.company,
        name=request.name,
        role="company_admin"
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message, "email": request.email}

# Super Admin: Delete company admin
@app.delete("/api/admin/delete-company-admin")
async def delete_company_admin(
    request: DeleteUserRequest,
    current_user: dict = Depends(get_current_user)
):
    """Delete a company admin (Super Admin only)"""
    require_admin(current_user, "super_admin")
    
    from auth_service import delete_user
    success, message = delete_user(request.email)
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message}

# Company Admin: Get users in their company
@app.get("/api/admin/company-users")
async def get_company_users(current_user: dict = Depends(get_current_user)):
    """Get all users in admin's company (Company Admin only)"""
    require_admin(current_user, "company_admin")
    
    company = current_user.get("company")
    if not company:
        raise HTTPException(
            status_code=400,
            detail="No company associated with this admin"
        )
    
    from auth_service import get_users_by_company
    users = get_users_by_company(company)
    return {"users": users, "company": company}

# Company Admin: Add user to their company
@app.post("/api/admin/add-user")
async def add_company_user(
    request: CreateUserRequest,
    current_user: dict = Depends(get_current_user)
):
    """Add a new user to admin's company (Company Admin only)"""
    require_admin(current_user, "company_admin")
    
    # Company admins can only add users to their own company
    if current_user["role"] == "company_admin":
        company = current_user.get("company")
        if not company:
            raise HTTPException(status_code=400, detail="No company associated with this admin")
    else:
        # Super admin can specify company
        company = request.company
    
    from auth_service import add_user
    success, message = add_user(
        email=request.email,
        password=request.password,
        company=company,
        name=request.name,
        role="user"
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message, "email": request.email}

# Company Admin: Delete user from their company
@app.delete("/api/admin/delete-user")
async def delete_company_user(
    request: DeleteUserRequest,
    current_user: dict = Depends(get_current_user)
):
    """Delete a user from admin's company (Company Admin only)"""
    require_admin(current_user, "company_admin")
    
    # Verify user belongs to admin's company
    if current_user["role"] == "company_admin":
        from auth_service import get_users_by_company
        company = current_user.get("company")
        users = get_users_by_company(company)
        user_emails = [u["email"] for u in users]
        
        if request.email not in user_emails:
            raise HTTPException(
                status_code=403,
                detail="Cannot delete users from other companies"
            )
    
    from auth_service import delete_user
    success, message = delete_user(request.email)
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message}

# Both admins: Update user password
@app.put("/api/admin/update-password")
async def update_password(
    request: UpdatePasswordRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update user password (Admin only)"""
    require_admin(current_user, "company_admin")
    
    from auth_service import update_user_password
    success, message = update_user_password(request.email, request.new_password)
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message}

# ----------------------------
# Run server directly
# ----------------------------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))