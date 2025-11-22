"""
Unified Agent - Handles RAG, PTO, and HR Tickets in one conversation
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.connection import get_db
from api.auth import get_current_user
from pydantic import BaseModel
from agents.utils.llm_client import get_llm_client
from agents.pto.agent import PTOAgent
from agents.hr_ticket.agent import HRTicketAgent
from schemas.rag import RAGQueryRequest
from api.rag import rag_query
import json

router = APIRouter(prefix="/api/chat", tags=["Unified Agent"])


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    agent_used: str
    metadata: dict = {}


def detect_intent(message: str) -> dict:
    """
    Detect user intent and which agent should handle it.
    Returns: {'agent': 'rag'|'pto'|'hr_ticket', 'confidence': 'high'|'low'}
    """
    message_lower = message.lower()
    
    # High-confidence PTO keywords
    pto_strong = [
        'request pto', 'request leave', 'request time off', 'request vacation',
        'book pto', 'book leave', 'book vacation', 'take time off',
        'need time off', 'need leave', 'need vacation', 'days off',
        'pto balance', 'leave balance', 'how many days', 'available days',
        'remaining days', 'check balance', 'my balance', 'check my balance',
        'i need leave', 'i need time off', 'i need pto', 'i want to take',
        'can i take', 'taking leave', 'taking time off'
    ]
    
    # High-confidence HR Ticket keywords
    hr_strong = [
        'schedule meeting with hr', 'meet with hr', 'talk to hr', 'speak to hr',
        'hr meeting', 'hr appointment', 'meeting with human resources',
        'schedule hr', 'book hr meeting', 'create ticket', 'hr ticket',
        'open ticket', 'submit ticket', 'paycheck issue', 'payroll problem',
        'meet hr', 'discuss with hr', 'contact hr', 'hr help',
        'insurance meeting', 'benefits meeting', 'schedule with hr'
    ]
    
    # Check for strong matches
    for keyword in pto_strong:
        if keyword in message_lower:
            return {'agent': 'pto', 'confidence': 'high'}
    
    for keyword in hr_strong:
        if keyword in message_lower:
            return {'agent': 'hr_ticket', 'confidence': 'high'}
    
    # Use LLM for ambiguous cases
    try:
        llm_client = get_llm_client()
        
        system_prompt = """Analyze the message and determine intent. Respond with JSON only.

**PTO Agent** - User wants to ACTION:
- Request/book time off, vacation, leave, PTO
- Check their PTO/leave balance or available days
- Examples: "I need 3 days off", "request leave for next week", "how many days do I have left"

**HR Ticket Agent** - User wants to SCHEDULE/MEET:
- Schedule a meeting with HR
- Discuss benefits, insurance, payroll issues with HR (needs meeting)
- Report workplace issues requiring HR intervention
- Create a support ticket
- Examples: "schedule meeting with HR", "discuss my insurance with HR", "paycheck problem, need to talk to HR"

**RAG Agent** - User wants to LEARN/KNOW:
- Learn about company policies (remote work, dress code, procedures)
- Ask general informational questions about the handbook
- Get information without taking action or scheduling
- Examples: "what is the PTO policy", "tell me about benefits", "what are the company holidays", "how does remote work work"

IMPORTANT: 
- Questions ABOUT policies = RAG
- REQUESTS for action = PTO or HR Ticket
- "What is the PTO policy?" = RAG
- "I need PTO" = PTO Agent
- "Schedule meeting about benefits" = HR Ticket

JSON format:
{
    "agent": "pto" or "hr_ticket" or "rag",
    "reasoning": "brief explanation"
}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ]
        
        response = llm_client.chat(messages, json_mode=True, temperature=0.2)
        result = json.loads(response)
        return {'agent': result.get('agent', 'rag'), 'confidence': 'medium'}
        
    except Exception as e:
        print(f"Intent detection failed: {e}")
        # Smart fallback based on question words
        question_words = ['what', 'how', 'why', 'when', 'where', 'who', 'which', 
                         'tell me', 'explain', 'describe', 'define']
        
        if any(word in message_lower for word in question_words):
            return {'agent': 'rag', 'confidence': 'low'}
        else:
            # If no question words, likely an action request
            return {'agent': 'hr_ticket', 'confidence': 'low'}


@router.post("/message", response_model=ChatResponse)
async def unified_chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Unified chat endpoint - intelligently routes to RAG, PTO, or HR Ticket agents
    """
    message = request.message
    
    # Detect intent
    intent = detect_intent(message)
    agent_type = intent['agent']
    
    print(f"🤖 Routing to {agent_type} agent (confidence: {intent['confidence']})")
    
    try:
        if agent_type == 'pto':
            # Use PTO Agent
            pto_agent = PTOAgent(db)
            result = await pto_agent.execute(
                user_email=current_user["email"],
                company=current_user["company"],
                message=message
            )
            
            return ChatResponse(
                response=result["response"],
                agent_used="pto",
                metadata={
                    "request_created": result.get("request_created", False),
                    "request_id": result.get("request_id"),
                    "balance_info": result.get("balance_info")
                }
            )
            
        elif agent_type == 'hr_ticket':
            # Use HR Ticket Agent
            hr_agent = HRTicketAgent()
            result = await hr_agent.process_message(
                user_email=current_user["email"],
                company=current_user["company"],
                message=message,
                db=db
            )
            
            return ChatResponse(
                response=result["response"],
                agent_used="hr_ticket",
                metadata={
                    "ticket_created": result.get("ticket_created", False),
                    "ticket_id": result.get("ticket_id"),
                    "queue_position": result.get("queue_position")
                }
            )
            
        else:  # rag
            # Use existing RAG endpoint
            rag_request = RAGQueryRequest(
                query=message,
                top_k=3
            )
            
            rag_result = await rag_query(rag_request, current_user)
            
            return ChatResponse(
                response=rag_result.answer,
                agent_used="rag",
                metadata={
                    "sources": rag_result.sources,  # Already formatted by rag_query
                    "company": rag_result.company
                }
            )
            
    except Exception as e:
        print(f"❌ Error in unified agent: {e}")
        import traceback
        traceback.print_exc()
        
        # Return a helpful error message
        return ChatResponse(
            response=f"Sorry, I encountered an error processing your request: {str(e)}",
            agent_used="error",
            metadata={"error": str(e)}
        )


@router.get("/health")
def health_check():
    """Health check for unified agent"""
    return {
        "status": "ok", 
        "message": "Unified agent is running",
        "agents": ["rag", "pto", "hr_ticket"]
    }