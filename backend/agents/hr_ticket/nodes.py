"""
LangGraph nodes for HR Ticket Agent workflow
"""
from agents.hr_ticket.state import HRTicketState
from agents.hr_ticket.tools import (
    check_open_tickets,
    create_ticket_in_db,
    validate_date
)
from agents.utils.llm_client import get_llm_client
from sqlalchemy.orm import Session
from datetime import datetime
import json


def parse_intent_node(state: HRTicketState, db: Session) -> HRTicketState:
    """
    Parse user's message to extract ticket details using LLM.
    If LLM fails, use smart keyword-based fallback.
    """
    llm_client = get_llm_client()
    
    system_prompt = """You are an HR ticket assistant. Extract ticket information from the user's message.

Categories: benefits, payroll, workplace_issue, general_inquiry, policy_question, leave_related, other
Meeting types: in_person, online, phone, no_meeting_needed
Urgency: normal, urgent
Time slots: morning, afternoon, evening, anytime

Respond ONLY with valid JSON in this exact format:
{
    "intent": "create_ticket",
    "subject": "Brief subject line",
    "description": "Full description of the request",
    "category": "category_name",
    "meeting_type": "meeting_type",
    "preferred_date": "YYYY-MM-DD or null",
    "preferred_time_slot": "time_slot or null",
    "urgency": "normal or urgent"
}

IMPORTANT: Always create a ticket. Extract a subject and category from the message.

Examples:
- "I need to discuss my health insurance" -> category: benefits, subject: "Health Insurance Discussion", meeting_type: online
- "There's a problem with my paycheck" -> category: payroll, subject: "Paycheck Issue", urgency: urgent
- "I have a workplace concern" -> category: workplace_issue, subject: "Workplace Concern", meeting_type: in_person
- "What's the policy on remote work?" -> category: policy_question, subject: "Remote Work Policy Question", meeting_type: no_meeting_needed
- "Schedule meeting please" -> category: general_inquiry, subject: "HR Meeting Request", meeting_type: online"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": state["user_message"]}
    ]
    
    try:
        response = llm_client.chat(messages, json_mode=True, temperature=0.3)
        parsed_data = json.loads(response)
        
        # Update state with parsed data
        state["intent"] = parsed_data.get("intent", "create_ticket")
        state["subject"] = parsed_data.get("subject", "HR Inquiry")
        state["description"] = parsed_data.get("description", state["user_message"])
        state["category"] = parsed_data.get("category", "general_inquiry")
        state["meeting_type"] = parsed_data.get("meeting_type", "online")
        state["urgency"] = parsed_data.get("urgency", "normal")
        state["preferred_time_slot"] = parsed_data.get("preferred_time_slot")
        
        # Parse date if provided
        date_str = parsed_data.get("preferred_date")
        if date_str and date_str != "null":
            try:
                state["preferred_date"] = datetime.strptime(date_str, "%Y-%m-%d").date()
            except:
                state["preferred_date"] = None
        else:
            state["preferred_date"] = None
        
        state["is_valid"] = True
        state["validation_errors"] = []
        
    except Exception as e:
        print(f"Error parsing intent with LLM: {e}")
        print(f"Falling back to keyword-based parsing...")
        
        # Smart keyword-based fallback
        msg_lower = state["user_message"].lower()
        
        # Determine category from keywords
        if any(word in msg_lower for word in ['insurance', 'health', 'dental', 'vision', 'benefits', 'coverage', 'retirement', '401k', 'pension', 'medical']):
            category = 'benefits'
            subject = 'Benefits Inquiry'
        elif any(word in msg_lower for word in ['paycheck', 'salary', 'pay', 'payroll', 'direct deposit', 'tax', 'w2', 'w-2', 'wages', 'compensation']):
            category = 'payroll'
            subject = 'Payroll Issue'
        elif any(word in msg_lower for word in ['issue', 'problem', 'concern', 'conflict', 'harassment', 'complaint', 'workplace', 'environment']):
            category = 'workplace_issue'
            subject = 'Workplace Concern'
        elif any(word in msg_lower for word in ['policy', 'rule', 'handbook', 'guideline', 'remote work', 'dress code', 'procedure']):
            category = 'policy_question'
            subject = 'Policy Question'
        elif any(word in msg_lower for word in ['pto', 'vacation', 'time off', 'leave', 'sick day', 'sick leave', 'absence']):
            category = 'leave_related'
            subject = 'Leave Related Question'
        else:
            category = 'general_inquiry'
            # Try to create a meaningful subject from message
            msg_words = state["user_message"].split()[:6]
            subject = ' '.join(msg_words)
            if len(state["user_message"].split()) > 6:
                subject += '...'
            if not subject.strip():
                subject = 'HR Support Request'
        
        # Determine urgency
        urgency = 'urgent' if any(word in msg_lower for word in ['urgent', 'asap', 'emergency', 'immediately', 'critical', 'important']) else 'normal'
        
        # Determine meeting type
        if any(phrase in msg_lower for phrase in ['in person', 'in-person', 'face to face', 'face-to-face', 'office']):
            meeting_type = 'in_person'
        elif any(word in msg_lower for word in ['phone', 'call', 'telephone']):
            meeting_type = 'phone'
        elif any(phrase in msg_lower for phrase in ['no meeting', 'just question', 'quick question', 'just asking', 'no need to meet']):
            meeting_type = 'no_meeting_needed'
        else:
            meeting_type = 'online'
        
        # Detect time preferences
        preferred_time_slot = None
        if 'morning' in msg_lower:
            preferred_time_slot = 'morning'
        elif 'afternoon' in msg_lower:
            preferred_time_slot = 'afternoon'
        elif 'evening' in msg_lower:
            preferred_time_slot = 'evening'
        
        state["intent"] = "create_ticket"
        state["subject"] = subject
        state["description"] = state["user_message"]
        state["category"] = category
        state["meeting_type"] = meeting_type
        state["urgency"] = urgency
        state["preferred_date"] = None
        state["preferred_time_slot"] = preferred_time_slot
        state["is_valid"] = True
        state["validation_errors"] = []
    
    return state


def validate_request_node(state: HRTicketState, db: Session) -> HRTicketState:
    """
    Validate the ticket request.
    - Check if preferred date is valid
    - Ensure required fields are present
    """
    errors = []
    
    # Validate subject
    if not state.get("subject") or len(state["subject"].strip()) == 0:
        errors.append("Subject is required")
    
    # Validate description
    if not state.get("description") or len(state["description"].strip()) == 0:
        errors.append("Description is required")
    
    # Validate preferred date (only if provided and not None)
    if state.get("preferred_date") is not None:
        is_valid, error_msg = validate_date(state["preferred_date"])
        if not is_valid:
            # Instead of failing, just clear the invalid date
            state["preferred_date"] = None
            # Don't add to errors - we'll just proceed without a specific date
    
    if errors:
        state["is_valid"] = False
        state["validation_errors"] = errors
    else:
        state["is_valid"] = True
        state["validation_errors"] = []
    
    return state


def check_duplicates_node(state: HRTicketState, db: Session) -> HRTicketState:
    """
    Check if user has existing open tickets.
    This is just informational - we still allow creating new tickets.
    """
    has_open, ticket_ids = check_open_tickets(
        db,
        state["user_email"],
        state["company"]
    )
    
    state["has_open_tickets"] = has_open
    state["open_ticket_ids"] = ticket_ids
    
    return state


def create_ticket_node(state: HRTicketState, db: Session) -> HRTicketState:
    """
    Create the ticket in the database.
    """
    try:
        ticket_id, queue_position = create_ticket_in_db(
            db=db,
            email=state["user_email"],
            company=state["company"],
            subject=state["subject"],
            description=state["description"],
            category=state["category"],
            meeting_type=state["meeting_type"],
            urgency=state["urgency"],
            preferred_date=state.get("preferred_date"),
            preferred_time_slot=state.get("preferred_time_slot")
        )
        
        state["ticket_id"] = ticket_id
        state["queue_position"] = queue_position
        
    except Exception as e:
        print(f"Error creating ticket: {e}")
        state["ticket_id"] = None
        state["queue_position"] = None
        state["is_valid"] = False
        state["validation_errors"].append(f"Failed to create ticket: {str(e)}")
    
    return state


def generate_response_node(state: HRTicketState, db: Session) -> HRTicketState:
    """
    Generate the final response to the user.
    """
    if not state["is_valid"]:
        # Validation failed
        error_msg = "I couldn't process your request. " + ". ".join(state["validation_errors"])
        state["agent_response"] = error_msg
        return state
    
    if not state.get("ticket_id"):
        # Ticket creation failed
        state["agent_response"] = "I'm sorry, there was an error creating your ticket. Please try again."
        return state
    
    # Success response
    meeting_info = ""
    if state.get("preferred_date"):
        meeting_info = f"\n\nPreferred date: {state['preferred_date'].strftime('%B %d, %Y')}"
        if state.get("preferred_time_slot"):
            meeting_info += f" ({state['preferred_time_slot']})"
    
    open_tickets_note = ""
    if state["has_open_tickets"] and len(state["open_ticket_ids"]) > 0:
        open_tickets_note = f"\n\nNote: You have {len(state['open_ticket_ids'])} other open ticket(s)."
    
    response = f"""✅ Your HR ticket has been created successfully!

**Ticket ID:** {state['ticket_id']}
**Subject:** {state['subject']}
**Category:** {state['category'].replace('_', ' ').title()}
**Queue Position:** #{state['queue_position']}
**Status:** Pending{meeting_info}{open_tickets_note}

A company admin will review your request shortly. You can check the status of your ticket anytime in the "My Tickets" section."""
    
    state["agent_response"] = response
    return state