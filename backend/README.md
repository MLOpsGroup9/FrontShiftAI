# FrontShiftAI Backend

Multi-tenant RAG (Retrieval-Augmented Generation) system providing AI-powered access to company handbook information across 19+ organizations.

## 🚀 Quick Start
```bash
# Navigate to backend
cd ~/Documents/Projects/FrontShiftAI/backend

# Activate virtual environment
source venv/bin/activate  # Mac/Linux
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or simply
python main.py
```

Access API documentation: http://localhost:8000/docs

## 📁 Project Structure
```
backend/
├── api/                     # API Layer - HTTP Endpoints
│   ├── __init__.py
│   ├── admin.py            # Admin management endpoints
│   ├── auth.py             # Authentication & JWT handling
│   └── rag.py              # RAG query endpoints
│
├── db/                      # Database Layer
│   ├── __init__.py
│   ├── connection.py       # SQLAlchemy engine & session
│   ├── models.py           # Database models (ORM)
│   └── seed.py             # Initial data seeding
│
├── schemas/                 # Schema Layer - Data Validation
│   ├── __init__.py
│   ├── auth.py             # Login/register request schemas
│   └── rag.py              # RAG query/response schemas
│
├── services/                # Business Logic Layer
│   ├── __init__.py
│   ├── auth_service.py     # User authentication logic
│   └── rag_service.py      # Company name normalization
│
├── tests/                   # Test Suite
│   ├── __init__.py
│   ├── conftest.py         # Pytest fixtures & configuration
│   ├── test_api/           # API endpoint tests
│   │   ├── test_admin.py
│   │   ├── test_auth.py
│   │   └── test_rag.py
│   ├── test_db/            # Database layer tests
│   │   ├── test_connection.py
│   │   ├── test_models.py
│   │   └── test_seed.py
│   ├── test_schemas/       # Schema validation tests
│   │   └── test_schemas.py
│   └── test_services/      # Service layer tests
│       ├── test_auth_service.py
│       └── test_rag_service.py
│
├── mytests/                 # Legacy tests (kept for reference)
│
├── .env                     # Environment variables (create this)
├── .pytest_cache/          # Pytest cache (auto-generated)
├── __pycache__/            # Python cache (auto-generated)
├── main.py                 # FastAPI application entry point
├── pytest.ini              # Pytest configuration
├── rag_cli.py              # CLI tool for testing RAG queries
├── README.md               # This file
├── requirements.txt        # Python dependencies
└── users.db                # SQLite database (auto-generated)
```

## 📄 Detailed File Descriptions

### Core Files

#### `main.py`
**Purpose**: FastAPI application entry point

**What it does**:
- Creates the FastAPI app instance
- Configures CORS middleware for cross-origin requests
- Registers all API routers (auth, rag, admin)
- Sets up lifespan events (startup/shutdown)
- Initializes and seeds database on startup
- Provides health check endpoint

**Key functions**:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs on startup
    init_db()
    seed_initial_data()
    yield
    # Runs on shutdown

app = FastAPI(title="FrontShiftAI API", version="2.0.0")
app.include_router(auth.router)
app.include_router(rag.router)
app.include_router(admin.router)
```

**When to modify**: Adding new routers, changing CORS settings, modifying startup behavior

---

#### `rag_cli.py`
**Purpose**: Command-line interface for testing RAG queries

**What it does**:
- Provides interactive terminal interface for RAG testing
- Uses the same RAG pipeline as the API
- Doesn't require authentication
- Useful for debugging and development

**Usage**:
```bash
python rag_cli.py
You: What is the PTO policy?
```

**When to modify**: Testing different RAG configurations, debugging pipeline issues

---

#### `users.db`
**Purpose**: SQLite database file (auto-generated)

**What it contains**:
- Users table (authentication data)
- Companies table (organization info)
- PTO-related tables (for future agents)
- Session/audit data

**How to inspect**:
```bash
sqlite3 users.db
sqlite> .tables
sqlite> SELECT * FROM users;
```

**When to reset**:
```bash
rm users.db
python -c "from db import init_db; from db.seed import seed_initial_data; init_db(); seed_initial_data()"
```

---

#### `.env`
**Purpose**: Environment configuration (you need to create this)

**Contents**:
```bash
# Generation Backend
GENERATION_BACKEND=auto

# Local Model (optional)
LLAMA_MODEL_PATH=/path/to/model.gguf

# Mercury API (fallback)
INCEPTION_API_KEY=your_api_key_here

# JWT Configuration
JWT_SECRET_KEY=generate-random-key-here

