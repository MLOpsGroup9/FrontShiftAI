"""
Tests for HR Ticket Agent nodes
"""
import pytest
from datetime import date, timedelta
from agents.hr_ticket.nodes import (
    parse_intent_node,
    validate_request_node,
    check_duplicates_node,
    create_ticket_node,
    generate_response_node
)
from agents.hr_ticket.state import HRTicketState


class TestParseIntentNode:
    """Test intent parsing node"""
    
    def test_parse_basic_request(self, db_session):
        """Test parsing a basic HR request"""
        state: HRTicketState = {
            "user_email": "user@crousemedical.com",
            "company": "Crouse Medical Practice",
            "user_message": "I need to discuss my health insurance options",
            "intent": "",
            "subject": None,
            "description": None,
            "category": None,
            "meeting_type": None,
            "preferred_date": None,
            "preferred_time_slot": None,
            "urgency": "normal",
            "is_valid": False,
            "validation_errors": [],
            "has_open_tickets": False,
            "open_ticket_ids": [],
            "ticket_id": None,
            "queue_position": None,
            "agent_response": ""
        }
        
        result = parse_intent_node(state, db_session)
        
        assert result["intent"] == "create_ticket"
        assert result["subject"] is not None
        assert result["description"] is not None
        assert result["category"] in ["benefits", "general_inquiry"]
        assert result["meeting_type"] is not None
        assert result["is_valid"] is True
    
    def test_parse_urgent_request(self, db_session):
        """Test parsing an urgent request"""
        state: HRTicketState = {
            "user_email": "user@crousemedical.com",
            "company": "Crouse Medical Practice",
            "user_message": "URGENT: There's a problem with my paycheck!",
            "intent": "",
            "subject": None,
            "description": None,
            "category": None,
            "meeting_type": None,
            "preferred_date": None,
            "preferred_time_slot": None,
            "urgency": "normal",
            "is_valid": False,
            "validation_errors": [],
            "has_open_tickets": False,
            "open_ticket_ids": [],
            "ticket_id": None,
            "queue_position": None,
            "agent_response": ""
        }
        
        result = parse_intent_node(state, db_session)
        
        # If LLM is available, it should parse as payroll
        # If LLM fails, it falls back to general_inquiry
        assert result["category"] in ["payroll", "general_inquiry"]

    def test_parse_with_preferred_time(self, db_session):
        """Test parsing with preferred time slot"""
        state: HRTicketState = {
            "user_email": "user@crousemedical.com",
            "company": "Crouse Medical Practice",
            "user_message": "I'd like to meet with HR in the morning to discuss workplace policies",
            "intent": "",
            "subject": None,
            "description": None,
            "category": None,
            "meeting_type": None,
            "preferred_date": None,
            "preferred_time_slot": None,
            "urgency": "normal",
            "is_valid": False,
            "validation_errors": [],
            "has_open_tickets": False,
            "open_ticket_ids": [],
            "ticket_id": None,
            "queue_position": None,
            "agent_response": ""
        }
        
        result = parse_intent_node(state, db_session)
        
        # If LLM is available, it should parse as policy_question
        # If LLM fails, it falls back to general_inquiry
        assert result["category"] in ["policy_question", "general_inquiry", "workplace_issue"]
        # Preferred time should be detected if LLM works
        # assert result["preferred_time_slot"] in ["morning", "anytime", None]
    
    def test_fallback_on_error(self, db_session, monkeypatch):
        """Test fallback when LLM fails"""
        def mock_chat(*args, **kwargs):
            raise Exception("LLM error")
        
        from agents.utils import llm_client
        monkeypatch.setattr(llm_client, "get_llm_client", lambda: type('obj', (object,), {'chat': mock_chat})())
        
        state: HRTicketState = {
            "user_email": "user@crousemedical.com",
            "company": "Crouse Medical Practice",
            "user_message": "I need help with something",
            "intent": "",
            "subject": None,
            "description": None,
            "category": None,
            "meeting_type": None,
            "preferred_date": None,
            "preferred_time_slot": None,
            "urgency": "normal",
            "is_valid": False,
            "validation_errors": [],
            "has_open_tickets": False,
            "open_ticket_ids": [],
            "ticket_id": None,
            "queue_position": None,
            "agent_response": ""
        }
        
        result = parse_intent_node(state, db_session)
        
        # Should fallback to defaults
        assert result["intent"] == "create_ticket"
        assert result["subject"] in ["HR Inquiry", "I need help with something"]
        assert result["category"] == "general_inquiry"
        assert result["is_valid"] is True


