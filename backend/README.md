# FrontShiftAI Backend

Multi-tenant RAG (Retrieval-Augmented Generation) system providing AI-powered access to company handbook information across 19+ organizations, enhanced with intelligent AI agents for automated workflows.

## Quick Start
```bash
# Navigate to backend
cd backend

# Activate virtual environment
source venv/bin/activate  # Mac/Linux
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Start the server
python main.py
```

Access API documentation: http://localhost:8000/docs

## Project Structure
```
backend/
├── agents/                  # AI Agents Layer
│   ├── pto/                # PTO Request Agent
│   │   ├── agent.py        # LangGraph workflow
│   │   ├── nodes.py        # Workflow nodes
│   │   ├── state.py        # State definition
│   │   └── tools.py        # Utility functions
│   ├── utils/              # Shared utilities
│   │   ├── llm_client.py   # LLM client with fallback
│   │   └── llm_config.py   # Provider configuration
│   └── tests/              # Agent tests
│       ├── conftest.py
│       ├── test_pto_tools.py
│       └── test_pto_nodes.py
│
├── api/                     # API Endpoints
│   ├── admin.py            # Admin management
│   ├── auth.py             # Authentication
│   ├── rag.py              # RAG queries
│   └── pto_agent.py        # PTO agent endpoints
│
├── db/                      # Database Layer
│   ├── connection.py       # SQLAlchemy setup
│   ├── models.py           # ORM models
│   └── seed.py             # Initial data
│
├── schemas/                 # Data Validation
│   ├── auth.py             # Auth schemas
│   ├── rag.py              # RAG schemas
│   └── pto.py              # PTO schemas
│
├── services/                # Business Logic
│   ├── auth_service.py     # Auth operations
│   └── rag_service.py      # RAG utilities
│
├── tests/                   # Test Suite
│   ├── test_api/
│   ├── test_db/
│   ├── test_schemas/
│   └── test_services/
│
├── .github/                 # CI/CD
│   └── workflows/
│       ├── backend.yml     # Backend tests
│       ├── frontend.yml    # Frontend build
│       ├── agents.yml      # Agent tests
│       └── config.yml      # Config validation
│
├── .env                     # Environment variables
├── main.py                 # Application entry
├── requirements.txt        # Dependencies
└── users.db                # SQLite database
```

## AI Agents System

### LangGraph Workflow Engine

FrontShiftAI uses LangGraph to build stateful, multi-step AI workflows as directed graphs.

**Key Benefits:**
- **State Management**: Automatic state propagation between steps
- **Conditional Routing**: Smart decision-making based on conditions
- **Error Recovery**: Built-in retry and fallback mechanisms
- **Testability**: Each node is independently testable
- **Visualization**: Clear graph representation

**Traditional Approach** (Without LangGraph):
```python
def process_pto_request(message):
    parsed = parse_request(message)
    if not parsed.valid:
        return error_response()
    
    validated = validate_dates(parsed)
    if not validated.ok:
        return validation_error()
    
    balance = check_balance(validated)
    if not balance.sufficient:
        return insufficient_balance_error()
    # ... deep nesting continues
```

**LangGraph Approach**:
```python
workflow = StateGraph(PTOAgentState)
workflow.add_node("parse", parse_node)
workflow.add_node("validate", validate_node)
workflow.add_node("check_balance", balance_node)

workflow.add_conditional_edges(
    "validate",
    router,
    {"continue": "check_balance", "failed": "error_response"}
)
```

### PTO Request Agent

Automates paid time off request workflow: parsing natural language, validating dates, checking balances, creating requests, and routing to administrators.

**Workflow:**
```
START
  ↓
Parse Intent (LLM extracts dates, reason)
  ↓
Validate Dates (holidays, blackouts, weekends)
  ↓ (valid/invalid)
Check Balance (sufficient days available?)
  ↓ (yes/no)
Check Conflicts (overlapping requests?)
  ↓ (none/found)
Create Request (save to database)
  ↓
Notify Admin (send notification)
  ↓
Generate Response (user confirmation)
  ↓
END
```

**State Definition:**
```python
class PTOAgentState(TypedDict):
    # Input
    user_email: str
    company: str
    user_message: str
    
    # Parsed data
    start_date: Optional[date]
    end_date: Optional[date]
    intent: str
    
    # Validation
    is_valid: bool
    validation_errors: List[str]
    total_business_days: float
    
    # Balance check
    remaining_days: float
    has_sufficient_balance: bool
    
    # Conflicts
    has_conflicts: bool
    conflicting_requests: List[dict]
    
    # Output
    request_id: Optional[str]
    agent_response: str
```

