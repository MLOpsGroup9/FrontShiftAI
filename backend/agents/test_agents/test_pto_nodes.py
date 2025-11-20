"""
Tests for PTO agent nodes
"""
import pytest
from datetime import date
from agents.pto.nodes import (
    validate_dates_node,
    check_balance_node,
    check_conflicts_node,
    create_request_node
)
from agents.pto.state import PTOAgentState

def test_validate_dates_valid(db_session, sample_company, sample_holidays):
    """Test date validation with valid dates"""
    state = PTOAgentState(
        user_email="test@test.com",
        company=sample_company.name,
        user_message="test",
        start_date=date(2025, 12, 1),
        end_date=date(2025, 12, 5),
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

def test_validate_dates_past_dates(db_session, sample_company):
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

def test_check_balance_sufficient(db_session, sample_pto_balance):
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

def test_check_balance_insufficient(db_session, sample_pto_balance):
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