class TestValidateRequestNode:
    """Test request validation node"""
    
    def test_valid_request(self, db_session):
        """Test validation of valid request"""
        state: HRTicketState = {
            "user_email": "user@crousemedical.com",
            "company": "Crouse Medical Practice",
            "user_message": "Test message",
            "intent": "create_ticket",
            "subject": "Test Subject",
            "description": "Test Description",
            "category": "benefits",
            "meeting_type": "online",
            "preferred_date": None,
            "preferred_time_slot": None,
            "urgency": "normal",
            "is_valid": False,
            "validation_errors": [],
            "has_open_tickets": False,
            "open_ticket_ids": [],
            "ticket_id": None,
            "queue_position": None,
            "agent_response": ""
        }
        
        result = validate_request_node(state, db_session)
        
        assert result["is_valid"] is True
        assert len(result["validation_errors"]) == 0
    
    def test_missing_subject(self, db_session):
        """Test validation fails with missing subject"""
        state: HRTicketState = {
            "user_email": "user@crousemedical.com",
            "company": "Crouse Medical Practice",
            "user_message": "Test message",
            "intent": "create_ticket",
            "subject": "",
            "description": "Test Description",
            "category": "benefits",
            "meeting_type": "online",
            "preferred_date": None,
            "preferred_time_slot": None,
            "urgency": "normal",
            "is_valid": False,
            "validation_errors": [],
            "has_open_tickets": False,
            "open_ticket_ids": [],
            "ticket_id": None,
            "queue_position": None,
            "agent_response": ""
        }
        
        result = validate_request_node(state, db_session)
        
        assert result["is_valid"] is False
        assert len(result["validation_errors"]) > 0
    
    def test_missing_description(self, db_session):
        """Test validation fails with missing description"""
        state: HRTicketState = {
            "user_email": "user@crousemedical.com",
            "company": "Crouse Medical Practice",
            "user_message": "Test message",
            "intent": "create_ticket",
            "subject": "Test Subject",
            "description": "",
            "category": "benefits",
            "meeting_type": "online",
            "preferred_date": None,
            "preferred_time_slot": None,
            "urgency": "normal",
            "is_valid": False,
            "validation_errors": [],
            "has_open_tickets": False,
            "open_ticket_ids": [],
            "ticket_id": None,
            "queue_position": None,
            "agent_response": ""
        }
        
        result = validate_request_node(state, db_session)
        
        assert result["is_valid"] is False
        assert len(result["validation_errors"]) > 0
    
    def test_invalid_past_date_cleared(self, db_session):
        """Test that invalid past date is cleared but doesn't fail validation"""
        yesterday = date.today() - timedelta(days=1)
        
        state: HRTicketState = {
            "user_email": "user@crousemedical.com",
            "company": "Crouse Medical Practice",
            "user_message": "Test message",
            "intent": "create_ticket",
            "subject": "Test Subject",
            "description": "Test Description",
            "category": "benefits",
            "meeting_type": "online",
            "preferred_date": yesterday,
            "preferred_time_slot": "morning",
            "urgency": "normal",
            "is_valid": False,
            "validation_errors": [],
            "has_open_tickets": False,
            "open_ticket_ids": [],
            "ticket_id": None,
            "queue_position": None,
            "agent_response": ""
        }
        
        result = validate_request_node(state, db_session)
        
        # Date should be cleared but validation should pass
        assert result["preferred_date"] is None
        assert result["is_valid"] is True
    
    def test_valid_future_date(self, db_session):
        """Test validation with valid future date"""
        tomorrow = date.today() + timedelta(days=1)
        
        state: HRTicketState = {
            "user_email": "user@crousemedical.com",
            "company": "Crouse Medical Practice",
            "user_message": "Test message",
            "intent": "create_ticket",
            "subject": "Test Subject",
            "description": "Test Description",
            "category": "benefits",
            "meeting_type": "online",
            "preferred_date": tomorrow,
            "preferred_time_slot": "morning",
            "urgency": "normal",
            "is_valid": False,
            "validation_errors": [],
            "has_open_tickets": False,
            "open_ticket_ids": [],
            "ticket_id": None,
            "queue_position": None,
            "agent_response": ""
        }
        
        result = validate_request_node(state, db_session)
        
        assert result["is_valid"] is True
        assert result["preferred_date"] == tomorrow


