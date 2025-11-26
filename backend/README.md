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
│   ├── website_extraction/ # Website Search Agent [NEW]
│   │   ├── agent.py        # LangGraph workflow
│   │   ├── nodes.py        # Workflow nodes
│   │   ├── state.py        # State definition
│   │   └── tools.py        # Brave Search integration
│   ├── utils/              # Shared utilities
│   │   ├── llm_client.py   # LLM client with fallback
│   │   └── llm_config.py   # Provider configuration
│   └── test_agents/        # Agent tests (206 tests) [UPDATED]
│       ├── conftest.py
│       ├── test_pto_tools.py
│       ├── test_pto_nodes.py
│       ├── test_hr_ticket_tools.py
│       ├── test_hr_ticket_nodes.py
│       ├── test_website_extraction_tools.py [NEW]
│       └── test_website_extraction_nodes.py [NEW]
│
├── api/                     # API Endpoints
│   ├── admin.py            # Admin management
│   ├── auth.py             # Authentication
│   ├── rag.py              # RAG queries
│   ├── pto_agent.py        # PTO agent endpoints
│   ├── hr_ticket_agent.py  # HR ticket endpoints
│   ├── unified_agent.py    # Unified chat router [UPDATED]
│   └── company_management.py # Company management [NEW]
│
├── db/                      # Database Layer
│   ├── connection.py       # SQLAlchemy setup
│   ├── models.py           # ORM models [UPDATED]
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
│       ├── agents.yml      # Agent tests [UPDATED]
│       └── config.yml      # Config validation
│
├── .env                     # Environment variables
├── main.py                 # Application entry
├── requirements.txt        # Dependencies
└── users.db                # SQLite database
```

## Unified Agent Router with Automatic Fallback

### Overview

The unified agent router provides intelligent message routing with **automatic fallback chain** for comprehensive information retrieval. When one agent can't answer a question, the system automatically tries the next best option.

### Fallback Architecture

**Agent Fallback Chain:**
```
User Message
    ↓
Intent Detection (LLM)
    ↓
├─→ PTO Agent (time off requests)
├─→ HR Ticket Agent (support requests)  
└─→ RAG Agent (handbook queries)
    ↓
    No answer in handbook?
    ↓
    ✓ Automatic Fallback ✓
    ↓
    Website Extraction Agent (search company website)
    ↓
    Still no answer?
    ↓
    HR Ticket Suggestion (human support)
```

**Example Flow:**
```
User: "What are the office hours for Crouse Medical?"

1. Intent Detection → "rag" (policy question)
2. RAG Agent searches handbook PDF → No relevant context found
3. **Automatic trigger** → Website Extraction Agent
4. Brave Search → crousemedical.com site:crousemedical.com office hours
5. Finds: "Mon-Fri 8AM-5PM" on /contact page
6. Returns answer with source attribution
```

### Implementation

**Endpoint:**
```
POST /api/chat/message
Request: {
  "message": "What are the office hours?",
  "conversation_id": "uuid" (optional)
}

Response: {
  "response": "🔍 Found on Crouse Medical Practice's website:...",
  "agent_used": "website_extraction",
  "conversation_id": "uuid",
  "metadata": {
    "found_answer": true,
    "source_urls": ["https://crousemedical.com/contact"],
    "confidence": 0.85,
    "triggered_by": "rag_fallback"
  }
}
```

**Fallback Trigger Logic:**
```python
# In unified_agent.py
rag_result = await rag_query(request, current_user)

# Check if RAG found nothing
if "No relevant context found" in rag_result.answer:
    # Automatically trigger Website Extraction
    website_agent = WebsiteExtractionAgent(db)
    website_result = await website_agent.execute(
        user_email=current_user["email"],
        company=current_user["company"],
        message=request.message,
        triggered_by="rag_fallback",
        original_query=request.message
    )
    
    if website_result["found_answer"]:
        return website_result  # Success!
    else:
        return website_result["hr_ticket_suggestion"]  # Final fallback
```

### Website Extraction Agent (NEW)

**Purpose:**
Automatically searches company websites when handbook PDFs don't contain the requested information. Handles operational details typically found on websites but not in employee handbooks.

**Use Cases:**
- Office hours and contact information
- Department-specific phone numbers
- Physical location addresses
- Staff directory and employee listings
- Current services and offerings
- Parking and facility information
- Real-time operational updates

**Workflow:**
```
START
  ↓
Parse Query (extract keywords, optimize search)
  ↓
Resolve Domain (get company website from database)
  ↓
Brave Search (API call with site: filter)
  ↓