# Server
PORT=8000
```

**Security**: Never commit this file to Git (already in .gitignore)

---

#### `requirements.txt`
**Purpose**: Python package dependencies

**Key packages**:
- `fastapi`: Web framework
- `uvicorn`: ASGI server
- `sqlalchemy`: ORM for database
- `pydantic`: Data validation
- `python-jose[cryptography]`: JWT handling
- `pytest`: Testing framework
- `llama-cpp-python`: Local LLM support
- `requests`: HTTP client for Mercury API

**When to update**:
```bash
pip freeze > requirements.txt
```

---

#### `pytest.ini`
**Purpose**: Pytest configuration

**What it configures**:
- Test discovery paths
- Default command-line options
- Test markers
- Warning filters

**Contents**:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
addopts = -v --tb=short --disable-warnings
```

---

### API Layer (`api/`)

#### `api/__init__.py`
**Purpose**: Makes `api/` a Python package

**Contents**: Empty (just makes the directory importable)

---

#### `api/auth.py`
**Purpose**: Authentication endpoints

**Endpoints**:
- `POST /api/auth/login` - User login, returns JWT token
- `GET /api/auth/me` - Get current user info from token

**Key functions**:
```python
def create_access_token(data: dict) -> str:
    # Creates JWT token with 24-hour expiration

def decode_access_token(token: str) -> dict:
    # Validates and decodes JWT token

async def get_current_user(credentials) -> dict:
    # Dependency for protected endpoints
```

**JWT Format**:
```json
{
  "sub": "user@company.com",
  "company": "Company Name",
  "role": "user",
  "exp": 1234567890
}
```

**When to modify**: Changing token expiration, adding new auth methods, implementing OAuth

---

#### `api/rag.py`
**Purpose**: RAG (Retrieval-Augmented Generation) query endpoints

**Endpoints**:
- `POST /api/rag/query` - Submit question, get AI-generated answer

**What it does**:
1. Validates user authentication
2. Extracts user's company from JWT token
3. Calls RAG pipeline with company filter
4. Filters results to ensure company data isolation
5. Formats response with answer and source citations

**Request example**:
```json
{
  "query": "What is the PTO policy?",
  "top_k": 3
}
```

**Response example**:
```json
{
  "answer": "Your PTO policy allows...",
  "sources": [...],
  "query": "What is the PTO policy?",
  "company": "Crouse Medical Practice"
}
```

**When to modify**: Changing RAG pipeline behavior, adding query analytics, implementing caching

---

#### `api/admin.py`
**Purpose**: Admin management endpoints

**Super Admin Endpoints** (manage all companies):
- `GET /api/admin/company-admins` - List all company admins
- `GET /api/admin/all-companies` - List all companies
- `POST /api/admin/add-company-admin` - Create new company admin
- `DELETE /api/admin/delete-company-admin` - Remove company admin

**Company Admin Endpoints** (manage their company):
- `GET /api/admin/company-users` - List users in admin's company
- `POST /api/admin/add-user` - Add user to company
- `DELETE /api/admin/delete-user` - Remove user from company
- `PUT /api/admin/update-password` - Change user password

**Key function**:
```python
def require_admin(current_user: dict, required_role: str):
    # Validates user has required admin role
    # Raises 403 if insufficient permissions
```

**When to modify**: Adding new admin features, implementing audit logs, adding bulk operations

---

### Database Layer (`db/`)

#### `db/__init__.py`
**Purpose**: Exports database components for easy importing

**Exports**:
```python
from db.connection import engine, SessionLocal, Base, get_db, init_db
from db.models import User, Company, UserRole, PTOBalance, PTORequest, ...
```

**Usage in other files**:
```python
from db import User, get_db, init_db
```

---

#### `db/connection.py`
**Purpose**: Database connection and session management

**Key components**:
```python
# Database URL
DATABASE_URL = "sqlite:///./users.db"

# SQLAlchemy engine
engine = create_engine(DATABASE_URL, ...)

# Session factory
SessionLocal = sessionmaker(bind=engine)

# Base class for models
Base = declarative_base()

# Dependency for FastAPI endpoints
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Initialize all tables
def init_db():
    Base.metadata.create_all(bind=engine)
```

**When to modify**: Switching to PostgreSQL, adding connection pooling, implementing read replicas

---

#### `db/models.py`
**Purpose**: SQLAlchemy ORM models (database schema)

**Models defined**:

**1. UserRole (Enum)**
```python
class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    COMPANY_ADMIN = "company_admin"
    USER = "user"
```

**2. User**
```python
class User(Base):
    email: str (primary key)
    password: str
    name: str
    role: UserRole
    company: str
    created_at: datetime
    updated_at: datetime
```