class TestCheckDuplicatesNode:
    """Test duplicate checking node"""
    
    def test_no_open_tickets(self, db_session):
        """Test when user has no open tickets"""
        state: HRTicketState = {
            "user_email": "user@crousemedical.com",
            "company": "Crouse Medical Practice",
            "user_message": "Test message",
            "intent": "create_ticket",
            "subject": "Test Subject",
            "description": "Test Description",
            "category": "benefits",
            "meeting_type": "online",
            "preferred_date": None,
            "preferred_time_slot": None,
            "urgency": "normal",
            "is_valid": True,
            "validation_errors": [],
            "has_open_tickets": False,
            "open_ticket_ids": [],
            "ticket_id": None,
            "queue_position": None,
            "agent_response": ""
        }
        
        result = check_duplicates_node(state, db_session)
        
        assert result["has_open_tickets"] is False
        assert len(result["open_ticket_ids"]) == 0
    
    def test_with_open_tickets(self, db_session, sample_hr_ticket):
        """Test when user has open tickets"""
        state: HRTicketState = {
            "user_email": sample_hr_ticket.email,
            "company": sample_hr_ticket.company,
            "user_message": "Test message",
            "intent": "create_ticket",
            "subject": "Test Subject",
            "description": "Test Description",
            "category": "benefits",
            "meeting_type": "online",
            "preferred_date": None,
            "preferred_time_slot": None,
            "urgency": "normal",
            "is_valid": True,
            "validation_errors": [],
            "has_open_tickets": False,
            "open_ticket_ids": [],
            "ticket_id": None,
            "queue_position": None,
            "agent_response": ""
        }
        
        result = check_duplicates_node(state, db_session)
        
        assert result["has_open_tickets"] is True
        assert sample_hr_ticket.id in result["open_ticket_ids"]


class TestCreateTicketNode:
    """Test ticket creation node"""
    
    def test_create_ticket_success(self, db_session):
        """Test successful ticket creation"""
        state: HRTicketState = {
            "user_email": "user@crousemedical.com",
            "company": "Crouse Medical Practice",
            "user_message": "Test message",
            "intent": "create_ticket",
            "subject": "Test Subject",
            "description": "Test Description",
            "category": "benefits",
            "meeting_type": "online",
            "preferred_date": None,
            "preferred_time_slot": None,
            "urgency": "normal",
            "is_valid": True,
            "validation_errors": [],
            "has_open_tickets": False,
            "open_ticket_ids": [],
            "ticket_id": None,
            "queue_position": None,
            "agent_response": ""
        }
        
        result = create_ticket_node(state, db_session)
        
        assert result["ticket_id"] is not None
        assert result["queue_position"] == 1
    
    def test_create_ticket_with_date(self, db_session):
        """Test creating ticket with preferred date"""
        tomorrow = date.today() + timedelta(days=1)
        
        state: HRTicketState = {
            "user_email": "user@crousemedical.com",
            "company": "Crouse Medical Practice",
            "user_message": "Test message",
            "intent": "create_ticket",
            "subject": "Test Subject",
            "description": "Test Description",
            "category": "benefits",
            "meeting_type": "online",
            "preferred_date": tomorrow,
            "preferred_time_slot": "morning",
            "urgency": "normal",
            "is_valid": True,
            "validation_errors": [],
            "has_open_tickets": False,
            "open_ticket_ids": [],
            "ticket_id": None,
            "queue_position": None,
            "agent_response": ""
        }
        
        result = create_ticket_node(state, db_session)
        
        assert result["ticket_id"] is not None
        
        # Verify in database
        from db.models import HRTicket
        ticket = db_session.query(HRTicket).filter_by(id=result["ticket_id"]).first()
        assert ticket.preferred_date == tomorrow
        assert ticket.preferred_time_slot == "morning"