Analyze Results (rank by relevance, score confidence)
  ↓
Found answer? (confidence ≥ 0.5)
  ↓
├─ YES → Generate Answer (LLM synthesis with sources)
└─ NO → Suggest HR Ticket (human support fallback)
  ↓
Format Response (with confidence indicator)
  ↓
END
```

**State Definition:**
```python
class WebsiteExtractionState(TypedDict):
    # Input
    user_email: str
    company: str
    user_message: str
    triggered_by: str  # 'rag_fallback' or 'direct'
    
    # Search optimization
    search_topic: str
    search_keywords: List[str]
    search_query: str
    info_type: str  # contact|hours|services|policies|pricing|locations
    
    # Domain resolution
    company_domain: str
    domain_found: bool
    
    # Search results
    brave_results: List[dict]
    ranked_results: List[dict]
    confidence_score: float
    found_answer: bool
    
    # Output
    answer: str
    source_urls: List[str]
    suggest_hr_ticket: bool
    agent_response: str
```

**Brave Search Integration:**
```python
def brave_search(query: str, site_domain: str) -> Tuple[List[dict], Optional[str]]:
    """
    Execute Brave Search API with site-specific filtering
    
    Example:
    query = "office hours"
    site_domain = "crousemedical.com"
    
    Actual search: "office hours site:crousemedical.com"
    
    Returns: (results, error)
    - results: List of {title, url, description, extra_snippets}
    - error: None on success, error message on failure
    """
```

**Relevance Scoring:**
```python
def score_result_relevance(result: dict, keywords: List[str], topic: str) -> float:
    """
    Multi-factor scoring (0.0 - 1.0):
    - Keyword match: 40% (presence in title/description)
    - Title relevance: 25% (topic match in title)
    - Snippet quality: 25% (description length, extra snippets, contact info)
    - Page type boost: 10% (/contact, /about pages boosted; /blog penalized)
    
    Contact pages with rich snippets score highest (0.8+)
    Blog posts score lowest (0.2-)
    """
```

**Confidence Thresholds:**
- **High Confidence (≥0.7)**: Answer presented with full confidence
- **Medium Confidence (0.5-0.7)**: Answer with verification suggestion
- **Low Confidence (<0.5)**: Suggest HR ticket for accurate information

**Example Interaction:**
```
User: "Who are the doctors at Crouse Medical?"

RAG Agent: No relevant context found in handbook
↓ (automatic fallback)
Website Extraction Agent:
  - Searches: "doctors site:crousemedical.com"
  - Finds: Staff directory page
  - Confidence: 0.82 (high)
  - Response: "🔍 Found on Crouse Medical Practice's website:
              
              Dr. Smith (Cardiology), Dr. Jones (Pediatrics)...
              
              📎 Source: crousemedical.com/our-team"
```

**API Integration:**
- Uses Brave Search API for web search
- Requires `BRAVE_API_KEY` in environment
- Handles rate limits and timeouts gracefully
- Falls back to HR ticket on API failures

### Conversation Examples

**Multi-Agent with Fallback:**
```
User: "What is the remote work policy?"
System: [RAG Agent] According to the handbook, employees may work remotely...

User: "What are the office hours?"
System: [RAG → Website Extraction fallback] 🔍 Found on company website: Mon-Fri 8AM-5PM

User: "I need 3 days off next week"
System: [PTO Agent] PTO request created for Dec 24-26...

User: "Who is the benefits coordinator?"
System: [RAG → Website Extraction fallback] 🔍 Based on the website, Jane Doe handles benefits

User: "Schedule a meeting with her"
System: [HR Ticket Agent] Support ticket created. You are #3 in queue...
```

### Benefits

1. **Seamless Fallback**: Users don't see "not found" errors - system automatically searches alternative sources
2. **Comprehensive Coverage**: Handbook + Website + Human support = complete information access
3. **Source Attribution**: All website-sourced answers include URL references
4. **Confidence Indication**: Users know when to verify information independently
5. **Intelligent Search**: Site-specific searches ensure results come from official company sources only

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

### Website Extraction Agent (NEW)

**Purpose:**
Automatic fallback when RAG agent finds no information in handbook PDFs. Searches company websites via Brave Search API to find operational information not typically documented in employee handbooks.

**When Triggered:**
- **Automatically**: When RAG returns "No relevant context found"
- **Seamlessly**: User doesn't see the fallback - just gets an answer
- **Intelligently**: Only for information likely to be on websites (hours, contacts, locations, staff)

**What It Finds:**
- Office hours and operating schedules
- Contact information (phone, email, departments)
- Physical locations and addresses
- Staff directories and employee listings
- Services and offerings
- Parking and facility details
- Information not in static PDFs

**Workflow:**
```
START (triggered by RAG fallback)
  ↓