**3. Company**
```python
class Company(Base):
    name: str (primary key)
    domain: str  # Industry
    email_domain: str (unique)
    url: str  # Handbook URL
    created_at: datetime
```

**4. PTOBalance** (for future PTO agent)
```python
class PTOBalance(Base):
    id: int (auto-increment)
    email: str
    company: str
    year: int
    total_days: float
    used_days: float
    pending_days: float
    remaining_days: computed property
```

**5. PTORequest** (for future PTO agent)
```python
class PTORequest(Base):
    id: str (UUID)
    email: str
    company: str
    start_date: date
    end_date: date
    days_requested: float
    reason: str
    status: PTOStatus (enum)
    admin_notes: str
    approved_by: str
    reviewed_at: datetime
```

**6. CompanyHoliday** (for future PTO agent)
**7. CompanyBlackoutDate** (for future PTO agent)

**When to modify**: Adding new tables, changing relationships, adding indexes

---

#### `db/seed.py`
**Purpose**: Populate database with initial data

**What it seeds**:
- 19 companies across different industries
- 1 super admin account
- 19 company admin accounts (one per company)
- 2 sample user accounts

**Key function**:
```python
def seed_initial_data(db_session=None):
    # Check if already seeded
    # Add all companies
    # Add super admin
    # Add company admins
    # Add sample users
```

**Seeded accounts**:
```python
# Super Admin
email: "admin@group9.com"
password: "admin123"

# Company Admins
email: "admin@{company-domain}.com"
password: "admin123"

# Sample Users
email: "user@crousemedical.com"
password: "password123"
```

**When to modify**: Adding new companies, changing default passwords, adding sample PTO data

---

### Schema Layer (`schemas/`)

#### `schemas/__init__.py`
**Purpose**: Exports all Pydantic schemas

**Exports**:
```python
from schemas.auth import LoginRequest, LoginResponse, UserInfo, ...
from schemas.rag import RAGQueryRequest, RAGQueryResponse
```

---

#### `schemas/auth.py`
**Purpose**: Pydantic models for authentication

**Models**:

**1. LoginRequest**
```python
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
```

**2. LoginResponse**
```python
class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    company: Optional[str]
    email: str
    role: str
```

**3. UserInfo**
```python
class UserInfo(BaseModel):
    email: str
    company: Optional[str]
    role: str
```

**4. CreateUserRequest, UpdatePasswordRequest, DeleteUserRequest**

**Why Pydantic**: Automatic validation, serialization, documentation generation

**When to modify**: Adding new fields, changing validation rules, adding custom validators

---

#### `schemas/rag.py`
**Purpose**: Pydantic models for RAG queries

**Models**:

**1. RAGQueryRequest**
```python
class RAGQueryRequest(BaseModel):
    query: str
    top_k: int = 5  # Default value
```

**2. RAGQueryResponse**
```python
class RAGQueryResponse(BaseModel):
    answer: str
    sources: List[Dict]
    query: str
    company: str
```

**When to modify**: Adding query parameters, changing response format, adding metadata

---

### Service Layer (`services/`)

#### `services/__init__.py`
**Purpose**: Exports service functions

**Exports**:
```python
from services.auth_service import validate_credentials, add_user, delete_user, ...
from services.rag_service import normalize_metadata_company_name
```

---

#### `services/auth_service.py`
**Purpose**: Business logic for authentication and user management

**Key functions**:

**1. validate_credentials(email, password, db) → (bool, company, role)**
- Checks if email/password combination is valid
- Returns user's company and role if valid

**2. get_company_from_email(email, db) → company**
- Looks up user's company by email

**3. get_all_companies(db) → List[Dict]**
- Returns all registered companies

**4. add_user(email, password, company, name, role, db) → (success, message)**
- Creates new user account
- Validates uniqueness and role

**5. delete_user(email, db) → (success, message)**
- Removes user account
- Prevents deleting super admin

**6. update_user_password(email, new_password, db) → (success, message)**
- Changes user password

**Design pattern**: All functions accept optional `db` parameter for testing flexibility

**When to modify**: Adding password hashing, implementing user roles, adding audit logging

---

#### `services/rag_service.py`
**Purpose**: Utility functions for RAG pipeline

**Key function**:

**normalize_metadata_company_name(metadata_company, user_company) → bool**
- Handles mismatch between vector DB metadata and database company names
- Returns True if companies match (case-insensitive, flexible matching)

**Why needed**: Vector DB stores company names with industry prefixes like "Healthcare Crouse Medical Practice", while database stores just "Crouse Medical Practice"

