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
│   ├── hr_ticket/          # HR Ticket Agent
│   │   ├── agent.py        # LangGraph workflow
│   │   ├── nodes.py        # Workflow nodes
│   │   ├── state.py        # State definition
│   │   └── tools.py        # Utility functions
│   ├── utils/              # Shared utilities
│   │   ├── llm_client.py   # LLM client with fallback
│   │   └── llm_config.py   # Provider configuration
│   └── test_agents/        # Agent tests
│       ├── conftest.py
│       ├── test_pto_tools.py
│       ├── test_pto_nodes.py
│       ├── test_hr_ticket_tools.py
│       └── test_hr_ticket_nodes.py
│
├── api/                     # API Endpoints
│   ├── admin.py            # Admin management
│   ├── auth.py             # Authentication
│   ├── rag.py              # RAG queries
│   ├── pto_agent.py        # PTO agent endpoints
│   ├── hr_ticket_agent.py  # HR ticket endpoints
│   └── unified_agent.py    # Unified chat router
│
├── db/                      # Database Layer
│   ├── connection.py       # SQLAlchemy setup
│   ├── models.py           # ORM models
│   └── seed.py             # Initial data
│
├── schemas/                 # Data Validation
│   ├── auth.py             # Auth schemas
│   ├── rag.py              # RAG schemas
│   ├── pto.py              # PTO schemas
│   └── hr_ticket.py        # HR ticket schemas
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

## Unified Agent Router

### Overview

The unified agent router provides a single endpoint that intelligently routes user messages to the appropriate agent (RAG, PTO, or HR Ticket) based on intent detection. This enables seamless conversational experiences where users can naturally switch between querying handbooks, requesting time off, and creating support tickets within the same chat session.

### Architecture

**Intent Detection Flow:**
```
User Message
    ↓
LLM Intent Classification
    ↓
├─→ RAG Agent (handbook queries)
├─→ PTO Agent (time off requests)
└─→ HR Ticket Agent (support requests)
    ↓
Unified Response
```

### Implementation

**Endpoint:**
```
POST /api/chat/message
Request: {"message": "What is the PTO policy?"}
Response: {
  "response": "According to the handbook...",
  "agent_used": "rag",
  "sources": [...]
}
```

**Intent Detection Logic:**
```python
def detect_intent(message: str) -> dict:
    """
    Uses LLM to classify user intent into three categories:
    - rag: Queries about company policies, procedures, benefits
    - pto: Requests for time off, PTO balance checks
    - hr_ticket: Support requests, meeting scheduling, complaints
    
    Fallback mechanism:
    1. LLM classification (primary)
    2. Keyword matching (fallback)
    3. Default to RAG (safest)
    """
    
    # Primary: LLM classification
    llm_result = classify_with_llm(message)
    if llm_result['confidence'] > 0.7:
        return llm_result
    
    # Fallback: Keyword matching
    pto_keywords = ['pto', 'leave', 'vacation', 'time off', 'days off']
    hr_keywords = ['hr', 'ticket', 'meeting', 'discuss', 'complaint']
    
    if any(keyword in message.lower() for keyword in pto_keywords):
        return {'intent': 'pto', 'confidence': 0.8}
    elif any(keyword in message.lower() for keyword in hr_keywords):
        return {'intent': 'hr_ticket', 'confidence': 0.8}
    
    # Default: RAG
    return {'intent': 'rag', 'confidence': 0.6}
```

**Router Implementation:**
```python
@router.post("/message", response_model=ChatResponse)
async def unified_chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Routes messages to appropriate agent based on intent.
    Maintains conversation context across agent boundaries.
    """
    intent_data = detect_intent(request.message)
    
    if intent_data['intent'] == 'pto':
        pto_agent = get_pto_agent()
        result = pto_agent.process(
            user_email=current_user['email'],
            company=current_user['company'],
            user_message=request.message,
            db=db
        )
        return ChatResponse(
            response=result['agent_response'],
            agent_used='pto',
            metadata={'request_id': result.get('request_id')}
        )
    
    elif intent_data['intent'] == 'hr_ticket':
        hr_agent = get_hr_ticket_agent()
        result = hr_agent.process(
            user_email=current_user['email'],
            company=current_user['company'],
            user_message=request.message,
            db=db
        )
        return ChatResponse(
            response=result['agent_response'],
            agent_used='hr_ticket',
            metadata={'ticket_id': result.get('ticket_id')}
        )
    
    else:  # Default to RAG
        rag_result = await rag_query(
            RAGQueryRequest(query=request.message),
            current_user
        )
        return ChatResponse(
            response=rag_result.answer,
            agent_used='rag',
            metadata={'sources': rag_result.sources}
        )
```

