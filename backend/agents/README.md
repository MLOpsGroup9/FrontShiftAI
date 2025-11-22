# FrontShiftAI Agent System

AI agent architecture built on LangGraph for automated workflow processing. Handles PTO requests and HR ticketing through stateful workflows.

## Architecture

### Directory Structure

```
agents/
├── base/                    # Base classes
├── pto/                     # PTO Request Agent
│   ├── agent.py            # Workflow definition
│   ├── nodes.py            # Processing functions
│   ├── state.py            # State types
│   └── tools.py            # Database utilities
├── hr_ticket/              # HR Ticket Agent
│   ├── agent.py            # Workflow definition
│   ├── nodes.py            # Processing functions
│   ├── state.py            # State types
│   └── tools.py            # Database utilities
├── utils/                   # Shared utilities
│   ├── llm_client.py       # LLM interface
│   └── llm_config.py       # Provider config
└── test_agents/            # Tests
    ├── conftest.py         # Test fixtures
    ├── test_pto_tools.py
    ├── test_pto_nodes.py
    ├── test_hr_ticket_tools.py
    └── test_hr_ticket_nodes.py
```

### File Responsibilities

**agent.py**: Builds the LangGraph workflow. Defines nodes, edges, and routing logic. Entry point for processing requests.

**nodes.py**: Pure functions that transform state. Each node handles one step: parsing, validation, database operations, or response generation.

**state.py**: TypedDict definitions for type safety. Documents all fields that flow through the workflow.

**tools.py**: Database queries and calculations. Business day counting, conflict checking, queue position, etc.

**llm_client.py**: Unified interface for LLM providers. Handles Groq, Ollama, Mercury with automatic fallback.

**llm_config.py**: Provider settings. Change one variable to switch LLM providers.

## How It Works

### Request Flow

1. User sends message through API
2. Unified router classifies intent (RAG, PTO, or HR Ticket)
3. Router calls appropriate agent with user email, company, and message
4. Agent executes LangGraph workflow
5. Workflow returns final state with response message
6. API returns response to user

### Workflow Execution

**PTO Agent Flow:**
```
START
  ↓
Parse Intent (extract dates, reason)
  ↓
Validate Dates (check past, holidays, blackouts)
  ↓
[Valid?] → No → Generate Error Response → END
  ↓ Yes
Check Balance (sufficient days?)
  ↓
[Sufficient?] → No → Generate Error Response → END
  ↓ Yes
Check Conflicts (overlapping requests?)
  ↓
Create Request (save to DB, update balance)
  ↓
Generate Success Response
  ↓
END
```

**HR Ticket Agent Flow:**
```
START
  ↓
Parse Intent (extract subject, category, meeting prefs)
  ↓
Validate Request (required fields, valid dates)
  ↓
[Valid?] → No → Generate Error Response → END
  ↓ Yes
Check Open Tickets (existing tickets?)
  ↓
Create Ticket (save to DB, assign queue position)
  ↓
Generate Success Response
  ↓
END
```

### State Flow

State is a dictionary that flows through the workflow. Each node receives it, modifies it, and returns it.

**PTO State Fields:**
- Input: user_email, company, user_message
- Parsed: start_date, end_date, reason, intent
- Validation: is_valid, validation_errors, total_business_days
- Balance: remaining_days, has_sufficient_balance
- Conflicts: has_conflicts, conflicting_requests
- Output: request_id, agent_response

**HR Ticket State Fields:**
- Input: user_email, company, user_message
- Parsed: subject, description, category, meeting_type, preferred_date, urgency
- Validation: is_valid, validation_errors
- Duplicates: has_open_tickets, open_ticket_ids
- Output: ticket_id, queue_position, agent_response

### Node Operations

**Parse Intent Node:**
Uses LLM to extract structured data from natural language. Sends system prompt + user message, receives JSON response, parses into state fields.

**Validate Node:**
Checks business rules. Past dates, holidays, blackouts for PTO. Required fields, valid categories for HR tickets. Adds errors to state, sets is_valid flag.

**Database Operations Node:**
Queries or creates records. Checks balances, detects conflicts for PTO. Calculates queue position, checks duplicates for HR tickets.

**Generate Response Node:**
Formats final message based on state. Error messages if validation failed. Success confirmation with details if workflow succeeded.

## LLM Integration

### Provider Setup

Configuration in `llm_config.py` sets primary provider and fallback chain:

```
Primary: Groq (llama-3.1-8b-instant)
Fallback: Local Ollama → Mercury
```

Change `USE_LLM` variable to switch providers. Client handles authentication, request formatting, and fallback automatically.

### Usage Patterns

**Structured Data Extraction:**
JSON mode enabled, low temperature (0.3), detailed system prompt with examples.

**Response Generation:**
JSON mode disabled, higher temperature (0.7), conversational prompts.

**Fallback Logic:**
Try primary provider with 3 retries. If all fail, try next in fallback chain. If all providers fail, raise exception.

## Database Integration

### Tools Layer

All database operations happen in `tools.py`. Nodes call these functions:

**PTO Tools:**
- `calculate_business_days()`: Counts weekdays excluding holidays
- `check_conflicting_requests()`: Finds overlapping approved requests
- `get_pto_balance()`: Retrieves employee balance
- `create_pto_request()`: Creates request record, updates balance

**HR Ticket Tools:**
- `calculate_queue_position()`: Counts pending tickets + 1
- `check_open_tickets()`: Finds pending/in-progress tickets
- `create_ticket_in_db()`: Creates ticket record

### Multi-Tenancy

All queries filter by company. Users only see their company's data. Tools enforce this isolation at the database layer.

## Testing Structure

### Test Organization