Parse Query (extract keywords: "office hours" → ["office", "hours", "contact"])
  ↓
Resolve Domain (database: "Crouse Medical Practice" → crousemedical.com)
  ↓
Brave Search (API: "office hours site:crousemedical.com")
  ↓
Rank Results (relevance scoring: contact pages boosted, blogs penalized)
  ↓
Confidence ≥ 0.5?
  ├─ YES → Generate Answer (LLM synthesis from top 3 results)
  └─ NO → Suggest HR Ticket (human support)
  ↓
Format Response (with source URLs and confidence indicator)
  ↓
END
```

**Relevance Scoring Algorithm:**
```python
# Multi-factor scoring (0.0 - 1.0):
- Keyword Match: 40%     # "hours" in content
- Title Relevance: 25%   # "Office Hours" in title
- Snippet Quality: 25%   # Long description, contact info present
- Page Type: 10%         # /contact boosted, /blog penalized

# Example scores:
/contact page with hours: 0.85 (high)
/about page mentioning hours: 0.45 (medium)  
/blog post: 0.15 (low)
```

**Confidence Levels:**
- **≥0.7**: "Found on company's website" (high confidence)
- **0.5-0.7**: "Found some information... verify directly" (medium confidence)
- **<0.5**: "Couldn't find... create HR ticket?" (low confidence)

**Example Interaction:**
```
User: "What are the office hours for Crouse Medical?"

1. Unified Agent → detect_intent() → "rag"
2. RAG Agent → searches handbook → "No relevant context found"
3. ✓ Automatic Fallback ✓
4. Website Extraction Agent:
   - Domain: crousemedical.com
   - Search: "office hours site:crousemedical.com"
   - Results: Contact page found
   - Rank: 0.85 confidence
   - Answer: "Mon-Fri 8AM-5PM"
5. Response: "🔍 Found on Crouse Medical Practice's website:
              
              Office Hours: Monday-Friday 8:00 AM - 5:00 PM
              
              📎 Source: crousemedical.com/contact"
```

**API Requirements:**
- **Brave Search API Key**: Required for web search functionality
- Set in `.env`: `BRAVE_API_KEY=your_brave_api_key`
- Free tier available at https://brave.com/search/api/
- Timeout handling: 10 seconds default
- Rate limiting: Handled gracefully with error messages

**Error Handling:**
- **API Timeout**: Suggests HR ticket
- **No API Key**: Suggests HR ticket  
- **Rate Limited**: Suggests HR ticket
- **No Results Found**: Suggests HR ticket with specific topic
- **Low Confidence**: Presents answer with verification suggestion

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

### Chat Persistence (NEW)
```python
class Conversation(Base):
    """User chat conversations"""
    id = Column(String, primary_key=True)  # UUID
    email = Column(String, index=True)
    company = Column(String, index=True)
    title = Column(String)  # First user message
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

class Message(Base):
    """Individual messages within conversations"""
    id = Column(String, primary_key=True)  # UUID
    conversation_id = Column(String, index=True)
    role = Column(String)  # 'user' or 'assistant'
    content = Column(String)
    agent_type = Column(String)  # 'rag', 'pto', 'hr_ticket', 'website_extraction'
    message_metadata = Column(String)  # JSON metadata
    created_at = Column(DateTime)
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
    meeting_type = Column(Enum(MeetingType))
    
    preferred_date = Column(Date, nullable=True)
    preferred_time_slot = Column(String, nullable=True)
    urgency = Column(Enum(Urgency))  # normal, urgent
    
    # Queue management
    status = Column(Enum(TicketStatus))
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

### Unified Chat Router (UPDATED)
```
POST /api/chat/message
  Request: {
    "message": "What is the PTO policy?",
    "conversation_id": "uuid" (optional)
  }
  Response: {
    "response": "According to the handbook...",
    "agent_used": "rag",
    "conversation_id": "uuid",
    "metadata": {"sources": [...]}
  }

# Website Extraction Example (automatic fallback)
POST /api/chat/message
  Request: {"message": "What are the office hours?"}
  Response: {
    "response": "🔍 Found on company's website: Mon-Fri 8AM-5PM",
    "agent_used": "website_extraction",
    "conversation_id": "uuid",
    "metadata": {
      "found_answer": true,
      "source_urls": ["https://company.com/contact"],
      "confidence": 0.85,
      "triggered_by": "rag_fallback"
    }
  }

# Chat History (NEW)
GET /api/chat/conversations
  Response: [
    {
      "id": "uuid",
      "title": "What is the PTO policy?",
      "created_at": "2025-11-26T10:00:00",
      "updated_at": "2025-11-26T10:05:00"
    }
  ]

GET /api/chat/conversations/{id}/messages
  Response: [
    {
      "id": "msg_uuid",
      "role": "user",
      "content": "What are the hours?",
      "agent_type": null,
      "created_at": "2025-11-26T10:00:00"
    },
    {
      "id": "msg_uuid2",
      "role": "assistant",
      "content": "Mon-Fri 8AM-5PM",
      "agent_type": "website_extraction",
      "created_at": "2025-11-26T10:00:15"
    }
  ]

DELETE /api/chat/conversations/{id}
  Response: {"message": "Conversation deleted"}
```

