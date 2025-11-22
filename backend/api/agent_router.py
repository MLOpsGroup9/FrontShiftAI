"""
Smart Agent Router - Automatically routes messages to the correct agent
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.connection import get_db
from api.auth import get_current_user
from schemas.pto import PTOChatRequest, PTOChatResponse
from agents.utils.llm_client import get_llm_client
import json

router = APIRouter(prefix="/api/chat", tags=["Smart Agent Router"])


def detect_agent(message: str) -> str:
    """
    Detect which agent should handle the message.
    Returns: 'pto' or 'hr_ticket'
    """
    message_lower = message.lower()
    
    # PTO-related keywords
    pto_keywords = [
        'pto', 'time off', 'vacation', 'leave', 'sick day', 'sick leave',
        'days off', 'holiday', 'absence', 'request leave', 'request time',
        'how many days', 'leave balance', 'available days', 'remaining days',
        'check balance', 'pto balance', 'my balance', 'days available',
        'request pto', 'take leave', 'book time off', 'schedule vacation'
    ]
    
    # HR Ticket keywords
    hr_keywords = [
        'hr', 'human resources', 'meeting with hr', 'talk to hr', 'speak to hr',
        'insurance', 'health insurance', 'dental', 'vision', 'benefits',
        'paycheck', 'payroll', 'salary', 'pay', 'direct deposit', 'w2', 'w-2',
        'policy', 'handbook', 'guideline', 'procedure', 'rule',
        'workplace', 'work environment', 'concern', 'issue', 'problem',
        'harassment', 'complaint', 'conflict', 'schedule meeting',
        'meet with hr', 'question for hr', 'ask hr', 'hr question'
    ]
    
    # Count matches
    pto_score = sum(1 for keyword in pto_keywords if keyword in message_lower)
    hr_score = sum(1 for keyword in hr_keywords if keyword in message_lower)
    
    # If clear winner, return it
    if pto_score > hr_score:
        return 'pto'
    elif hr_score > pto_score:
        return 'hr_ticket'
    
    # If tied or no matches, use LLM for smart detection
    try:
        llm_client = get_llm_client()
        
        system_prompt = """You are an agent router. Analyze the user's message and determine which agent should handle it.

PTO Agent handles:
- Requesting time off / vacation / leave
- Checking PTO balance
- Questions about available leave days
- Scheduling time off

HR Ticket Agent handles:
- Questions about benefits (insurance, retirement, etc.)
- Payroll issues (paycheck, salary, tax forms)
- Policy questions (remote work, dress code, handbook)
- Workplace concerns or issues
- Meeting with HR for any reason
- General HR inquiries

Respond ONLY with valid JSON:
{
    "agent": "pto" or "hr_ticket",
    "confidence": "high" or "low",
    "reason": "brief explanation"
}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ]
        
        response = llm_client.chat(messages, json_mode=True, temperature=0.3)
        parsed = json.loads(response)
        return parsed.get("agent", "hr_ticket")  # Default to HR if unclear
        
    except Exception as e:
        print(f"LLM routing failed: {e}, defaulting to HR ticket")
        return 'hr_ticket'  # Default to HR ticket if detection fails


@router.post("/message")
async def smart_chat(
    request: PTOChatRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Smart chat endpoint that automatically routes to the correct agent
    """
    # Detect which agent should handle this
    agent_type = detect_agent(request.message)
    
    print(f"🤖 Routing message to: {agent_type}")
    
    # Route to appropriate agent
    if agent_type == 'pto':
        from api.pto_agent import chat_with_pto_agent
        response = await chat_with_pto_agent(request, current_user, db)
        response_dict = response.__dict__ if hasattr(response, '__dict__') else response
        response_dict['agent_used'] = 'pto'
        return response_dict
    else:
        from api.hr_ticket_agent import create_ticket_via_chat
        response = await create_ticket_via_chat(request, current_user, db)
        response_dict = response.__dict__ if hasattr(response, '__dict__') else response
        response_dict['agent_used'] = 'hr_ticket'
        return response_dict