**Graph Implementation:**
```python
class PTOAgent:
    def _build_graph(self):
        workflow = StateGraph(PTOAgentState)
        
        # Add nodes
        workflow.add_node("parse_intent", parse_intent_node)
        workflow.add_node("validate_dates", validate_dates_node)
        workflow.add_node("check_balance", check_balance_node)
        workflow.add_node("check_conflicts", check_conflicts_node)
        workflow.add_node("create_request", create_request_node)
        workflow.add_node("generate_response", generate_response_node)
        
        # Define flow
        workflow.set_entry_point("parse_intent")
        workflow.add_conditional_edges("validate_dates", router, {...})
        workflow.add_edge("create_request", "generate_response")
        workflow.add_edge("generate_response", END)
        
        return workflow.compile()
```

**Node Example:**
```python
def validate_dates_node(state: PTOAgentState, db: Session) -> PTOAgentState:
    """
    Validates dates against:
    - Past dates (reject)
    - Company holidays (exclude)
    - Blackout periods (reject)
    - Weekend-only requests (reject)
    """
    if state["start_date"] < date.today():
        state["validation_errors"].append("Cannot request PTO for past dates")
        state["is_valid"] = False
        return state
    
    holidays = get_company_holidays(db, state["company"], state["start_date"].year)
    business_days = calculate_business_days(
        state["start_date"], 
        state["end_date"], 
        holidays
    )
    
    state["total_business_days"] = business_days
    state["is_valid"] = True
    return state
```

### LLM Integration

**Provider Configuration:**
```python
# Primary provider (code-based switching)
USE_LLM = "groq"  # Options: "groq", "local", "mercury"

# Automatic fallback
ENABLE_FALLBACK = True
FALLBACK_CHAIN = ["groq", "local", "mercury"]

# Provider settings
GROQ_CONFIG = {
    "model": "llama-3.1-8b-instant",
    "temperature": 0.7,
}

LOCAL_CONFIG = {
    "url": "http://localhost:11434",  # Ollama
    "model": "llama3:3b",
}
```

**Client with Fallback:**
```python
class AgentLLMClient:
    def chat(self, messages, json_mode=False):
        # Try primary provider
        response = self._try_provider(self.primary_provider, messages)
        if response:
            return response
        
        # Automatic fallback
        if self.enable_fallback:
            for provider in self.fallback_chain:
                response = self._try_provider(provider, messages)
                if response:
                    return response
        
        raise Exception("All LLM providers failed")
```

**Natural Language Processing:**
```python
async def parse_user_intent(user_message: str) -> Dict:
    """
    Input: "I need leave from December 25 to December 27"
    Output: {
        "intent": "request_pto",
        "start_date": "2025-12-25",
        "end_date": "2025-12-27"
    }
    """
    llm_client = get_llm_client()
    
    messages = [
        {"role": "system", "content": "Extract PTO request details..."},
        {"role": "user", "content": user_message}
    ]
    
    response = llm_client.chat(messages, json_mode=True, temperature=0.3)
    return json.loads(response)
```

## Database Schema

### User Management
```python
class User(Base):
    email = Column(String, primary_key=True)
    password = Column(String)
    name = Column(String)
    role = Column(Enum(UserRole))  # super_admin, company_admin, user
    company = Column(String, nullable=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

class Company(Base):
    name = Column(String, primary_key=True)
    domain = Column(String)  # Industry
    email_domain = Column(String, unique=True)
    url = Column(String)  # Handbook URL
```

### PTO System
```python
class PTOBalance(Base):
    id = Column(Integer, primary_key=True)
    email = Column(String, index=True)
    company = Column(String)
    year = Column(Integer, default=2025)
    
    total_days = Column(Float, default=15.0)
    used_days = Column(Float, default=0.0)
    pending_days = Column(Float, default=0.0)
    
    @property
    def remaining_days(self):
        return self.total_days - self.used_days - self.pending_days

class PTORequest(Base):
    id = Column(String, primary_key=True)  # UUID
    email = Column(String, index=True)
    company = Column(String)
    
    start_date = Column(Date)
    end_date = Column(Date)
    days_requested = Column(Float)
    reason = Column(String)
    
    status = Column(Enum(PTOStatus))  # pending, approved, denied
    admin_notes = Column(String)
    approved_by = Column(String)
    reviewed_at = Column(DateTime)

class CompanyHoliday(Base):
    id = Column(String, primary_key=True)
    company = Column(String)
    holiday_name = Column(String)
    holiday_date = Column(Date)
    is_recurring = Column(Boolean)

class CompanyBlackoutDate(Base):
    id = Column(String, primary_key=True)
    company = Column(String)
    period_name = Column(String)
    start_date = Column(Date)
    end_date = Column(Date)
    reason = Column(String)
```

