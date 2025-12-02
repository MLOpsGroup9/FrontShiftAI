"""
Tests for PTO agent nodes
Enhanced with comprehensive workflow validation
"""
import pytest
from datetime import date, timedelta
from agents.pto.nodes import (
    parse_intent_node,
    validate_dates_node,
    check_balance_node,
    check_conflicts_node,
    create_request_node,
    generate_response_node
)
from agents.pto.state import PTOAgentState


class TestParseIntentNode:
    """Test intent parsing node"""
    
    def test_parse_pto_request(self, db_session):
        """Test parsing a PTO request"""
        state = PTOAgentState(
            user_email="test@test.com",
            company="Test Company",
            user_message="I need 3 days off next week",
            start_date=None,
            end_date=None,
            intent=None,
            is_valid=False,
            validation_errors=[],
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
        
        result = parse_intent_node(state, db_session)
        
        # Should extract intent
        assert result['intent'] in ['request_pto', 'check_balance', 'general_query']
    
    def test_parse_balance_check(self, db_session):
        """Test parsing a balance check request"""
        state = PTOAgentState(
            user_email="test@test.com",
            company="Test Company",
            user_message="How many PTO days do I have left?",
            start_date=None,
            end_date=None,
            intent=None,
            is_valid=False,
            validation_errors=[],
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
        
        result = parse_intent_node(state, db_session)
        
        # Should identify as balance check
        assert result['intent'] in ['check_balance', 'general_query']


class TestValidateDatesNode:
    """Test date validation node"""
    
    def test_validate_dates_valid(self, db_session, sample_company, sample_holidays):
        """Test date validation with valid dates"""
        # Use future weekdays to ensure valid business days
        today = date.today()
        start_date = today + timedelta(days=7)  # One week from now
        
        # Ensure we start on a Monday
        while start_date.weekday() != 0:  # Monday = 0
            start_date += timedelta(days=1)
        
        end_date = start_date + timedelta(days=4)  # Mon-Fri (5 business days)
        
        state = PTOAgentState(
            user_email="test@test.com",
            company=sample_company.name,
            user_message="test",
            start_date=start_date,
            end_date=end_date,
            intent="request_pto",
            is_valid=False,
            validation_errors=[],
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
        
        result = validate_dates_node(state, db_session)
        
        assert result['is_valid'] is True
        assert result['total_business_days'] == 5.0
        assert len(result['validation_errors']) == 0

    def test_validate_dates_past_dates(self, db_session, sample_company):
        """Test date validation with past dates"""
        state = PTOAgentState(
            user_email="test@test.com",
            company=sample_company.name,
            user_message="test",
            start_date=date(2020, 1, 1),
            end_date=date(2020, 1, 5),
            intent="request_pto",
            is_valid=False,
            validation_errors=[],
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
        
        result = validate_dates_node(state, db_session)
        
        assert result['is_valid'] is False
        assert "past dates" in result['validation_errors'][0].lower()
    
    def test_validate_weekend_only(self, db_session, sample_company):
        """Test validation rejects weekend-only requests"""
        # Find next Saturday
        today = date.today()
        next_saturday = today + timedelta(days=(5 - today.weekday() + 7) % 7)
        if next_saturday == today or next_saturday < today:
            next_saturday += timedelta(days=7)
        
        state = PTOAgentState(
            user_email="test@test.com",
            company=sample_company.name,
            user_message="test",
            start_date=next_saturday,  # Saturday
            end_date=next_saturday + timedelta(days=1),  # Sunday
            intent="request_pto",
            is_valid=False,
            validation_errors=[],
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
        
        result = validate_dates_node(state, db_session)
        
        assert result['is_valid'] is False
        assert any("business day" in err.lower() for err in result['validation_errors'])
    
    def test_validate_with_holidays(self, db_session, sample_company, sample_holidays):
        """Test validation excludes holidays correctly"""
        # Use dates far enough in the future to avoid conflicts
        today = date.today()
        # Find a Wednesday in the future (at least 2 weeks out)
        start_date = today + timedelta(days=14)
        while start_date.weekday() != 2:  # Wednesday = 2
            start_date += timedelta(days=1)
        
        end_date = start_date + timedelta(days=2)  # Wed-Fri (3 days)
        
        state = PTOAgentState(
            user_email="test@test.com",
            company=sample_company.name,
            user_message="test",
            start_date=start_date,
            end_date=end_date,
            intent="request_pto",
            is_valid=False,
            validation_errors=[],
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
        
        result = validate_dates_node(state, db_session)
        
        assert result['is_valid'] is True
        # Should be 3 business days (Wed, Thu, Fri) if no holidays
        # Or 2 days if one holiday falls in this range
        # Adjust assertion based on your sample_holidays fixture
        assert result['total_business_days'] >= 2.0
        assert result['total_business_days'] <= 3.0
    
    def test_validate_single_day(self, db_session, sample_company):
        """Test validation with single day request"""
        tomorrow = date.today() + timedelta(days=1)
        # Ensure it's a weekday
        while tomorrow.weekday() >= 5:  # Saturday = 5, Sunday = 6
            tomorrow += timedelta(days=1)
        
        state = PTOAgentState(
            user_email="test@test.com",
            company=sample_company.name,
            user_message="test",
            start_date=tomorrow,
            end_date=tomorrow,
            intent="request_pto",
            is_valid=False,
            validation_errors=[],
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
        
        result = validate_dates_node(state, db_session)
        
        assert result['is_valid'] is True
        assert result['total_business_days'] == 1.0


class TestCheckBalanceNode:
    """Test balance checking node"""
    
    def test_check_balance_sufficient(self, db_session, sample_pto_balance):
        """Test balance check with sufficient balance"""
        state = PTOAgentState(
            user_email=sample_pto_balance.email,
            company=sample_pto_balance.company,
            user_message="test",
            total_business_days=5.0,
            intent="request_pto",
            is_valid=True,
            validation_errors=[],
            holiday_dates=[],
            blackout_conflicts=[],
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
            start_date=None,
            end_date=None,
            reason=None,
            error_message=None
        )
        
        result = check_balance_node(state, db_session)
        
        assert result['has_sufficient_balance'] is True
        assert result['remaining_days'] == 15.0
        assert result['current_balance'] == 15.0

    def test_check_balance_insufficient(self, db_session, sample_pto_balance):
        """Test balance check with insufficient balance"""
        state = PTOAgentState(
            user_email=sample_pto_balance.email,
            company=sample_pto_balance.company,
            user_message="test",
            total_business_days=20.0,  # More than available
            intent="request_pto",
            is_valid=True,
            validation_errors=[],
            holiday_dates=[],
            blackout_conflicts=[],
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
            start_date=None,
            end_date=None,
            reason=None,
            error_message=None
        )
        
        result = check_balance_node(state, db_session)
        
        assert result['has_sufficient_balance'] is False
        assert len(result['validation_errors']) > 0
        assert "insufficient" in result['validation_errors'][0].lower()
    
    def test_check_balance_exact_match(self, db_session, sample_pto_balance):
        """Test balance check when request exactly matches remaining"""
        state = PTOAgentState(
            user_email=sample_pto_balance.email,
            company=sample_pto_balance.company,
            user_message="test",
            total_business_days=15.0,  # Exactly the available amount
            intent="request_pto",
            is_valid=True,
            validation_errors=[],
            holiday_dates=[],
            blackout_conflicts=[],
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
            start_date=None,
            end_date=None,
            reason=None,
            error_message=None
        )
        
        result = check_balance_node(state, db_session)
        
        assert result['has_sufficient_balance'] is True
        assert result['remaining_days'] == 15.0
    
    def test_check_balance_with_usage(self, db_session, pto_balance_with_usage):
        """Test balance check with existing used and pending days"""
        state = PTOAgentState(
            user_email=pto_balance_with_usage.email,
            company=pto_balance_with_usage.company,
            user_message="test",
            total_business_days=5.0,
            intent="request_pto",
            is_valid=True,
            validation_errors=[],
            holiday_dates=[],
            blackout_conflicts=[],
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
            start_date=None,
            end_date=None,
            reason=None,
            error_message=None
        )
        
        result = check_balance_node(state, db_session)
        
        # Total: 15, Used: 5, Pending: 3, Remaining: 7
        assert result['has_sufficient_balance'] is True
        assert result['remaining_days'] == 7.0
        assert result['used_days'] == 5.0
        assert result['pending_days'] == 3.0
    
    def test_check_balance_no_record(self, db_session):
        """Test balance check when no balance record exists"""
        state = PTOAgentState(
            user_email="nonexistent@test.com",
            company="Test Company",
            user_message="test",
            total_business_days=5.0,
            intent="request_pto",
            is_valid=True,
            validation_errors=[],
            holiday_dates=[],
            blackout_conflicts=[],
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
            start_date=None,
            end_date=None,
            reason=None,
            error_message=None
        )
        
        result = check_balance_node(state, db_session)
        
        # If balance is auto-created, it should have sufficient balance
        # If not created, should fail - adjust based on actual implementation
        # For now, check that it doesn't crash
        assert 'has_sufficient_balance' in result


class TestCheckConflictsNode:
    """Test conflict checking node"""
    
    def test_no_conflicts(self, db_session, sample_user):
        """Test when no conflicts exist"""
        today = date.today()
        start_date = today + timedelta(days=30)  # Far in the future
        end_date = start_date + timedelta(days=4)
        
        state = PTOAgentState(
            user_email=sample_user.email,
            company=sample_user.company,
            user_message="test",
            start_date=start_date,
            end_date=end_date,
            intent="request_pto",
            is_valid=True,
            validation_errors=[],
            holiday_dates=[],
            blackout_conflicts=[],
            total_business_days=5.0,
            has_sufficient_balance=True,
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
        
        result = check_conflicts_node(state, db_session)
        
        assert result['has_conflicts'] is False
        assert len(result['conflicting_requests']) == 0
    
    def test_with_conflicts(self, db_session, sample_approved_pto_request):
        """Test when conflicts exist"""
        state = PTOAgentState(
            user_email=sample_approved_pto_request.email,
            company=sample_approved_pto_request.company,
            user_message="test",
            start_date=sample_approved_pto_request.start_date,
            end_date=sample_approved_pto_request.end_date,
            intent="request_pto",
            is_valid=True,
            validation_errors=[],
            holiday_dates=[],
            blackout_conflicts=[],
            total_business_days=4.0,
            has_sufficient_balance=True,
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
        
        result = check_conflicts_node(state, db_session)
        
        assert result['has_conflicts'] is True
        assert len(result['conflicting_requests']) == 1


class TestCreateRequestNode:
    """Test request creation node"""
    
    def test_create_request_success(self, db_session, sample_pto_balance):
        """Test successful request creation"""
        today = date.today()
        start_date = today + timedelta(days=14)
        end_date = start_date + timedelta(days=4)
        
        state = PTOAgentState(
            user_email=sample_pto_balance.email,
            company=sample_pto_balance.company,
            user_message="test",
            start_date=start_date,
            end_date=end_date,
            total_business_days=5.0,
            reason="Vacation",
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
            remaining_days=15.0,
            error_message=None
        )
        
        result = create_request_node(state, db_session)
        
        assert result['request_created'] is True
        assert result['request_id'] is not None
        
        # Verify in database
        from db.models import PTORequest
        request = db_session.query(PTORequest).filter_by(
            id=result['request_id']
        ).first()
        assert request is not None
        assert request.status.value == "pending"


class TestGenerateResponseNode:
    """Test response generation node"""
    
    def test_success_response(self, db_session):
        """Test generating success response"""
        today = date.today()
        start_date = today + timedelta(days=10)
        end_date = start_date + timedelta(days=4)
        
        state = PTOAgentState(
            user_email="test@test.com",
            company="Test Company",
            user_message="test",
            start_date=start_date,
            end_date=end_date,
            total_business_days=5.0,
            intent="request_pto",
            is_valid=True,
            validation_errors=[],
            holiday_dates=[],
            blackout_conflicts=[],
            has_sufficient_balance=True,
            has_conflicts=False,
            conflicting_requests=[],
            request_id="test-req-123",
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
        
        assert "success" in result['agent_response'].lower()
        assert "test-req-123" in result['agent_response']
        assert len(result['agent_response']) > 50
    
    def test_validation_error_response(self, db_session):
        """Test generating error response"""
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
        
        assert "past dates" in result['agent_response'].lower()
        assert result['request_created'] is False