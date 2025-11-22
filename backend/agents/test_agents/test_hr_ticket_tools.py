"""
Tests for HR Ticket Agent tools/utilities
"""
import pytest
from datetime import date, datetime, timedelta
from agents.hr_ticket.tools import (
    check_open_tickets,
    calculate_queue_position,
    create_ticket_in_db,
    get_ticket_by_id,
    get_user_tickets,
    validate_date,
    is_company_admin,
    get_ticket_stats
)
from db.models import HRTicket, TicketStatus, TicketCategory, MeetingType, Urgency, User, UserRole


class TestCheckOpenTickets:
    """Test checking for open tickets"""
    
    def test_no_open_tickets(self, db_session):
        """Test when user has no open tickets"""
        has_open, ticket_ids = check_open_tickets(
            db_session,
            "user@crousemedical.com",
            "Crouse Medical Practice"
        )
        
        assert has_open is False
        assert ticket_ids == []
    
    def test_with_open_tickets(self, db_session, sample_hr_ticket):
        """Test when user has open tickets"""
        has_open, ticket_ids = check_open_tickets(
            db_session,
            sample_hr_ticket.email,
            sample_hr_ticket.company
        )
        
        assert has_open is True
        assert sample_hr_ticket.id in ticket_ids
    
    def test_ignores_closed_tickets(self, db_session, sample_hr_ticket):
        """Test that closed tickets are not counted"""
        sample_hr_ticket.status = TicketStatus.CLOSED
        db_session.commit()
        
        has_open, ticket_ids = check_open_tickets(
            db_session,
            sample_hr_ticket.email,
            sample_hr_ticket.company
        )
        
        assert has_open is False
        assert ticket_ids == []
    
    def test_company_isolation(self, db_session, sample_hr_ticket):
        """Test that tickets from other companies are not returned"""
        has_open, ticket_ids = check_open_tickets(
            db_session,
            sample_hr_ticket.email,
            "Different Company"
        )
        
        assert has_open is False
        assert ticket_ids == []


class TestCalculateQueuePosition:
    """Test queue position calculation"""
    
    def test_first_ticket(self, db_session):
        """Test queue position for first ticket"""
        position = calculate_queue_position(db_session, "Crouse Medical Practice")
        assert position == 1
    
    def test_multiple_pending_tickets(self, db_session, sample_hr_ticket):
        """Test queue position with existing pending tickets"""
        position = calculate_queue_position(db_session, sample_hr_ticket.company)
        assert position == 2
    
    def test_ignores_non_pending_tickets(self, db_session, sample_hr_ticket):
        """Test that only pending tickets count"""
        sample_hr_ticket.status = TicketStatus.IN_PROGRESS
        db_session.commit()
        
        position = calculate_queue_position(db_session, sample_hr_ticket.company)
        assert position == 1


class TestCreateTicketInDb:
    """Test ticket creation"""
    
    def test_create_basic_ticket(self, db_session):
        """Test creating a basic ticket"""
        ticket_id, queue_position = create_ticket_in_db(
            db=db_session,
            email="user@crousemedical.com",
            company="Crouse Medical Practice",
            subject="Test Ticket",
            description="Test Description",
            category="general_inquiry",
            meeting_type="online",
            urgency="normal"
        )
        
        assert ticket_id is not None
        assert queue_position == 1
        
        # Verify ticket exists
        ticket = db_session.query(HRTicket).filter_by(id=ticket_id).first()
        assert ticket is not None
        assert ticket.subject == "Test Ticket"
        assert ticket.status == TicketStatus.PENDING
    
    def test_create_with_preferred_date(self, db_session):
        """Test creating ticket with preferred date"""
        tomorrow = date.today() + timedelta(days=1)
        
        ticket_id, queue_position = create_ticket_in_db(
            db=db_session,
            email="user@crousemedical.com",
            company="Crouse Medical Practice",
            subject="Test Ticket",
            description="Test Description",
            category="benefits",
            meeting_type="in_person",
            urgency="urgent",
            preferred_date=tomorrow,
            preferred_time_slot="morning"
        )
        
        ticket = db_session.query(HRTicket).filter_by(id=ticket_id).first()
        assert ticket.preferred_date == tomorrow
        assert ticket.preferred_time_slot == "morning"
        assert ticket.urgency == Urgency.URGENT


class TestGetTicketById:
    """Test retrieving ticket by ID"""
    
    def test_get_existing_ticket(self, db_session, sample_hr_ticket):
        """Test getting an existing ticket"""
        ticket = get_ticket_by_id(
            db_session,
            sample_hr_ticket.id,
            sample_hr_ticket.company
        )
        
        assert ticket is not None
        assert ticket.id == sample_hr_ticket.id
    
    def test_get_nonexistent_ticket(self, db_session):
        """Test getting a nonexistent ticket"""
        ticket = get_ticket_by_id(
            db_session,
            "nonexistent-id",
            "Crouse Medical Practice"
        )
        
        assert ticket is None
    
    def test_company_isolation(self, db_session, sample_hr_ticket):
        """Test that tickets from other companies are not returned"""
        ticket = get_ticket_by_id(
            db_session,
            sample_hr_ticket.id,
            "Different Company"
        )
        
        assert ticket is None