## API Endpoints

### Authentication
```
POST /api/auth/login
  Request: {"email": "user@company.com", "password": "password"}
  Response: {"access_token": "jwt_token", "role": "user", ...}

GET /api/auth/me
  Response: {"email": "user@company.com", "company": "...", "role": "user"}
```

### RAG Queries
```
POST /api/rag/query
  Request: {"query": "What is the PTO policy?", "top_k": 3}
  Response: {"answer": "...", "sources": [...], "company": "..."}
```

### PTO Agent (User)
```
POST /api/pto/chat
  Request: {"message": "I need leave from Dec 25-27"}
  Response: {
    "response": "PTO Request Submitted...",
    "request_created": true,
    "request_id": "uuid",
    "balance_info": {...}
  }

GET /api/pto/balance
  Response: {
    "total_days": 15.0,
    "used_days": 0.0,
    "pending_days": 2.0,
    "remaining_days": 13.0
  }

GET /api/pto/requests
  Response: [{"id": "...", "start_date": "...", "status": "pending", ...}]
```

### PTO Agent (Admin)
```
GET /api/pto/admin/requests?status_filter=pending
  Response: [{"id": "...", "email": "...", "status": "pending", ...}]

POST /api/pto/admin/approve
  Request: {
    "request_id": "uuid",
    "status": "approved",
    "admin_notes": "Approved"
  }

GET /api/pto/admin/balances
  Response: [{"email": "...", "total_days": 15, "remaining_days": 13, ...}]

PUT /api/pto/admin/balance/{email}?total_days=20
  Response: {"message": "Balance updated"}

POST /api/pto/admin/reset-balance/{email}
  Response: {"message": "Balance reset", "available_now": 15.0}

POST /api/pto/admin/reset-all-balances
  Response: {"message": "Reset 10 employees", "employees_reset": 10}

DELETE /api/pto/admin/balance/{email}
  Response: {"message": "Balance deleted"}
```

### Admin Management
```
GET /api/admin/company-users
  Response: {"users": [...]}

POST /api/admin/add-user
  Request: {"email": "...", "password": "...", "name": "..."}

DELETE /api/admin/delete-user
  Request: {"email": "..."}

PUT /api/admin/update-password
  Request: {"email": "...", "new_password": "..."}
```

## Continuous Integration

### GitHub Actions Workflows

**Backend CI** (`.github/workflows/backend.yml`):
- Triggers: Push/PR to any branch with backend changes
- Tests: Database, API, Services, Schemas
- Coverage: XML and HTML reports uploaded
- Artifacts: Coverage reports (7-day retention)

**Frontend CI** (`.github/workflows/frontend.yml`):
- Triggers: Push/PR to any branch with frontend changes
- Build: Production bundle with npm
- Artifacts: Build output (7-day retention)

**Agent Tests** (`.github/workflows/agents.yml`):
- Triggers: Push/PR to any branch with agent changes
- Tests: PTO Tools, Nodes, State, Workflow
- Coverage: Agent-specific reports
- Future: Placeholder for additional agents

**Config Validation** (`.github/workflows/config.yml`):
- Triggers: Push/PR to any branch with config changes
- Validates: LLM config, database models, API endpoints
- Checks: Environment secrets, configuration integrity

**Features:**
- Automatic testing on every push
- Manual workflow dispatch available
- Parallel execution for faster feedback
- Comprehensive coverage reporting
- Branch-specific artifact naming

**Running Manually:**
1. Navigate to repository → Actions tab
2. Select workflow
3. Click "Run workflow"
4. Choose branch and execute

## Testing

### Run Tests
```bash
# All tests
pytest

# Backend tests only
pytest tests/

# Agent tests only
pytest agents/tests/

# Specific test file
pytest tests/test_api/test_auth.py

# With coverage
pytest --cov=. --cov-report=html --cov-report=term
```

