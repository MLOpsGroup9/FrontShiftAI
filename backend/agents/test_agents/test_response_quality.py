"""
Tests for response quality and completeness
Validates that agent responses contain required information
"""
import pytest
import sys
from pathlib import Path
from datetime import date

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))

from agents.pto.nodes import generate_response_node
from agents.pto.state import PTOAgentState
from agents.hr_ticket.nodes import generate_response_node as hr_generate_response
from agents.hr_ticket.state import HRTicketState


class TestPTOSuccessResponseCompleteness:
    """Test PTO success responses contain all required fields"""
    
    def test_success_response_has_request_id(self, db_session):
        """Test success response includes request ID"""
        state = PTOAgentState(
            user_email="test@test.com",
            company="Test Company",
            user_message="test",
            start_date=date(2025, 12, 1),
            end_date=date(2025, 12, 5),
            total_business_days=5.0,
            intent="request_pto",
            is_valid=True,
            validation_errors=[],
            holiday_dates=[],
            blackout_conflicts=[],
            has_sufficient_balance=True,
            has_conflicts=False,
            conflicting_requests=[],
            request_id="req-abc-123",
            request_created=True,
            agent_response="",
            should_end=False,
            current_balance=15.0,
            used_days=0.0,
            pending_days=0.0,
            remaining_days=10.0,
            reason=None,
            error_message=None
        )
        
        result = generate_response_node(state, db_session)
        
        assert "req-abc-123" in result['agent_response']
    
    def test_success_response_has_dates(self, db_session):
        """Test success response includes dates"""
        state = PTOAgentState(
            user_email="test@test.com",
            company="Test Company",
            user_message="test",
            start_date=date(2025, 12, 24),
            end_date=date(2025, 12, 26),
            total_business_days=3.0,
            intent="request_pto",
            is_valid=True,
            validation_errors=[],
            holiday_dates=[],
            blackout_conflicts=[],
            has_sufficient_balance=True,
            has_conflicts=False,
            conflicting_requests=[],
            request_id="req-123",
            request_created=True,
            agent_response="",
            should_end=False,
            current_balance=15.0,
            used_days=0.0,
            pending_days=0.0,
            remaining_days=12.0,
            reason=None,
            error_message=None
        )
        
        result = generate_response_node(state, db_session)
        
        # Should mention dates or December
        assert any(word in result['agent_response'] for word in ['December', '24', '26', 'Dates'])
    
    def test_success_response_has_status(self, db_session):
        """Test success response includes status"""
        state = PTOAgentState(
            user_email="test@test.com",
            company="Test Company",
            user_message="test",
            start_date=date(2025, 12, 1),
            end_date=date(2025, 12, 5),
            total_business_days=5.0,
            intent="request_pto",
            is_valid=True,
            validation_errors=[],
            holiday_dates=[],
            blackout_conflicts=[],
            has_sufficient_balance=True,
            has_conflicts=False,
            conflicting_requests=[],
            request_id="req-123",
            request_created=True,
            agent_response="",
            should_end=False,
            current_balance=15.0,
            used_days=0.0,
            pending_days=0.0,
            remaining_days=10.0,
            reason=None,
            error_message=None
        )
        
        result = generate_response_node(state, db_session)
        
        # Should mention pending or status
        assert any(word in result['agent_response'].lower() for word in ['pending', 'status', 'approval'])


class TestPTOErrorResponseQuality:
    """Test PTO error responses are specific and helpful"""
    
    def test_error_response_is_specific(self, db_session):
        """Test error messages are specific, not generic"""
        state = PTOAgentState(
            user_email="test@test.com",
            company="Test Company",
            user_message="test",
            start_date=date(2020, 1, 1),
            end_date=date(2020, 1, 5),
            intent="request_pto",
            is_valid=False,
            validation_errors=["Cannot request PTO for past dates"],
            holiday_dates=[],
            blackout_conflicts=[],
            total_business_days=None,
            has_sufficient_balance=False,
            has_conflicts=False,
            conflicting_requests=[],
            request_id=None,
            request_created=False,
            agent_response="",
            should_end=False,
            current_balance=None,
            used_days=None,
            pending_days=None,
            remaining_days=None,
            reason=None,
            error_message=None
        )
        
        result = generate_response_node(state, db_session)
        
        # Should include the specific error, not generic "error occurred"
        assert "past dates" in result['agent_response'].lower()
        assert "error occurred" not in result['agent_response'].lower()
    
    def test_insufficient_balance_shows_numbers(self, db_session):
        """Test insufficient balance error shows actual numbers"""
        state = PTOAgentState(
            user_email="test@test.com",
            company="Test Company",
            user_message="test",
            start_date=date(2025, 12, 1),
            end_date=date(2025, 12, 20),
            total_business_days=15.0,
            intent="request_pto",
            is_valid=True,
            validation_errors=["Insufficient balance. Requested: 15.0 days, Available: 10.0 days"],
            holiday_dates=[],
            blackout_conflicts=[],
            has_sufficient_balance=False,
            has_conflicts=False,
            conflicting_requests=[],
            request_id=None,
            request_created=False,
            agent_response="",
            should_end=False,
            current_balance=15.0,
            used_days=5.0,
            pending_days=0.0,
            remaining_days=10.0,
            reason=None,
            error_message=None
        )
        
        result = generate_response_node(state, db_session)
        
        # Should show requested and available
        assert any(num in result['agent_response'] for num in ['15', '10'])


