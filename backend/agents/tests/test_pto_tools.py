"""
Tests for PTO agent tools
"""
import pytest
from datetime import date, timedelta
from agents.pto.tools import (
    calculate_business_days,
    get_company_holidays,
    check_blackout_periods,
    get_pto_balance,
    check_conflicting_requests
)

def test_calculate_business_days_no_holidays():
    """Test business days calculation without holidays"""
    start = date(2025, 12, 1)  # Monday
    end = date(2025, 12, 5)    # Friday
    holidays = []
    
    result = calculate_business_days(start, end, holidays)
    assert result == 5.0

def test_calculate_business_days_with_weekend():
    """Test business days calculation excluding weekends"""
    start = date(2025, 12, 1)  # Monday
    end = date(2025, 12, 7)    # Sunday
    holidays = []
    
    result = calculate_business_days(start, end, holidays)
    assert result == 5.0  # Mon-Fri only

def test_calculate_business_days_with_holidays():
    """Test business days calculation with holidays"""
    start = date(2025, 12, 24)  # Wednesday
    end = date(2025, 12, 26)    # Friday
    holidays = [date(2025, 12, 25)]  # Christmas
    
    result = calculate_business_days(start, end, holidays)
    assert result == 2.0  # Wed and Fri only

def test_get_company_holidays(db_session, sample_company, sample_holidays):
    """Test fetching company holidays"""
    holidays = get_company_holidays(db_session, sample_company.name, 2025)
    
    assert len(holidays) == 2
    assert date(2025, 12, 25) in holidays
    assert date(2025, 1, 1) in holidays

def test_get_pto_balance(db_session, sample_pto_balance):
    """Test fetching PTO balance"""
    balance = get_pto_balance(db_session, sample_pto_balance.email, 2025)
    
    assert balance is not None
    assert balance['total_days'] == 15.0
    assert balance['used_days'] == 0.0
    assert balance['remaining_days'] == 15.0

def test_get_pto_balance_nonexistent(db_session):
    """Test fetching non-existent PTO balance"""
    balance = get_pto_balance(db_session, "nonexistent@test.com", 2025)
    assert balance is None

def test_check_conflicting_requests_no_conflicts(db_session, sample_user):
    """Test checking for conflicts when none exist"""
    start = date(2025, 12, 1)
    end = date(2025, 12, 5)
    
    has_conflicts, conflicts = check_conflicting_requests(
        db_session, sample_user.email, start, end
    )
    
    assert has_conflicts is False
    assert len(conflicts) == 0

def test_check_conflicting_requests_with_conflicts(db_session, sample_user):
    """Test checking for conflicts when they exist"""
    from db.models import PTORequest, PTOStatus
    
    # Create existing request
    existing_request = PTORequest(
        id="req-1",
        email=sample_user.email,
        company=sample_user.company,
        start_date=date(2025, 12, 3),
        end_date=date(2025, 12, 5),
        days_requested=3.0,
        status=PTOStatus.APPROVED
    )
    db_session.add(existing_request)
    db_session.commit()
    
    # Check for conflicts with overlapping dates
    start = date(2025, 12, 1)
    end = date(2025, 12, 4)
    
    has_conflicts, conflicts = check_conflicting_requests(
        db_session, sample_user.email, start, end
    )
    
    assert has_conflicts is True
    assert len(conflicts) == 1
    assert conflicts[0]['id'] == "req-1"