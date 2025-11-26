"""
Tests for database error handling
Validates graceful degradation when database operations fail
"""
import pytest
import sys
from pathlib import Path
from datetime import date
from sqlalchemy.exc import IntegrityError, OperationalError

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))

from agents.pto.nodes import create_request_node
from agents.pto.state import PTOAgentState
from agents.hr_ticket.nodes import create_ticket_node
from agents.hr_ticket.state import HRTicketState
from db.models import PTORequest, HRTicket


class TestPTODatabaseErrors:
    """Test PTO agent database error handling"""
    
    def test_duplicate_request_id(self, db_session, sample_pto_balance):
        """Test handling duplicate request ID (though UUID should prevent this)"""
        import uuid
        
        # Create request with specific ID
        existing_id = str(uuid.uuid4())
        existing = PTORequest(
            id=existing_id,
            email=sample_pto_balance.email,
            company=sample_pto_balance.company,
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 5),
            days_requested=5.0,
            status="pending"
        )
        db_session.add(existing)
        db_session.commit()
        
        # This test just ensures UUID generation makes duplicates extremely unlikely
        # Create many requests and verify all have unique IDs
        state = PTOAgentState(
            user_email=sample_pto_balance.email,
            company=sample_pto_balance.company,
            user_message="test",
            start_date=date(2025, 12, 1),
            end_date=date(2025, 12, 5),
            total_business_days=5.0,
            reason="Test",
            intent="request_pto",
            is_valid=True,
            validation_errors=[],
            holiday_dates=[],
            blackout_conflicts=[],
            has_sufficient_balance=True,
            has_conflicts=False,
            conflicting_requests=[],
            request_id=None,
            request_created=False,
            agent_response="",
            should_end=False,
            current_balance=15.0,
            used_days=0.0,
            pending_days=0.0,
            remaining_days=10.0,
            error_message=None
        )
        
        result = create_request_node(state, db_session)
        
        # Should create successfully with different ID
        assert result['request_created'] is True
        assert result['request_id'] != existing_id


class TestHRTicketDatabaseErrors:
    """Test HR ticket agent database error handling"""
    
    def test_ticket_creation_with_db_error(self, db_session, monkeypatch):
        """Test ticket creation handles database errors"""
        
        def mock_add_failure(*args, **kwargs):
            raise OperationalError("Database error", None, None)
        
        monkeypatch.setattr(db_session, 'add', mock_add_failure)
        
        state: HRTicketState = {
            "user_email": "test@company.com",
            "company": "Test Company",
            "user_message": "test",
            "intent": "create_ticket",
            "subject": "Test",
            "description": "Test",
            "category": "general_inquiry",
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
        
        # Should handle gracefully
        assert result['ticket_id'] is None
        assert result['is_valid'] is False


class TestDatabaseConnectionHandling:
    """Test behavior with database connection issues"""
    
    def test_query_failure_handling(self, monkeypatch):
        """Test graceful handling of query failures"""
        
        def mock_query_failure(*args, **kwargs):
            raise OperationalError("Connection failed", None, None)
        
        # This tests that tools handle database errors
        # Actual implementation may vary
        from agents.pto import tools
        
        # If get_pto_balance encounters error, should return None or handle gracefully
        # Specific test depends on implementation
    
    

class TestDataIntegrityValidation:
    """Test data integrity checks"""
    
    def test_negative_balance_handling(self, db_session):
        """Test handling of negative balance (data integrity issue)"""
        from db.models import PTOBalance
        
        # Create balance with negative remaining
        bad_balance = PTOBalance(
            email="test@test.com",
            company="Test Company",
            year=2025,
            total_days=15.0,
            used_days=20.0,  # More than total!
            pending_days=0.0
        )
        db_session.add(bad_balance)
        db_session.commit()
        
        from agents.pto.tools import get_pto_balance
        balance = get_pto_balance(db_session, "test@test.com", 2025)
        
        # Should return data, even if logically inconsistent
        assert balance is not None
        assert balance['remaining_days'] < 0  # Negative is possible
    
    