**Mapping dictionary**:
```python
METADATA_TO_DB_COMPANY_MAP = {
    "healthcare crouse medical practice": "Crouse Medical Practice",
    "retail lunds & byerlys": "Lunds & Byerlys",
    ...
}
```

**When to modify**: Adding new companies, changing company name format, implementing fuzzy matching

---

### Test Suite (`tests/`)

#### `tests/conftest.py`
**Purpose**: Shared pytest fixtures and configuration

**Key fixtures**:

**1. test_engine**
- Creates in-memory SQLite database for testing
- Ensures tests don't affect production database

**2. test_db**
- Provides database session for tests
- Automatically rolls back after each test

**3. client**
- TestClient instance for making API requests
- Overrides `get_db` to use test database

**4. auth_headers, admin_headers, super_admin_headers**
- Pre-authenticated headers for testing protected endpoints

**Why needed**: Isolated testing environment, faster tests, no database cleanup needed

---

#### `tests/test_api/`
**Purpose**: Test API endpoints

**Files**:
- `test_auth.py` - Authentication endpoint tests
- `test_admin.py` - Admin endpoint tests
- `test_rag.py` - RAG query endpoint tests

**Example test**:
```python
def test_login_success(client, test_db):
    # Seed database
    seed_initial_data(test_db)
    
    # Make request
    response = client.post("/api/auth/login", json={...})
    
    # Assert response
    assert response.status_code == 200
    assert "access_token" in response.json()
```

---

#### `tests/test_db/`
**Purpose**: Test database layer

**Files**:
- `test_connection.py` - Database connection tests
- `test_models.py` - ORM model tests
- `test_seed.py` - Seeding function tests

---

#### `tests/test_services/`
**Purpose**: Test business logic

**Files**:
- `test_auth_service.py` - Authentication service tests
- `test_rag_service.py` - RAG service tests

---

#### `tests/test_schemas/`
**Purpose**: Test Pydantic validation

**File**: `test_schemas.py`

**Example**:
```python
def test_login_request_invalid_email():
    with pytest.raises(ValidationError):
        LoginRequest(email="invalid", password="pass")
```

---

## 🧪 Testing

### Run All Tests
```bash
cd ~/Documents/Projects/FrontShiftAI/backend
pytest
```

### Run Specific Test File
```bash
pytest tests/test_api/test_auth.py
```

### Run with Coverage
```bash
pytest --cov=. --cov-report=html
```

### Test Results
- **38 tests total**
- **Pass rate**: ~90%
- **Coverage**: Database, API, Services, Schemas

---

## 🔧 Development Workflow

### 1. Start Development Server
```bash
cd ~/Documents/Projects/FrontShiftAI/backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Make Changes
Edit files in `api/`, `db/`, `schemas/`, or `services/`

### 3. Test Changes
```bash
pytest  # Run all tests
# or
pytest tests/test_api/test_auth.py::test_login_success  # Specific test
```

### 4. Check API Docs
Visit http://localhost:8000/docs

### 5. Manual Testing
```bash
# Test login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@crousemedical.com","password":"password123"}'
```

---

## 📊 Database Management

### View Database
```bash
sqlite3 users.db
sqlite> .tables
sqlite> .schema users
sqlite> SELECT * FROM users;
```

### Reset Database
```bash
rm users.db
python -c "from db import init_db; from db.seed import seed_initial_data; init_db(); seed_initial_data()"
```

### Add New Company
```python
from db import SessionLocal, Company
db = SessionLocal()
company = Company(
    name="New Company",
    domain="Industry",
    email_domain="newcompany.com",
    url="https://..."
)
db.add(company)
db.commit()
```

---

## 🚀 Deployment Commands

### Production Start
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### With Gunicorn
```bash
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

---

## 📝 Environment Variables
```bash
# Required
GENERATION_BACKEND=auto
INCEPTION_API_KEY=your_api_key

# Optional
JWT_SECRET_KEY=your_secret
LLAMA_MODEL_PATH=/path/to/model.gguf
PORT=8000
```

---

## 🆘 Troubleshooting

### Server won't start
```bash
# Check port availability
lsof -i :8000

# Kill existing process
kill -9 $(lsof -t -i:8000)
```

### Database errors
```bash
# Reset database
rm users.db
python -c "from db import init_db; init_db()"
```

### Import errors
```bash
# Reinstall dependencies
pip install -r requirements.txt
```

---

## 📚 Additional Resources

- **API Docs**: http://localhost:8000/docs
- **FastAPI**: https://fastapi.tiangolo.com
- **SQLAlchemy**: https://docs.sqlalchemy.org
- **Pytest**: https://docs.pytest.org

---
**Last Updated**: November 19, 2025  