### Test Structure
```python
# conftest.py - Fixtures
@pytest.fixture
def db_session():
    """In-memory test database"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    yield session

@pytest.fixture
def sample_pto_balance(db_session):
    """Sample PTO balance for testing"""
    balance = PTOBalance(...)
    db_session.add(balance)
    db_session.commit()
    return balance
```
```python
# test_pto_tools.py
def test_calculate_business_days_with_holidays():
    start = date(2025, 12, 24)
    end = date(2025, 12, 26)
    holidays = [date(2025, 12, 25)]
    
    result = calculate_business_days(start, end, holidays)
    assert result == 2.0  # Wed and Fri only

def test_check_conflicting_requests(db_session):
    # Create existing request
    existing = PTORequest(...)
    db_session.add(existing)
    
    # Check for conflicts
    has_conflicts, conflicts = check_conflicting_requests(...)
    assert has_conflicts is True
```
```python
# test_pto_nodes.py
def test_validate_dates_past_dates(db_session):
    state = PTOAgentState(
        start_date=date(2020, 1, 1),
        is_valid=False,
        ...
    )
    
    result = validate_dates_node(state, db_session)
    assert result['is_valid'] is False
    assert "past dates" in result['validation_errors'][0]
```

## Development Workflow

### Setup
```bash
# Clone and setup
cd backend
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cat > .env << EOF
GROQ_API_KEY=your_key
JWT_SECRET_KEY=secure_random_key
GENERATION_BACKEND=auto
EOF

# Initialize database
python -c "from db import init_db; from db.seed import seed_initial_data; init_db(); seed_initial_data()"

# Start server
python main.py
```

### Development Cycle

1. Make changes in relevant layer
2. Run tests: `pytest`
3. Test via API docs: http://localhost:8000/docs
4. Commit and push (CI/CD validates automatically)

### Database Management
```bash
# Inspect database
sqlite3 users.db
> .tables
> SELECT * FROM users;
> SELECT * FROM pto_requests WHERE status = 'pending';

# Reset database
rm users.db
python -c "from db import init_db; from db.seed import seed_initial_data; init_db(); seed_initial_data()"

# Backup
cp users.db users_backup_$(date +%Y%m%d).db
```

## Production Deployment

### Server Configuration
```bash
# Standard
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# With Gunicorn (recommended)
gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120
```

### Environment Variables
```bash
# LLM Configuration
GROQ_API_KEY=your_groq_key
LLAMA_MODEL_PATH=/path/to/model  # Optional
INCEPTION_API_KEY=your_mercury_key

# Security
JWT_SECRET_KEY=secure_random_key
CORS_ORIGINS=https://yourdomain.com

# Database
DATABASE_URL=sqlite:///./users.db

# Server
PORT=8000
WORKERS=4
LOG_LEVEL=info
```

### Production Checklist

**Security:**
- Change default passwords
- Implement password hashing
- Configure HTTPS/TLS
- Set secure JWT secret
- Enable CORS for trusted origins only
- Implement rate limiting

**Database:**
- Migrate to PostgreSQL
- Configure connection pooling
- Set up automated backups
- Implement migration tool (Alembic)
- Add database indexes

**Monitoring:**
- Configure application logging
- Set up error tracking
- Implement health check monitoring
- Configure performance metrics
- Set up alerting

**Infrastructure:**
- Configure reverse proxy
- Set up load balancing
- Implement container orchestration
- Configure auto-scaling
- Set up deployment pipeline

## Troubleshooting

### Server Issues
```bash
# Port already in use
lsof -i :8000
kill -9 $(lsof -t -i:8000)

# Database errors
rm users.db
python -c "from db import init_db; init_db()"

# Import errors
pip install -r requirements.txt --force-reinstall
```

### Common Problems

**Authentication Failures:**
- Verify JWT_SECRET_KEY consistency
- Check token expiration
- Validate user credentials

**Agent Failures:**
- Check LLM provider availability
- Verify API keys in environment
- Review agent workflow logs

**Database Issues:**
- Verify database file exists
- Check file permissions
- Reset database if corrupted

## Future Agents

The architecture supports multiple agents:
```
agents/
├── pto/              # Implemented
├── expense/          # Planned: Expense Report Agent
├── scheduling/       # Planned: Scheduling Agent
└── utils/            # Shared utilities
```

Each agent follows the same pattern:
1. Define state structure
2. Implement processing nodes
3. Create utility functions
4. Build LangGraph workflow
5. Add API endpoints
6. Write comprehensive tests

## Resources

- **API Docs**: http://localhost:8000/docs
- **FastAPI**: https://fastapi.tiangolo.com
- **SQLAlchemy**: https://docs.sqlalchemy.org
- **LangGraph**: https://langchain-ai.github.io/langgraph
- **Pytest**: https://docs.pytest.org

## Default Credentials
```
Super Admin:
  Email: admin@group9.com
  Password: admin123

Company Admin:
  Email: admin@crousemedical.com
  Password: admin123

User:
  Email: user@crousemedical.com
  Password: password123
```

---

**Last Updated**: November 20, 2025  
**Version**: 2.0.0