### Conversation Examples

**Multi-Agent Conversation:**
```
User: "What is the remote work policy?"
System: [RAG Agent] According to the handbook, employees may work remotely...

User: "I need 3 days off next week"
System: [PTO Agent] PTO request created for Dec 24-26. Your request is pending approval...

User: "Also, can I schedule a meeting with HR about benefits?"
System: [HR Ticket Agent] Support ticket created. You are #5 in queue...

User: "What documents do I need for the benefits meeting?"
System: [RAG Agent] For benefits enrollment, you will need...
```

### Benefits

1. **Single Entry Point**: Users interact with one endpoint regardless of request type
2. **Seamless Context Switching**: Natural conversation flow across different agent domains
3. **Intelligent Routing**: LLM-based classification with keyword fallback
4. **Unified Response Format**: Consistent response structure across all agents
5. **Metadata Preservation**: Agent-specific data (request IDs, ticket numbers) included in responses

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

### HR Ticket Agent

Automates HR support requests and meeting scheduling: parsing employee inquiries, categorizing tickets, managing queue, and facilitating admin-employee communication.

**Workflow:**
```
START
  ↓
Parse Intent (LLM extracts subject, category, meeting preferences)
  ↓
Validate Request (check required fields, validate dates)
  ↓ (valid/invalid)
Check Duplicates (existing open tickets?)
  ↓ (informational only)
Create Ticket (save to database, assign queue position)
  ↓
Generate Response (user confirmation with ticket details)
  ↓
END
```

**State Definition:**
```python
class HRTicketState(TypedDict):
    # Input
    user_email: str
    company: str
    user_message: str
    
    # Parsed data
    intent: str
    subject: Optional[str]
    description: Optional[str]
    category: Optional[str]  # benefits, payroll, workplace_issue, etc.
    meeting_type: Optional[str]  # in_person, online, phone, no_meeting
    preferred_date: Optional[date]
    preferred_time_slot: Optional[str]  # morning, afternoon, evening
    urgency: str  # normal, urgent
    
    # Validation
    is_valid: bool
    validation_errors: List[str]
    
    # Duplicate check
    has_open_tickets: bool
    open_ticket_ids: List[str]
    
    # Output
    ticket_id: Optional[str]
    queue_position: Optional[int]
    agent_response: str
```

**Features:**
- **Smart Categorization**: Automatically categorizes requests (benefits, payroll, workplace issues, etc.)
- **Queue Management**: Assigns position based on pending tickets
- **Meeting Coordination**: Captures preferred dates/times for HR meetings
- **Admin Dashboard**: Queue view with filtering and sorting
- **Meeting Scheduling**: Admin can schedule meetings with links/locations
- **Ticket Lifecycle**: Pending → In Progress → Scheduled → Resolved/Closed
- **Admin Notes System**: Admins can add notes visible to users for transparency

**Example User Interactions:**
```python
# Benefits inquiry
"I need to discuss my health insurance options"
→ Category: benefits, Meeting: online

# Urgent payroll issue
"URGENT: There's a problem with my paycheck"
→ Category: payroll, Urgency: urgent

# Policy question
"What's the remote work policy?"
→ Category: policy_question, Meeting: no_meeting_needed

# Workplace concern
"I'd like to meet in person to discuss a workplace issue"
→ Category: workplace_issue, Meeting: in_person
```