class TestHRTicketResponseCompleteness:
    """Test HR ticket responses contain required information"""
    
    def test_success_has_ticket_id(self, db_session):
        """Test success response includes ticket ID"""
        state: HRTicketState = {
            "user_email": "test@company.com",
            "company": "Test Company",
            "user_message": "test",
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
            "ticket_id": "ticket-xyz-789",
            "queue_position": 5,
            "agent_response": ""
        }
        
        result = hr_generate_response(state, db_session)
        
        assert "ticket-xyz-789" in result['agent_response']
    
    def test_success_has_queue_position(self, db_session):
        """Test success response includes queue position"""
        state: HRTicketState = {
            "user_email": "test@company.com",
            "company": "Test Company",
            "user_message": "test",
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
            "ticket_id": "ticket-123",
            "queue_position": 3,
            "agent_response": ""
        }
        
        result = hr_generate_response(state, db_session)
        
        # Should mention queue position
        assert "#3" in result['agent_response'] or "3" in result['agent_response']
    
    def test_error_response_lists_all_errors(self, db_session):
        """Test error responses list all validation errors"""
        state: HRTicketState = {
            "user_email": "test@company.com",
            "company": "Test Company",
            "user_message": "test",
            "intent": "create_ticket",
            "subject": "",
            "description": "",
            "category": "benefits",
            "meeting_type": "online",
            "preferred_date": None,
            "preferred_time_slot": None,
            "urgency": "normal",
            "is_valid": False,
            "validation_errors": [
                "Subject is required",
                "Description is required"
            ],
            "has_open_tickets": False,
            "open_ticket_ids": [],
            "ticket_id": None,
            "queue_position": None,
            "agent_response": ""
        }
        
        result = hr_generate_response(state, db_session)
        
        # Should include both errors
        assert "Subject is required" in result['agent_response']
        assert "Description is required" in result['agent_response']


class TestResponseLength:
    """Test response length is appropriate"""
    
    def test_success_response_not_too_short(self, db_session):
        """Test success responses have minimum length"""
        state = PTOAgentState(
            user_email="test@test.com",
            company="Test Company",
            user_message="test",
            start_date=date(2025, 12, 1),
            end_date=date(2025, 12, 5),
            total_business_days=5.0,
            intent="request_pto",
            is_valid=True,
            validation_errors=[],
            holiday_dates=[],
            blackout_conflicts=[],
            has_sufficient_balance=True,
            has_conflicts=False,
            conflicting_requests=[],
            request_id="req-123",
            request_created=True,
            agent_response="",
            should_end=False,
            current_balance=15.0,
            used_days=0.0,
            pending_days=0.0,
            remaining_days=10.0,
            reason=None,
            error_message=None
        )
        
        result = generate_response_node(state, db_session)
        
        # Should be at least 50 characters
        assert len(result['agent_response']) >= 50
    
    def test_error_response_not_too_short(self, db_session):
        """Test error responses have minimum length"""
        state = PTOAgentState(
            user_email="test@test.com",
            company="Test Company",
            user_message="test",
            start_date=date(2020, 1, 1),
            end_date=date(2020, 1, 5),
            intent="request_pto",
            is_valid=False,
            validation_errors=["Cannot request PTO for past dates"],
            holiday_dates=[],
            blackout_conflicts=[],
            total_business_days=None,
            has_sufficient_balance=False,
            has_conflicts=False,
            conflicting_requests=[],
            request_id=None,
            request_created=False,
            agent_response="",
            should_end=False,
            current_balance=None,
            used_days=None,
            pending_days=None,
            remaining_days=None,
            reason=None,
            error_message=None
        )
        
        result = generate_response_node(state, db_session)
        
        # Error message should be informative, not just "Error"
        assert len(result['agent_response']) >= 30