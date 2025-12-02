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
        # Use future dates starting on a Monday
        today = date.today()
        start = today + timedelta(days=(7 - today.weekday()) % 7)  # Next Monday
        if start == today:
            start += timedelta(days=7)
        end = start + timedelta(days=4)  # Friday
        holidays = []
        
        result = calculate_business_days(start, end, holidays)
        assert result == 5.0
    
    def test_calculate_business_days_with_weekend(self):
        """Test business days calculation excluding weekends"""
        # Use future dates starting on a Monday
        today = date.today()
        start = today + timedelta(days=(7 - today.weekday()) % 7)  # Next Monday
        if start == today:
            start += timedelta(days=7)
        end = start + timedelta(days=6)  # Sunday (Mon-Sun = 7 days)
        holidays = []
        
        result = calculate_business_days(start, end, holidays)
        assert result == 5.0  # Mon-Fri only
    
    def test_calculate_business_days_with_holidays(self):
        """Test business days calculation with holidays"""
        # Use future dates starting on a Wednesday
        today = date.today()
        start = today + timedelta(days=14)
        while start.weekday() != 2:  # Wednesday = 2
            start += timedelta(days=1)
        end = start + timedelta(days=2)  # Friday
        
        # Add a holiday on Thursday
        holidays = [start + timedelta(days=1)]
        
        result = calculate_business_days(start, end, holidays)
        assert result == 2.0  # Wed and Fri only
    
    def test_weekend_only_request(self):
        """Test that weekend-only requests return zero"""
        # Find next Saturday
        today = date.today()
        start = today + timedelta(days=(5 - today.weekday() + 7) % 7)
        if start == today or start < today:
            start += timedelta(days=7)
        end = start + timedelta(days=1)  # Sunday
        holidays = []
        
        result = calculate_business_days(start, end, holidays)
        assert result == 0.0
    
    def test_single_day_request(self):
        """Test single business day request"""
        # Use future date on a Monday
        today = date.today()
        start = today + timedelta(days=(7 - today.weekday()) % 7)  # Next Monday
        if start == today:
            start += timedelta(days=7)
        end = start  # Same day
        holidays = []
        
        result = calculate_business_days(start, end, holidays)
        assert result == 1.0
    
    def test_multiple_weeks_span(self):
        """Test calculation spanning multiple weeks"""
        # Use future dates starting on a Monday
        today = date.today()
        start = today + timedelta(days=(7 - today.weekday()) % 7)  # Next Monday
        if start == today:
            start += timedelta(days=7)
        end = start + timedelta(days=11)  # Almost 2 weeks later (Friday)
        holidays = []
        
        result = calculate_business_days(start, end, holidays)
        assert result == 10.0  # 2 full work weeks
    
    def test_all_holidays(self):
        """Test when all days are holidays"""
        # Use future dates starting on a Wednesday
        today = date.today()
        start = today + timedelta(days=14)
        while start.weekday() != 2:  # Wednesday = 2
            start += timedelta(days=1)
        end = start + timedelta(days=2)  # Friday
        
        # Mark all three days as holidays
        holidays = [
            start,
            start + timedelta(days=1),
            start + timedelta(days=2)
        ]
        
        result = calculate_business_days(start, end, holidays)
        assert result == 0.0
    
    def test_end_before_start(self):
        """Test invalid date range (end before start)"""
        today = date.today()
        start = today + timedelta(days=10)
        end = today + timedelta(days=5)
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
        today = date.today()
        start = today + timedelta(days=30)
        end = start + timedelta(days=4)
        
        has_conflicts, conflicts = check_conflicting_requests(
            db_session, sample_user.email, start, end
        )
        
        assert has_conflicts is False
        assert len(conflicts) == 0
    
    def test_check_conflicting_requests_with_conflicts(self, db_session, sample_user):
        """Test checking for conflicts when they exist"""
        from db.models import PTORequest, PTOStatus
        import uuid
        
        today = date.today()
        conflict_start = today + timedelta(days=20)
        conflict_end = conflict_start + timedelta(days=2)
        
        # Create existing request
        existing_request = PTORequest(
            id=str(uuid.uuid4()),
            email=sample_user.email,
            company=sample_user.company,
            start_date=conflict_start,
            end_date=conflict_end,
            days_requested=3.0,
            status=PTOStatus.APPROVED
        )
        db_session.add(existing_request)
        db_session.commit()
        
        # Check for conflicts with overlapping dates
        start = conflict_start - timedelta(days=2)
        end = conflict_start + timedelta(days=1)
        
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
        
        today = date.today()
        conflict_start = today + timedelta(days=25)
        conflict_end = conflict_start + timedelta(days=2)
        
        # Create pending request
        pending_request = PTORequest(
            id=str(uuid.uuid4()),
            email=sample_user.email,
            company=sample_user.company,
            start_date=conflict_start,
            end_date=conflict_end,
            days_requested=3.0,
            status=PTOStatus.PENDING
        )
        db_session.add(pending_request)
        db_session.commit()
        
        # Check for conflicts
        start = conflict_start - timedelta(days=2)
        end = conflict_start + timedelta(days=1)
        
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
        
        today = date.today()
        denied_start = today + timedelta(days=30)
        denied_end = denied_start + timedelta(days=2)
        
        # Create denied request
        denied_request = PTORequest(
            id=str(uuid.uuid4()),
            email=sample_user.email,
            company=sample_user.company,
            start_date=denied_start,
            end_date=denied_end,
            days_requested=3.0,
            status=PTOStatus.DENIED
        )
        db_session.add(denied_request)
        db_session.commit()
        
        # Check for conflicts
        start = denied_start - timedelta(days=2)
        end = denied_start + timedelta(days=1)
        
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
        # Existing: sample dates
        # New: 2 days before start to 2 days after start (overlaps at start)
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
        # Existing: sample dates
        # New: 2 days before end to 2 days after end (overlaps at end)
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
        # New: 10 days before to 5 days before (before existing)
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
        # New: 5 days after to 10 days after (after existing)
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
        today = date.today()
        start = today + timedelta(days=40)
        end = start + timedelta(days=4)
        
        has_conflicts, conflict_list = check_blackout_periods(
            db_session,
            sample_company.name,
            start,
            end
        )
        
        assert has_conflicts is False
        assert len(conflict_list) == 0
    
    def test_with_blackout_period(self, db_session, sample_company):
        """Test detection of blackout period"""
        from db.models import CompanyBlackoutDate
        import uuid
        
        today = date.today()
        blackout_start = today + timedelta(days=50)
        blackout_end = blackout_start + timedelta(days=10)
        
        # Create blackout period
        blackout = CompanyBlackoutDate(
            id=str(uuid.uuid4()),
            company=sample_company.name,
            period_name="Year-End Shutdown",
            start_date=blackout_start,
            end_date=blackout_end,
            reason="Company closed for holidays"
        )
        db_session.add(blackout)
        db_session.commit()
        
        # Check request that overlaps
        request_start = blackout_start - timedelta(days=5)
        request_end = blackout_start + timedelta(days=5)
        
        has_conflicts, conflict_list = check_blackout_periods(
            db_session,
            sample_company.name,
            request_start,
            request_end
        )
        
        assert has_conflicts is True
        assert len(conflict_list) == 1
        assert "Year-End Shutdown" in conflict_list[0]
    
    def test_no_overlap_with_blackout(self, db_session, sample_company):
        """Test request that doesn't overlap blackout"""
        from db.models import CompanyBlackoutDate
        import uuid
        
        today = date.today()
        blackout_start = today + timedelta(days=60)
        blackout_end = blackout_start + timedelta(days=10)
        
        # Create blackout period
        blackout = CompanyBlackoutDate(
            id=str(uuid.uuid4()),
            company=sample_company.name,
            period_name="Year-End Shutdown",
            start_date=blackout_start,
            end_date=blackout_end,
            reason="Company closed"
        )
        db_session.add(blackout)
        db_session.commit()
        
        # Check request before blackout
        request_start = blackout_start - timedelta(days=20)
        request_end = blackout_start - timedelta(days=10)
        
        has_conflicts, conflict_list = check_blackout_periods(
            db_session,
            sample_company.name,
            request_start,
            request_end
        )
        
        assert has_conflicts is False
        assert len(conflict_list) == 0