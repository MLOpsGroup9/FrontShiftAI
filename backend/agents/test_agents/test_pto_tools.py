"""
Tests for PTO agent tools
Enhanced with edge cases and comprehensive validation
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


class TestCalculateBusinessDays:
    """Test business days calculation"""
    
    def test_calculate_business_days_no_holidays(self):
        """Test business days calculation without holidays"""
        start = date(2025, 12, 1)  # Monday
        end = date(2025, 12, 5)    # Friday
        holidays = []
        
        result = calculate_business_days(start, end, holidays)
        assert result == 5.0
    
    def test_calculate_business_days_with_weekend(self):
        """Test business days calculation excluding weekends"""
        start = date(2025, 12, 1)  # Monday
        end = date(2025, 12, 7)    # Sunday
        holidays = []
        
        result = calculate_business_days(start, end, holidays)
        assert result == 5.0  # Mon-Fri only
    
    def test_calculate_business_days_with_holidays(self):
        """Test business days calculation with holidays"""
        start = date(2025, 12, 24)  # Wednesday
        end = date(2025, 12, 26)    # Friday
        holidays = [date(2025, 12, 25)]  # Christmas
        
        result = calculate_business_days(start, end, holidays)
        assert result == 2.0  # Wed and Fri only
    
    def test_weekend_only_request(self):
        """Test that weekend-only requests return zero"""
        start = date(2025, 12, 6)   # Saturday
        end = date(2025, 12, 7)     # Sunday
        holidays = []
        
        result = calculate_business_days(start, end, holidays)
        assert result == 0.0
    
    def test_single_day_request(self):
        """Test single business day request"""
        start = date(2025, 12, 1)  # Monday
        end = date(2025, 12, 1)    # Same Monday
        holidays = []
        
        result = calculate_business_days(start, end, holidays)
        assert result == 1.0
    
    def test_multiple_weeks_span(self):
        """Test calculation spanning multiple weeks"""
        start = date(2025, 12, 1)   # Monday
        end = date(2025, 12, 12)    # Friday (almost 2 weeks)
        holidays = []
        
        result = calculate_business_days(start, end, holidays)
        assert result == 10.0  # 2 full work weeks
    
    def test_all_holidays(self):
        """Test when all days are holidays"""
        start = date(2025, 12, 24)  # Wednesday
        end = date(2025, 12, 26)    # Friday
        holidays = [
            date(2025, 12, 24),
            date(2025, 12, 25),
            date(2025, 12, 26)
        ]
        
        result = calculate_business_days(start, end, holidays)
        assert result == 0.0
    
    def test_end_before_start(self):
        """Test invalid date range (end before start)"""
        start = date(2025, 12, 5)
        end = date(2025, 12, 1)
        holidays = []
        
        result = calculate_business_days(start, end, holidays)
        assert result == 0.0


class TestGetCompanyHolidays:
    """Test fetching company holidays"""
    
    def test_get_company_holidays(self, db_session, sample_company, sample_holidays):
        """Test fetching company holidays"""
        holidays = get_company_holidays(db_session, sample_company.name, 2025)
        
        assert len(holidays) == 2
        assert date(2025, 12, 25) in holidays
        assert date(2025, 1, 1) in holidays
    
    def test_get_holidays_nonexistent_company(self, db_session):
        """Test fetching holidays for non-existent company"""
        holidays = get_company_holidays(db_session, "Nonexistent Company", 2025)
        
        assert len(holidays) == 0
    
    def test_get_holidays_different_year(self, db_session, sample_company, sample_holidays):
        """Test fetching holidays for different year"""
        holidays = get_company_holidays(db_session, sample_company.name, 2024)
        
        # Should return empty since our fixtures are for 2025
        assert len(holidays) == 0


class TestGetPTOBalance:
    """Test fetching PTO balance"""
    
    def test_get_pto_balance(self, db_session, sample_pto_balance):
        """Test fetching PTO balance"""
        balance = get_pto_balance(db_session, sample_pto_balance.email, 2025)
        
        assert balance is not None
        assert balance['total_days'] == 15.0
        assert balance['used_days'] == 0.0
        assert balance['remaining_days'] == 15.0
    
    def test_get_pto_balance_nonexistent(self, db_session):
        """Test fetching non-existent PTO balance"""
        balance = get_pto_balance(db_session, "nonexistent@test.com", 2025)
        
        assert balance is None
    
    def test_balance_with_usage(self, db_session, pto_balance_with_usage):
        """Test balance calculation with used and pending days"""
        balance = get_pto_balance(db_session, pto_balance_with_usage.email, 2025)
        
        assert balance is not None
        assert balance['total_days'] == 15.0
        assert balance['used_days'] == 5.0
        assert balance['pending_days'] == 3.0
        assert balance['remaining_days'] == 7.0  # 15 - 5 - 3
    
    def test_balance_different_year(self, db_session, sample_pto_balance):
        """Test fetching balance for different year"""
        balance = get_pto_balance(db_session, sample_pto_balance.email, 2024)
        
        assert balance is None


class TestCheckConflictingRequests:
    """Test conflict detection"""
    
    def test_check_conflicting_requests_no_conflicts(self, db_session, sample_user):
        """Test checking for conflicts when none exist"""
        start = date(2025, 12, 1)
        end = date(2025, 12, 5)
        
        has_conflicts, conflicts = check_conflicting_requests(
            db_session, sample_user.email, start, end
        )
        
        assert has_conflicts is False
        assert len(conflicts) == 0
    
    def test_check_conflicting_requests_with_conflicts(self, db_session, sample_user):
        """Test checking for conflicts when they exist"""
        from db.models import PTORequest, PTOStatus
        import uuid
        
        # Create existing request
        existing_request = PTORequest(
            id=str(uuid.uuid4()),
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
        assert conflicts[0]['id'] == existing_request.id
    
    def test_includes_pending_requests(self, db_session, sample_user):
        """Test that pending requests ARE counted as conflicts"""
        from db.models import PTORequest, PTOStatus
        import uuid
        
        # Create pending request
        pending_request = PTORequest(
            id=str(uuid.uuid4()),
            email=sample_user.email,
            company=sample_user.company,
            start_date=date(2025, 12, 3),
            end_date=date(2025, 12, 5),
            days_requested=3.0,
            status=PTOStatus.PENDING
        )
        db_session.add(pending_request)
        db_session.commit()
        
        # Check for conflicts
        start = date(2025, 12, 1)
        end = date(2025, 12, 4)
        
        has_conflicts, conflicts = check_conflicting_requests(
            db_session, sample_user.email, start, end
        )
        
        # Pending requests ARE conflicts
        assert has_conflicts is True
        assert len(conflicts) == 1
    
    def test_ignores_denied_requests(self, db_session, sample_user):
        """Test that denied requests don't count as conflicts"""
        from db.models import PTORequest, PTOStatus
        import uuid
        
        # Create denied request
        denied_request = PTORequest(
            id=str(uuid.uuid4()),
            email=sample_user.email,
            company=sample_user.company,
            start_date=date(2025, 12, 3),
            end_date=date(2025, 12, 5),
            days_requested=3.0,
            status=PTOStatus.DENIED
        )
        db_session.add(denied_request)
        db_session.commit()
        
        # Check for conflicts
        start = date(2025, 12, 1)
        end = date(2025, 12, 4)
        
        has_conflicts, conflicts = check_conflicting_requests(
            db_session, sample_user.email, start, end
        )
        
        assert has_conflicts is False
    
    def test_exact_overlap(self, db_session, sample_approved_pto_request):
        """Test detection with exact date overlap"""
        has_conflicts, conflicts = check_conflicting_requests(
            db_session,
            sample_approved_pto_request.email,
            sample_approved_pto_request.start_date,
            sample_approved_pto_request.end_date
        )
        
        assert has_conflicts is True
        assert len(conflicts) == 1
    
    def test_partial_overlap_start(self, db_session, sample_approved_pto_request):
        """Test detection with partial overlap at start"""
        # Existing: Dec 10-15
        # New: Dec 8-12 (overlaps at start)
        start = sample_approved_pto_request.start_date - timedelta(days=2)
        end = sample_approved_pto_request.start_date + timedelta(days=2)
        
        has_conflicts, conflicts = check_conflicting_requests(
            db_session,
            sample_approved_pto_request.email,
            start,
            end
        )
        
        assert has_conflicts is True
    
    def test_partial_overlap_end(self, db_session, sample_approved_pto_request):
        """Test detection with partial overlap at end"""
        # Existing: Dec 10-15
        # New: Dec 13-17 (overlaps at end)
        start = sample_approved_pto_request.end_date - timedelta(days=2)
        end = sample_approved_pto_request.end_date + timedelta(days=2)
        
        has_conflicts, conflicts = check_conflicting_requests(
            db_session,
            sample_approved_pto_request.email,
            start,
            end
        )
        
        assert has_conflicts is True
    
    def test_no_overlap_before(self, db_session, sample_approved_pto_request):
        """Test no conflict when request is before existing"""
        # Existing: Dec 10-15
        # New: Dec 1-5 (before existing)
        start = sample_approved_pto_request.start_date - timedelta(days=10)
        end = sample_approved_pto_request.start_date - timedelta(days=5)
        
        has_conflicts, conflicts = check_conflicting_requests(
            db_session,
            sample_approved_pto_request.email,
            start,
            end
        )
        
        assert has_conflicts is False
    
    def test_no_overlap_after(self, db_session, sample_approved_pto_request):
        """Test no conflict when request is after existing"""
        # Existing: Dec 10-15
        # New: Dec 20-25 (after existing)
        start = sample_approved_pto_request.end_date + timedelta(days=5)
        end = sample_approved_pto_request.end_date + timedelta(days=10)
        
        has_conflicts, conflicts = check_conflicting_requests(
            db_session,
            sample_approved_pto_request.email,
            start,
            end
        )
        
        assert has_conflicts is False
    
    def test_user_isolation(self, db_session, sample_approved_pto_request, sample_user):
        """Test that conflicts are user-specific"""
        # Different user shouldn't see conflicts
        has_conflicts, conflicts = check_conflicting_requests(
            db_session,
            "different@testcompany.com",  # Different user
            sample_approved_pto_request.start_date,
            sample_approved_pto_request.end_date
        )
        
        # Should not find conflicts from different user
        assert has_conflicts is False