**Admin Workflow:**
1. View ticket queue (filter by status, category, urgency)
2. Pick up ticket (assigns to admin, status: in_progress)
3. Add notes (visible to user for communication)
4. Schedule meeting (if needed, status: scheduled)
5. Resolve/Close ticket (status: resolved/closed)

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
    PTO Example:
    Input: "I need leave from December 25 to December 27"
    Output: {
        "intent": "request_pto",
        "start_date": "2025-12-25",
        "end_date": "2025-12-27"
    }
    
    HR Ticket Example:
    Input: "I need to discuss my health insurance options"
    Output: {
        "intent": "create_ticket",
        "subject": "Health Insurance Discussion",
        "category": "benefits",
        "meeting_type": "online"
    }
    """
    llm_client = get_llm_client()
    
    messages = [
        {"role": "system", "content": "Extract request details..."},
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

### HR Ticket System
```python
class HRTicket(Base):
    id = Column(String, primary_key=True)  # UUID
    email = Column(String, index=True)
    company = Column(String, index=True)
    
    # Request details
    subject = Column(String)
    description = Column(String)
    category = Column(Enum(TicketCategory))
    # benefits, payroll, workplace_issue, general_inquiry,
    # policy_question, leave_related, other
    
    meeting_type = Column(Enum(MeetingType))
    # in_person, online, phone, no_meeting_needed
    
    preferred_date = Column(Date, nullable=True)
    preferred_time_slot = Column(String, nullable=True)
    urgency = Column(Enum(Urgency))  # normal, urgent
    
    # Queue management
    status = Column(Enum(TicketStatus))
    # pending, in_progress, scheduled, resolved, closed
    queue_position = Column(Integer)
    created_at = Column(DateTime)
    
    # Admin interaction
    assigned_to = Column(String, nullable=True)
    picked_up_at = Column(DateTime, nullable=True)
    
    # Meeting details
    scheduled_datetime = Column(DateTime, nullable=True)
    meeting_link = Column(String, nullable=True)
    meeting_location = Column(String, nullable=True)
    
    # Resolution
    resolved_at = Column(DateTime, nullable=True)
    resolution_notes = Column(String, nullable=True)
    
    updated_at = Column(DateTime)

class HRTicketNote(Base):
    """
    Admin notes that are visible to users.
    Provides transparent communication between admins and employees.
    """
    id = Column(String, primary_key=True)  # UUID
    ticket_id = Column(String, ForeignKey('hr_tickets.id'))
    admin_email = Column(String)
    note = Column(String)
    created_at = Column(DateTime)
    
    # Relationship
    ticket = relationship("HRTicket", backref="notes")
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

### Unified Chat Router
```
POST /api/chat/message
  Request: {"message": "What is the PTO policy?"}
  Response: {
    "response": "According to the handbook...",
    "agent_used": "rag",
    "metadata": {"sources": [...]}
  }

POST /api/chat/message
  Request: {"message": "I need 3 days off next week"}
  Response: {
    "response": "PTO request created...",
    "agent_used": "pto",
    "metadata": {"request_id": "uuid", "balance_info": {...}}
  }

POST /api/chat/message
  Request: {"message": "I need to schedule a meeting with HR"}
  Response: {
    "response": "Ticket created successfully...",
    "agent_used": "hr_ticket",
    "metadata": {"ticket_id": "uuid", "queue_position": 5}
  }
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

### HR Ticket Agent (User)
```
POST /api/hr-tickets/chat
  Request: {"message": "I need to discuss my health insurance options"}
  Response: {
    "response": "Ticket created successfully...",
    "ticket_created": true,
    "ticket_id": "uuid",
    "queue_position": 5,
    "ticket_details": {...}
  }

GET /api/hr-tickets/my-tickets
  Response: {
    "tickets": [
      {
        "id": "uuid",
        "subject": "Health Insurance Discussion",
        "status": "pending",
        "queue_position": 5,
        "created_at": "2025-11-21T10:30:00",
        "notes": [
          {
            "id": "note_uuid",
            "admin_email": "admin@company.com",
            "note": "Reviewing your request",
            "created_at": "2025-11-21T11:00:00"
          }
        ],
        ...
      }
    ],
    "total_count": 3
  }

GET /api/hr-tickets/{ticket_id}
  Response: {
    "id": "uuid",
    "subject": "...",
    "status": "scheduled",
    "scheduled_datetime": "2025-11-25T14:00:00",
    "meeting_link": "https://meet.google.com/...",
    "notes": [
      {
        "admin_email": "admin@company.com",
        "note": "Meeting scheduled for next week",
        "created_at": "2025-11-21T12:00:00"
      }
    ],
    ...
  }

DELETE /api/hr-tickets/{ticket_id}
  Response: {"message": "Ticket cancelled successfully"}
```

### HR Ticket Agent (Admin)
```
GET /api/hr-tickets/admin/queue
  Query params:
    - status_filter: pending|in_progress|scheduled|all
    - category_filter: benefits|payroll|workplace_issue|...
    - urgency_filter: urgent|normal
    - sort_by: created_at|urgency|category
  
  Response: {
    "tickets": [
      {
        "id": "uuid",
        "email": "user@company.com",
        "subject": "Health Insurance",
        "category": "benefits",
        "urgency": "normal",
        "status": "pending",
        "queue_position": 1,
        "created_at": "2025-11-21T09:00:00",
        ...
      }
    ],
    "total_count": 12
  }

POST /api/hr-tickets/admin/pick-ticket
  Request: {"ticket_id": "uuid"}
  Response: {"message": "Ticket assigned to you"}

POST /api/hr-tickets/admin/schedule-meeting
  Request: {
    "ticket_id": "uuid",
    "scheduled_datetime": "2025-11-25T14:00:00",
    "meeting_link": "https://meet.google.com/...",
    "meeting_location": null,
    "admin_notes": "Looking forward to our meeting"
  }
  Response: {"message": "Meeting scheduled successfully"}

POST /api/hr-tickets/admin/resolve
  Request: {
    "ticket_id": "uuid",
    "status": "resolved",
    "resolution_notes": "Issue resolved successfully"
  }
  Response: {"message": "Ticket resolved successfully"}

POST /api/hr-tickets/admin/add-note
  Request: {
    "ticket_id": "uuid",
    "note": "Waiting for additional information"
  }
  Response: {
    "message": "Note added successfully",
    "note": {
      "id": "note_uuid",
      "admin_email": "admin@company.com",
      "note": "Waiting for additional information",
      "created_at": "2025-11-21T13:30:00"
    }
  }

GET /api/hr-tickets/admin/stats
  Response: {
    "total_pending": 12,
    "total_in_progress": 5,
    "total_scheduled": 3,
    "total_resolved_today": 8,
    "total_closed_today": 2,
    "average_resolution_time_hours": 4.5,
    "by_category": {
      "benefits": 5,
      "payroll": 3,
      "workplace_issue": 2,
      ...
    },
    "by_urgency": {
      "normal": 15,
      "urgent": 5
    }
  }
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
- Tests: PTO Agent (Tools, Nodes), HR Ticket Agent (Tools, Nodes)
- Coverage: Agent-specific reports
- Future: Scalable for additional agents

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
pytest agents/test_agents/

# Specific agent tests
pytest agents/test_agents/test_pto_tools.py
pytest agents/test_agents/test_hr_ticket_nodes.py

# Specific test file
pytest tests/test_api/test_auth.py

# With coverage
pytest --cov=. --cov-report=html --cov-report=term

# Agent coverage
pytest agents/test_agents/ --cov=agents --cov-report=term
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

@pytest.fixture
def sample_hr_ticket(db_session):
    """Sample HR ticket for testing"""
    ticket = HRTicket(...)
    db_session.add(ticket)
    db_session.commit()
    return ticket
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
# test_hr_ticket_tools.py
def test_check_open_tickets(db_session, sample_hr_ticket):
    has_open, ticket_ids = check_open_tickets(
        db_session,
        sample_hr_ticket.email,
        sample_hr_ticket.company
    )
    assert has_open is True
    assert sample_hr_ticket.id in ticket_ids

def test_calculate_queue_position(db_session):
    position = calculate_queue_position(db_session, "Crouse Medical Practice")
    assert position == 1
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
```python
# test_hr_ticket_nodes.py
def test_parse_intent_node(db_session):
    state = HRTicketState(
        user_message="I need to discuss my health insurance",
        ...
    )
    
    result = parse_intent_node(state, db_session)
    assert result['category'] in ['benefits', 'general_inquiry']
    assert result['is_valid'] is True
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
> SELECT * FROM hr_tickets WHERE status = 'pending';
> SELECT * FROM hr_ticket_notes WHERE ticket_id = 'uuid';

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
├── pto/              # ✓ Implemented: PTO Request Agent
├── hr_ticket/        # ✓ Implemented: HR Ticket Agent
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

**Implemented Agents:**
- **PTO Request Agent**: Automated vacation request processing with balance tracking
- **HR Ticket Agent**: Employee support ticketing with queue management and meeting coordination

**Planned Agents:**
- **Expense Report Agent**: Automated expense submission and approval workflow
- **Scheduling Agent**: Shift scheduling and swap management
- **Equipment Request Agent**: Company equipment and resource requests

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