### Company Management (NEW)
```
POST /api/company/add
  Request: {
    "company_name": "New Medical Center",
    "domain": "Healthcare",
    "url": "https://newmedical.com/handbook.pdf"
  }
  Response: {
    "message": "Company processing started",
    "task_id": "uuid",
    "company_name": "New Medical Center"
  }

GET /api/company/task-status/{task_id}
  Response: {
    "task_id": "uuid",
    "status": "running",
    "message": "Running data pipeline...",
    "started_at": "2025-11-26T10:00:00"
  }
```

### RAG Queries
```
POST /api/rag/query
  Request: {"query": "What is the PTO policy?", "top_k": 3}
  Response: {"answer": "...", "sources": [...], "company": "..."}
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

**Agent Tests** (`.github/workflows/agents.yml`) [UPDATED]:
- Triggers: Push/PR to any branch with agent changes
- Tests: PTO Agent, HR Ticket Agent, Website Extraction Agent [NEW]
- Coverage: Agent-specific reports
- Total: 206 automated tests (was 167)

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

# Agent tests only (206 tests) [UPDATED]
pytest agents/test_agents/

# Specific agent tests
pytest agents/test_agents/test_pto_tools.py
pytest agents/test_agents/test_hr_ticket_nodes.py
pytest agents/test_agents/test_website_extraction_tools.py [NEW]
pytest agents/test_agents/test_website_extraction_nodes.py [NEW]

# Specific test file
pytest tests/test_api/test_auth.py

# With coverage
pytest --cov=. --cov-report=html --cov-report=term

# Agent coverage (includes website extraction) [UPDATED]
pytest agents/test_agents/ --cov=agents --cov-report=term
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
GROQ_API_KEY=your_groq_key
BRAVE_API_KEY=your_brave_key
JWT_SECRET_KEY=secure_random_key
GENERATION_BACKEND=auto
GOOGLE_APPLICATION_CREDENTIALS=/path/to/gcs-key.json
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
> SELECT * FROM conversations LIMIT 10;
> SELECT * FROM messages WHERE conversation_id = 'uuid';

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

# External APIs [NEW]
BRAVE_API_KEY=your_brave_key

# Security
JWT_SECRET_KEY=secure_random_key
CORS_ORIGINS=https://yourdomain.com

# Google Cloud Storage [NEW]
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

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
- Secure API keys (Brave, Groq) [NEW]

**Database:**
- Migrate to PostgreSQL
- Configure connection pooling
- Set up automated backups
- Implement migration tool (Alembic)
- Add database indexes
- Chat history retention policies [NEW]

**Monitoring:**
- Configure application logging
- Set up error tracking
- Implement health check monitoring
- Configure performance metrics
- Set up alerting
- Monitor external API usage (Brave Search) [NEW]

**Infrastructure:**
- Configure reverse proxy
- Set up load balancing
- Implement container orchestration
- Configure auto-scaling
- Set up deployment pipeline
- GCS sync for data pipeline [NEW]

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
- Verify API keys in environment (Groq, Brave) [UPDATED]
- Review agent workflow logs

**Database Issues:**
- Verify database file exists
- Check file permissions
- Reset database if corrupted

**Website Extraction Failures (NEW):**
- Verify BRAVE_API_KEY is set
- Check Brave API rate limits
- Ensure company has URL in database
- Review search timeout settings

## Future Agents

The architecture supports multiple agents:
```
agents/
├── pto/              # ✓ Implemented: PTO Request Agent
├── hr_ticket/        # ✓ Implemented: HR Ticket Agent
├── website_extraction/ # ✓ Implemented: Website Search Agent [NEW]
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
- **Website Extraction Agent**: Automatic web search fallback for information not in handbooks [NEW]

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
- **Brave Search API**: https://brave.com/search/api/ [NEW]

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