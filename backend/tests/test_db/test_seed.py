"""Test database seeding"""
import pytest
from db.seed import seed_initial_data
from db.models import User, Company, UserRole

def test_seed_initial_data(test_db):
    """Test that seeding creates expected data"""
    # Mock the session
    import db.seed
    original_session = db.seed.SessionLocal
    db.seed.SessionLocal = lambda: test_db
    
    try:
        seed_initial_data()
        
        # Check companies were created
        companies = test_db.query(Company).all()
        assert len(companies) == 19
        
        # Check super admin was created
        super_admin = test_db.query(User).filter(User.role == UserRole.SUPER_ADMIN).first()
        assert super_admin is not None
        assert super_admin.email == "admin@group9.com"
        
        # Check company admins were created
        admins = test_db.query(User).filter(User.role == UserRole.COMPANY_ADMIN).all()
        assert len(admins) == 19
        
        # Check regular users were created
        users = test_db.query(User).filter(User.role == UserRole.USER).all()
        assert len(users) == 2
        
    finally:
        db.seed.SessionLocal = original_session