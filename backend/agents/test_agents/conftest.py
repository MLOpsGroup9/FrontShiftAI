"""
Pytest fixtures for agent tests
"""
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))

import pytest
from datetime import date, datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Now imports should work
from db.models import Base, User, Company, PTOBalance, PTORequest, CompanyHoliday, PTOStatus, UserRole
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
    from db.models import HRTicket, TicketStatus, TicketCategory, MeetingType, Urgency
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
    from db.models import User, UserRole
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