class TestGetUserTickets:
    """Test retrieving user's tickets"""
    
    def test_get_user_tickets(self, db_session, sample_hr_ticket):
        """Test getting all tickets for a user"""
        tickets = get_user_tickets(
            db_session,
            sample_hr_ticket.email,
            sample_hr_ticket.company
        )
        
        assert len(tickets) == 1
        assert tickets[0].id == sample_hr_ticket.id
    
    def test_empty_ticket_list(self, db_session):
        """Test when user has no tickets"""
        tickets = get_user_tickets(
            db_session,
            "newuser@crousemedical.com",
            "Crouse Medical Practice"
        )
        
        assert len(tickets) == 0
    
    def test_company_isolation(self, db_session, sample_hr_ticket):
        """Test that tickets from other companies are not returned"""
        tickets = get_user_tickets(
            db_session,
            sample_hr_ticket.email,
            "Different Company"
        )
        
        assert len(tickets) == 0


class TestValidateDate:
    """Test date validation"""
    
    def test_valid_future_date(self):
        """Test valid future date"""
        tomorrow = date.today() + timedelta(days=1)
        is_valid, error = validate_date(tomorrow)
        
        assert is_valid is True
        assert error is None
    
    def test_today_is_valid(self):
        """Test that today is valid"""
        is_valid, error = validate_date(date.today())
        
        assert is_valid is True
        assert error is None
    
    def test_past_date_invalid(self):
        """Test that past dates are invalid"""
        yesterday = date.today() - timedelta(days=1)
        is_valid, error = validate_date(yesterday)
        
        assert is_valid is False
        assert "past" in error.lower()
    
    def test_none_date_valid(self):
        """Test that None is valid (optional date)"""
        is_valid, error = validate_date(None)
        
        assert is_valid is True
        assert error is None


class TestIsCompanyAdmin:
    """Test admin role checking"""
    
    def test_company_admin(self, db_session, sample_company_admin):
        """Test that company admin is identified correctly"""
        is_admin = is_company_admin(
            db_session,
            sample_company_admin.email,
            sample_company_admin.company
        )
        
        assert is_admin is True
    
    def test_regular_user(self, db_session, sample_user):
        """Test that regular user is not identified as admin"""
        is_admin = is_company_admin(
            db_session,
            sample_user.email,
            sample_user.company
        )
        
        assert is_admin is False
    
    def test_admin_different_company(self, db_session, sample_company_admin):
        """Test that admin from different company returns False"""
        is_admin = is_company_admin(
            db_session,
            sample_company_admin.email,
            "Different Company"
        )
        
        assert is_admin is False
    
    def test_nonexistent_user(self, db_session):
        """Test with nonexistent user"""
        is_admin = is_company_admin(
            db_session,
            "nonexistent@example.com",
            "Crouse Medical Practice"
        )
        
        assert is_admin is False


class TestGetTicketStats:
    """Test ticket statistics"""
    
    def test_empty_stats(self, db_session):
        """Test stats when no tickets exist"""
        stats = get_ticket_stats(db_session, "Crouse Medical Practice")
        
        assert stats["total_pending"] == 0
        assert stats["total_in_progress"] == 0
        assert stats["total_scheduled"] == 0
        assert stats["total_resolved_today"] == 0
        assert stats["total_closed_today"] == 0
        assert stats["average_resolution_time_hours"] is None
    
    def test_stats_with_tickets(self, db_session, sample_hr_ticket):
        """Test stats with existing tickets"""
        stats = get_ticket_stats(db_session, sample_hr_ticket.company)
        
        assert stats["total_pending"] == 1
        assert stats["total_in_progress"] == 0
        # Check that by_category has at least one entry
        assert len(stats["by_category"]) > 0
        # The key might be "TicketCategory.BENEFITS" or "benefits" depending on str() output
        assert any("benefits" in str(key).lower() for key in stats["by_category"].keys())
        assert "normal" in stats["by_urgency"] or any("normal" in str(key).lower() for key in stats["by_urgency"].keys())
    
    def test_stats_resolution_time(self, db_session, sample_hr_ticket):
        """Test average resolution time calculation"""
        # Resolve ticket
        sample_hr_ticket.status = TicketStatus.RESOLVED
        sample_hr_ticket.resolved_at = datetime.utcnow()
        db_session.commit()
        
        stats = get_ticket_stats(db_session, sample_hr_ticket.company)
        
        assert stats["average_resolution_time_hours"] is not None
        assert stats["average_resolution_time_hours"] >= 0
    
    def test_company_isolation(self, db_session, sample_hr_ticket):
        """Test that stats are company-specific"""
        stats = get_ticket_stats(db_session, "Different Company")
        
        assert stats["total_pending"] == 0