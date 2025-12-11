"""
Pytest fixtures for agent tests
"""
import sys
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from backend/.env
backend_dir = Path(__file__).resolve().parent.parent.parent
env_path = backend_dir / '.env'
load_dotenv(env_path)

# Verify GROQ_API_KEY is loaded
if os.getenv('GROQ_API_KEY'):
    print(f"\n✓ GROQ_API_KEY loaded for testing")
else:
    print(f"\n⚠ Warning: GROQ_API_KEY not found in {env_path}")

# Add backend directory to path
sys.path.insert(0, str(backend_dir))

# ... rest of your conftest.py continues here

import pytest
from datetime import date, datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Now imports should work
from db.models import (
    Base, User, Company, PTOBalance, PTORequest, CompanyHoliday, 
    PTOStatus, UserRole, HRTicket, TicketStatus, TicketCategory, 
    MeetingType, Urgency
)
from db.connection import get_db

# Test database
TEST_DATABASE_URL = "sqlite:///./test_agents.db"

@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test"""
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    
    yield session
    
    session.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def sample_company(db_session):
    """Create a sample company"""
    company = Company(
        name="Test Company",
        domain="Technology",
        email_domain="testcompany.com",
        url="https://test.com"
    )
    db_session.add(company)
    db_session.commit()
    return company

@pytest.fixture
def sample_user(db_session, sample_company):
    """Create a sample user"""
    user = User(
        email="test@testcompany.com",
        password="password123",
        name="Test User",
        role=UserRole.USER,
        company=sample_company.name
    )
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def sample_pto_balance(db_session, sample_user, sample_company):
    """Create a sample PTO balance"""
    balance = PTOBalance(
        email=sample_user.email,
        company=sample_company.name,
        year=2025,
        total_days=15.0,
        used_days=0.0,
        pending_days=0.0
    )
    db_session.add(balance)
    db_session.commit()
    return balance

@pytest.fixture
def sample_holidays(db_session, sample_company):
    """Create sample company holidays"""
    import uuid
    holidays = [
        CompanyHoliday(
            id=str(uuid.uuid4()),
            company=sample_company.name,
            holiday_name="Christmas",
            holiday_date=date(2025, 12, 25),
            is_recurring=True
        ),
        CompanyHoliday(
            id=str(uuid.uuid4()),
            company=sample_company.name,
            holiday_name="New Year",
            holiday_date=date(2025, 1, 1),
            is_recurring=True
        )
    ]
    for holiday in holidays:
        db_session.add(holiday)
    db_session.commit()
    return holidays

# ==========================================
# HR TICKET FIXTURES
# ==========================================

@pytest.fixture
def sample_hr_ticket(db_session, sample_user):
    """Create a sample HR ticket for testing"""
    from datetime import datetime
    import uuid
    
    ticket = HRTicket(
        id=str(uuid.uuid4()),
        email=sample_user.email,
        company=sample_user.company,
        subject="Test HR Ticket",
        description="This is a test ticket for HR inquiries",
        category=TicketCategory.BENEFITS,
        meeting_type=MeetingType.ONLINE,
        urgency=Urgency.NORMAL,
        status=TicketStatus.PENDING,
        queue_position=1,
        preferred_date=None,
        preferred_time_slot=None,
        created_at=datetime.utcnow()
    )
    
    db_session.add(ticket)
    db_session.commit()
    db_session.refresh(ticket)
    
    return ticket


@pytest.fixture
def sample_company_admin(db_session):
    """Create a sample company admin user for testing"""
    from datetime import datetime
    
    admin = User(
        email="admin@crousemedical.com",
        password="admin123",
        name="Test Admin",
        role=UserRole.COMPANY_ADMIN,
        company="Crouse Medical Practice",
        created_at=datetime.utcnow()
    )
    
    # Check if already exists
    existing = db_session.query(User).filter_by(email=admin.email).first()
    if existing:
        return existing
    
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    
    return admin

# ==========================================
# NEW FIXTURES FOR ENHANCED TESTING
# ==========================================

@pytest.fixture
def sample_approved_pto_request(db_session, sample_user):
    """Create an approved PTO request for conflict testing"""
    import uuid
    
    # Use future dates to avoid test failures
    today = date.today()
    start_date = today + timedelta(days=45)  # 45 days in the future
    end_date = start_date + timedelta(days=5)  # 6 days total (includes weekend)
    
    request = PTORequest(
        id=str(uuid.uuid4()),
        email=sample_user.email,
        company=sample_user.company,
        start_date=start_date,
        end_date=end_date,
        days_requested=4.0,
        status=PTOStatus.APPROVED,
        reason="Vacation"
    )
    db_session.add(request)
    db_session.commit()
    return request

@pytest.fixture
def multiple_hr_tickets(db_session, sample_user):
    """Create multiple HR tickets with different statuses"""
    import uuid
    tickets = []
    
    statuses = [
        (TicketStatus.PENDING, 1),
        (TicketStatus.IN_PROGRESS, None),
        (TicketStatus.RESOLVED, None),
        (TicketStatus.CLOSED, None)
    ]
    
    for status, queue_pos in statuses:
        ticket = HRTicket(
            id=str(uuid.uuid4()),
            email=sample_user.email,
            company=sample_user.company,
            subject=f"Ticket - {status.value}",
            description=f"Test ticket with status {status.value}",
            category=TicketCategory.GENERAL_INQUIRY,
            meeting_type=MeetingType.NO_MEETING,
            urgency=Urgency.NORMAL,
            status=status,
            queue_position=queue_pos,
            created_at=datetime.utcnow()
        )
        db_session.add(ticket)
        tickets.append(ticket)
    
    db_session.commit()
    return tickets

@pytest.fixture
def pto_balance_with_usage(db_session, sample_user, sample_company):
    """Create PTO balance with some days already used and pending"""
    balance = PTOBalance(
        email=sample_user.email,
        company=sample_company.name,
        year=2025,
        total_days=15.0,
        used_days=5.0,
        pending_days=3.0
    )
    db_session.add(balance)
    db_session.commit()
    return balance

@pytest.fixture
def sample_company_with_url(db_session):
    """Create a sample company with URL for website extraction tests"""
    company = Company(
        name="Crouse Medical Practice",
        domain="Healthcare",
        email_domain="crousemedical.com",
        url="https://crousemed.com/media/1449/cmp-employee-handbook.pdf"
    )
    db_session.add(company)
    db_session.commit()
    return company