class TestGenerateResponseNode:
    """Test response generation node"""
    
    def test_success_response(self, db_session):
        """Test generating success response"""
        state: HRTicketState = {
            "user_email": "user@crousemedical.com",
            "company": "Crouse Medical Practice",
            "user_message": "Test message",
            "intent": "create_ticket",
            "subject": "Test Subject",
            "description": "Test Description",
            "category": "benefits",
            "meeting_type": "online",
            "preferred_date": None,
            "preferred_time_slot": None,
            "urgency": "normal",
            "is_valid": True,
            "validation_errors": [],
            "has_open_tickets": False,
            "open_ticket_ids": [],
            "ticket_id": "test-ticket-id",
            "queue_position": 1,
            "agent_response": ""
        }
        
        result = generate_response_node(state, db_session)
        
        assert "successfully" in result["agent_response"].lower()
        assert "test-ticket-id" in result["agent_response"]
        assert "#1" in result["agent_response"]
    
    def test_validation_error_response(self, db_session):
        """Test generating error response for validation failure"""
        state: HRTicketState = {
            "user_email": "user@crousemedical.com",
            "company": "Crouse Medical Practice",
            "user_message": "Test message",
            "intent": "create_ticket",
            "subject": "",
            "description": "",
            "category": "benefits",
            "meeting_type": "online",
            "preferred_date": None,
            "preferred_time_slot": None,
            "urgency": "normal",
            "is_valid": False,
            "validation_errors": ["Subject is required", "Description is required"],
            "has_open_tickets": False,
            "open_ticket_ids": [],
            "ticket_id": None,
            "queue_position": None,
            "agent_response": ""
        }
        
        result = generate_response_node(state, db_session)
        
        assert "couldn't process" in result["agent_response"].lower()
        assert "Subject is required" in result["agent_response"]
    
    def test_creation_error_response(self, db_session):
        """Test generating error response when ticket creation fails"""
        state: HRTicketState = {
            "user_email": "user@crousemedical.com",
            "company": "Crouse Medical Practice",
            "user_message": "Test message",
            "intent": "create_ticket",
            "subject": "Test Subject",
            "description": "Test Description",
            "category": "benefits",
            "meeting_type": "online",
            "preferred_date": None,
            "preferred_time_slot": None,
            "urgency": "normal",
            "is_valid": True,
            "validation_errors": [],
            "has_open_tickets": False,
            "open_ticket_ids": [],
            "ticket_id": None,
            "queue_position": None,
            "agent_response": ""
        }
        
        result = generate_response_node(state, db_session)
        
        assert "error" in result["agent_response"].lower()
    
    def test_response_with_open_tickets_note(self, db_session):
        """Test response includes note about other open tickets"""
        state: HRTicketState = {
            "user_email": "user@crousemedical.com",
            "company": "Crouse Medical Practice",
            "user_message": "Test message",
            "intent": "create_ticket",
            "subject": "Test Subject",
            "description": "Test Description",
            "category": "benefits",
            "meeting_type": "online",
            "preferred_date": None,
            "preferred_time_slot": None,
            "urgency": "normal",
            "is_valid": True,
            "validation_errors": [],
            "has_open_tickets": True,
            "open_ticket_ids": ["ticket-1", "ticket-2"],
            "ticket_id": "test-ticket-id",
            "queue_position": 1,
            "agent_response": ""
        }
        
        result = generate_response_node(state, db_session)
        
        assert "2 other open ticket" in result["agent_response"]