class TestCheckBlackoutPeriods:
    """Test blackout period checking"""
    
    def test_no_blackout_periods(self, db_session, sample_company):
        """Test when no blackout periods exist"""
        has_conflicts, conflict_list = check_blackout_periods(
            db_session,
            sample_company.name,
            date(2025, 12, 1),
            date(2025, 12, 5)
        )
        
        assert has_conflicts is False
        assert len(conflict_list) == 0
    
    def test_with_blackout_period(self, db_session, sample_company):
        """Test detection of blackout period"""
        from db.models import CompanyBlackoutDate
        import uuid
        
        # Create blackout period
        blackout = CompanyBlackoutDate(
            id=str(uuid.uuid4()),
            company=sample_company.name,
            period_name="Year-End Shutdown",
            start_date=date(2025, 12, 20),
            end_date=date(2025, 12, 31),
            reason="Company closed for holidays"
        )
        db_session.add(blackout)
        db_session.commit()
        
        # Check request that overlaps
        has_conflicts, conflict_list = check_blackout_periods(
            db_session,
            sample_company.name,
            date(2025, 12, 15),
            date(2025, 12, 25)
        )
        
        assert has_conflicts is True
        assert len(conflict_list) == 1
        assert "Year-End Shutdown" in conflict_list[0]
    
    def test_no_overlap_with_blackout(self, db_session, sample_company):
        """Test request that doesn't overlap blackout"""
        from db.models import CompanyBlackoutDate
        import uuid
        
        # Create blackout period
        blackout = CompanyBlackoutDate(
            id=str(uuid.uuid4()),
            company=sample_company.name,
            period_name="Year-End Shutdown",
            start_date=date(2025, 12, 20),
            end_date=date(2025, 12, 31),
            reason="Company closed"
        )
        db_session.add(blackout)
        db_session.commit()
        
        # Check request before blackout
        has_conflicts, conflict_list = check_blackout_periods(
            db_session,
            sample_company.name,
            date(2025, 12, 1),
            date(2025, 12, 10)
        )
        
        assert has_conflicts is False
        assert len(conflict_list) == 0