```
test_agents/
├── conftest.py              # Shared fixtures (DB, sample data)
├── test_pto_tools.py        # PTO utility function tests
├── test_pto_nodes.py        # PTO workflow node tests
├── test_hr_ticket_tools.py  # HR ticket utility tests
└── test_hr_ticket_nodes.py  # HR ticket workflow tests
```

### Fixture Hierarchy

**conftest.py provides:**
- `db_session`: In-memory SQLite database, fresh per test
- `sample_user`: Test user record
- `sample_company`: Test company record
- `sample_pto_balance`: PTO balance with known values
- `sample_hr_ticket`: HR ticket with known status

Tests use these fixtures as building blocks. Database recreated for each test ensures isolation.

### Tool Tests

Test utility functions independently:

**Business Day Calculator:**
- No holidays: Mon-Fri = 5 days
- With holidays: Mon-Fri with Wed holiday = 4 days
- Weekend only: Sat-Sun = 0 days
- Multi-week spans calculate correctly

**Conflict Checker:**
- Detects overlapping date ranges
- Ignores non-overlapping requests
- Returns correct conflict details
- Filters by company and approved status

**Queue Position:**
- Empty queue returns position 1
- Existing tickets increment correctly
- Filters by company

### Node Tests

Test workflow steps with mock state:

**Validation Tests:**
- Reject past dates
- Reject weekend-only requests
- Exclude holidays correctly
- Detect blackout periods
- Calculate business days accurately

**Balance Check Tests:**
- Detect insufficient balance
- Calculate remaining days correctly
- Handle missing balance records

**Parsing Tests:**
- Extract dates from natural language
- Handle relative dates ("next week")
- Classify categories correctly
- Detect urgency keywords

**Creation Tests:**
- Generate unique IDs
- Update database correctly
- Handle transaction errors

### Running Tests

```bash
# All agent tests
pytest agents/test_agents/

# Specific agent
pytest agents/test_agents/test_pto*.py
pytest agents/test_agents/test_hr_ticket*.py

# With coverage
pytest agents/test_agents/ --cov=agents --cov-report=html

# Specific test
pytest agents/test_agents/test_pto_tools.py::test_calculate_business_days
```

### Coverage Goals

- Tools: 90%+ coverage (critical business logic)
- Nodes: 85%+ coverage (workflow steps)
- Integration: Key user flows tested end-to-end

## Agent Details

### PTO Request Agent

**Purpose:** Automate vacation request processing

**Key Nodes:**
1. Parse dates and reason from message
2. Validate against holidays, blackouts, past dates
3. Check employee balance
4. Detect conflicts with approved requests
5. Create request record
6. Generate confirmation

**Business Rules:**
- Cannot request past dates
- Must include weekdays
- Holidays excluded from count
- Blackout periods rejected
- Requires sufficient balance
- Conflicts shown but don't block

**Database Operations:**
- Query holidays and blackouts
- Check PTO balance
- Find conflicting requests
- Create PTORequest record
- Update pending balance

### HR Ticket Agent

**Purpose:** Automate support ticket creation

**Key Nodes:**
1. Parse subject, category, meeting preferences
2. Validate required fields and dates
3. Check existing open tickets
4. Create ticket record with queue position
5. Generate confirmation

**Categories:**
- benefits: Insurance, retirement
- payroll: Pay issues
- workplace_issue: Conflicts, concerns
- general_inquiry: Questions
- policy_question: Policy clarification
- leave_related: Non-PTO leave

**Meeting Types:**
- in_person: Physical meeting
- online: Video call
- phone: Phone call
- no_meeting_needed: Simple inquiry

**Database Operations:**
- Check open tickets
- Calculate queue position
- Create HRTicket record
- Generate unique ID

## Key Concepts

### LangGraph Workflow

Graph with nodes (functions) and edges (connections). State flows through nodes. Conditional routing based on state values.

**Benefits:**
- Declarative workflow definition
- Each step independently testable
- Easy to visualize and modify
- Automatic state propagation

### State Immutability

Nodes receive state, return new state. Never modify in place. Makes workflows predictable and testable.

### Error Accumulation

Errors stored in state, not raised as exceptions. Workflows complete with error details. Conditional routing handles error paths.

### Pure Functions

Nodes are pure: same input = same output. No side effects except database reads. Makes testing straightforward.

### Singleton Pattern

Agents compiled once, reused for all requests. Workflow graph construction is expensive, so we cache it.

## Future Extensions

### Planned Agents

**Expense Report Agent:**
Parse receipts, validate amounts, check policy, route to approvers, track reimbursement.

**Scheduling Agent:**
Handle shift swaps, validate coverage, check availability, manage approvals, update schedules.

**Equipment Request Agent:**
Parse requests, check inventory, validate eligibility, route to approvers, track fulfillment.

### Adding New Agents

1. Create `agents/new_agent/` directory
2. Define state in `state.py`
3. Implement nodes in `nodes.py`
4. Create utilities in `tools.py`
5. Build graph in `agent.py`
6. Write tests in `test_agents/`
7. Add to unified router
8. Update documentation

## Best Practices

**State Design:**
- Use TypedDict for type safety
- Document every field
- Include validation flags
- Keep related data together

**Node Implementation:**
- Pure functions only
- Single responsibility
- Accumulate errors, don't raise
- Accept DB session as parameter

**Testing:**
- Test tools independently
- Test nodes with mock state
- Test integration flows
- Use fixtures for setup

**LLM Usage:**
- Low temp for parsing (0.3)
- High temp for generation (0.7)
- JSON mode for structured data
- Clear prompts with examples
- Enable fallback in production

## Resources

- LangGraph: https://langchain-ai.github.io/langgraph
- Groq API: https://console.groq.com/docs
- Ollama: https://ollama.ai
- Pytest: https://docs.pytest.org