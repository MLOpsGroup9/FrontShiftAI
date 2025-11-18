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
from company_mapping import validate_credentials, get_company_from_email, COMPANIES

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
    yield
    print("👋 RAG API shutting down...")

# ----------------------------
# Request/Response Models
# ----------------------------
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    company: str
    email: str

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
    company: str

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
        if email is None or company is None:
            return None
        return {"email": email, "company": company}
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
        is_valid, company = validate_credentials(request.email, request.password)
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": request.email, "company": company},
            expires_delta=access_token_expires
        )
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            company=company,
            email=request.email
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
        company=current_user["company"]
    )

@app.get("/api/companies")
def get_companies():
    """
    Get list of all available companies (for reference)
    """
    return {
        "companies": [
            {
                "name": c["company"],
                "domain": c["domain"],
                "email_domain": c["email_domain"]
            }
            for c in COMPANIES
        ]
    }

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
        company_name = current_user["company"]
        
        print(f"🔍 RAG Query from {current_user['email']} ({company_name}): {request.query}")
        
        # Run RAG pipeline with company filter
        result = pipeline.run(
            query=request.query,
            company_name=company_name,
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
            company=company_name,
        )
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# ----------------------------
# Run server directly
# ----------------------------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))