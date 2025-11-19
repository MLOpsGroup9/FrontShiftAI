"""
Database models and configuration
SQLite for local, easily upgradable to PostgreSQL for GCP
"""

from sqlalchemy import create_engine, Column, String, DateTime, Enum, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import enum

# Database URL - Change this for GCP PostgreSQL later
# LOCAL: sqlite:///./users.db
# GCP: postgresql://user:password@/dbname?host=/cloudsql/project:region:instance
DATABASE_URL = "sqlite:///./users.db"

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==========================================
# ENUMS
# ==========================================
class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    COMPANY_ADMIN = "company_admin"
    USER = "user"

# ==========================================
# MODELS
# ==========================================
class Company(Base):
    __tablename__ = "companies"
    
    name = Column(String, primary_key=True, index=True)
    domain = Column(String)  # Healthcare, Retail, etc.
    email_domain = Column(String, unique=True, index=True)
    url = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class User(Base):
    __tablename__ = "users"
    
    email = Column(String, primary_key=True, index=True)
    password = Column(String)  # In production, use hashed passwords
    name = Column(String)
    role = Column(Enum(UserRole), default=UserRole.USER)
    company = Column(String, nullable=True)  # None for super_admin
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PTOBalance(Base):
    __tablename__ = "pto_balances"
    
    email = Column(String, primary_key=True, index=True)
    company = Column(String)
    total_days = Column(Integer, default=15)  # Annual PTO allocation
    used_days = Column(Integer, default=0)
    available_days = Column(Integer, default=15)
    year = Column(Integer, default=2025)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PTORequest(Base):
    __tablename__ = "pto_requests"
    
    id = Column(String, primary_key=True)  # UUID
    email = Column(String, index=True)
    company = Column(String)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    days_requested = Column(Integer)  # Business days only
    reason = Column(String, nullable=True)
    status = Column(String, default="pending")  # pending, approved, denied
    approved_by = Column(String, nullable=True)  # Admin email who approved
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CompanyBlackoutDate(Base):
    __tablename__ = "company_blackout_dates"
    
    id = Column(String, primary_key=True)
    company = Column(String, index=True)
    date = Column(DateTime)
    reason = Column(String)  # "Holiday rush", "Inventory", etc.
    created_at = Column(DateTime, default=datetime.utcnow)

# ==========================================
# DATABASE FUNCTIONS
# ==========================================
def init_db():
    """Initialize database with tables"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def seed_initial_data():
    """Seed database with initial companies and users"""
    from sqlalchemy.orm import Session
    
    db = SessionLocal()
    
    try:
        # Check if already seeded
        existing_companies = db.query(Company).count()
        if existing_companies > 0:
            print("Database already seeded, skipping...")
            return
        
        print("🌱 Seeding database...")
        
        # Add Companies
        companies_data = [
            {"name": "Crouse Medical Practice", "domain": "Healthcare", "email_domain": "crousemedical.com", "url": "https://crousemed.com/media/1449/cmp-employee-handbook.pdf"},
            {"name": "Healthcare Services Group", "domain": "Healthcare", "email_domain": "healthcareservices.com", "url": "https://www.hcsgcorp.com/wp-content/uploads/2023/01/Employee-Handbook-Healthcare-Services-Group-January-2023.pdf"},
            {"name": "Lunds & Byerlys", "domain": "Retail", "email_domain": "lundsbyerlys.com", "url": "https://corporate.lundsandbyerlys.com/wp-content/uploads/2024/05/EmployeeHandbook_20190926.pdf"},
            {"name": "Holiday Market", "domain": "Retail", "email_domain": "holidaymarket.com", "url": "https://holiday-market.com/schedules/handbook.pdf"},
            {"name": "End Policies Manufacturing", "domain": "Manufacturing", "email_domain": "endpolicies.com", "url": "https://endpolicies.com/wp-content/uploads/2021/08/employee-handbook-2021-updated-1.pdf"},
            {"name": "B&G Foods", "domain": "Manufacturing", "email_domain": "bgfoods.com", "url": "https://bgfood.com/wp-content/uploads/2022/01/BG-Employee-Handbook-2022.pdf"},
            {"name": "Kinyon Construction", "domain": "Construction", "email_domain": "kinyonconstruction.com", "url": "https://www.kinyonconstruction.com/files/132869525.pdf"},
            {"name": "TNT Construction", "domain": "Construction", "email_domain": "tntconstruction.com", "url": "https://www.tntconstructionmn.com/wp-content/uploads/2018/05/TNT-Construction-Inc-Handbook_Final-2018.pdf"},
            {"name": "Alta Peruvian Lodge", "domain": "Hospitality", "email_domain": "altaperuvian.com", "url": "https://www.altaperuvian.com/wp-content/uploads/2017/01/APL-Empl-Manual-Revised-12-22-16-fixed.pdf"},
            {"name": "Western University Hospitality Services", "domain": "Hospitality", "email_domain": "westernhospitality.com", "url": "https://www.hospitalityservices.uwo.ca/staff/handbook.pdf"},
            {"name": "Old National Bank", "domain": "Finance", "email_domain": "oldnational.com", "url": "https://www.oldnational.com/globalassets/onb-site/onb-documents/onb-about-us/onb-team-member-handbook/team-member-handbook.pdf"},
            {"name": "Home Bank", "domain": "Finance", "email_domain": "homebank.com", "url": "https://cdn.firstbranchcms.com/kcms-doc/472/88717/2025-Home-Bank-Employee-Handbook.25.02.24.13.53.40.pdf"},
            {"name": "The Clean Space", "domain": "Cleaning&Maintenance", "email_domain": "cleanspace.com", "url": "https://thecleanspace.com/wp-content/uploads/2024/09/8.-Employee-Handbook-v4.8.pdf"},
            {"name": "AFL Cleaning Services", "domain": "Cleaning&Maintenance", "email_domain": "aflcleaning.com", "url": "https://www.aflcleaningservices.com/resources/AFL_EmployeeHandbook_new.pdf"},
            {"name": "O'Neill Logistics", "domain": "Logistics", "email_domain": "oneilllogistics.com", "url": "https://www.oneilllogistics.com/wp-content/uploads/2023/06/NJ-Warehouse-2022-Employee-Handbook.pdf"},
            {"name": "Buchheit Logistics", "domain": "Logistics", "email_domain": "buchheitlogistics.com", "url": "https://driver.buchheitlogistics.com/wp-content/uploads/2021/06/Logistics-Team-Member-Handbook.pdf"},
            {"name": "Jacob Heating and Cooling", "domain": "FieldServiceTechnicians", "email_domain": "jacobhac.com", "url": "https://www.jacobhac.com/wp-content/uploads/2021/01/Jacob-HAC-Employee-Handbook.pdf"},
            {"name": "CRA Staffing", "domain": "FieldServiceTechnicians", "email_domain": "crastaffing.com", "url": "https://www.crastaffing.com/wp-content/uploads/2020/01/2018-Field-Staff-Handbook-PDF.pdf"},
            {"name": "Prestige Janitorial Service", "domain": "Cleaning&Maintenance", "email_domain": "prestigejanitorial.com", "url": "https://www.phoenixjanitorialservice.net/wp-content/uploads/2017/05/2018-Employee-Handbook.pdf"},
        ]
        
        for company_data in companies_data:
            company = Company(**company_data)
            db.add(company)
        
        # Add Super Admin
        super_admin = User(
            email="admin@group9.com",
            password="admin123",  # In production, hash this!
            name="Super Admin",
            role=UserRole.SUPER_ADMIN,
            company=None
        )
        db.add(super_admin)
        
        # Add Company Admins
        company_admins = [
            {"email": "admin@crousemedical.com", "name": "Crouse Admin", "company": "Crouse Medical Practice"},
            {"email": "admin@healthcareservices.com", "name": "Healthcare Services Admin", "company": "Healthcare Services Group"},
            {"email": "admin@lundsbyerlys.com", "name": "Lunds Admin", "company": "Lunds & Byerlys"},
            {"email": "admin@holidaymarket.com", "name": "Holiday Market Admin", "company": "Holiday Market"},
            {"email": "admin@endpolicies.com", "name": "End Policies Admin", "company": "End Policies Manufacturing"},
            {"email": "admin@bgfoods.com", "name": "B&G Foods Admin", "company": "B&G Foods"},
            {"email": "admin@kinyonconstruction.com", "name": "Kinyon Admin", "company": "Kinyon Construction"},
            {"email": "admin@tntconstruction.com", "name": "TNT Admin", "company": "TNT Construction"},
            {"email": "admin@altaperuvian.com", "name": "Alta Peruvian Admin", "company": "Alta Peruvian Lodge"},
            {"email": "admin@westernhospitality.com", "name": "Western Hospitality Admin", "company": "Western University Hospitality Services"},
            {"email": "admin@oldnational.com", "name": "Old National Admin", "company": "Old National Bank"},
            {"email": "admin@homebank.com", "name": "Home Bank Admin", "company": "Home Bank"},
            {"email": "admin@cleanspace.com", "name": "Clean Space Admin", "company": "The Clean Space"},
            {"email": "admin@aflcleaning.com", "name": "AFL Cleaning Admin", "company": "AFL Cleaning Services"},
            {"email": "admin@oneilllogistics.com", "name": "O'Neill Admin", "company": "O'Neill Logistics"},
            {"email": "admin@buchheitlogistics.com", "name": "Buchheit Admin", "company": "Buchheit Logistics"},
            {"email": "admin@jacobhac.com", "name": "Jacob HAC Admin", "company": "Jacob Heating and Cooling"},
            {"email": "admin@crastaffing.com", "name": "CRA Staffing Admin", "company": "CRA Staffing"},
            {"email": "admin@prestigejanitorial.com", "name": "Prestige Admin", "company": "Prestige Janitorial Service"},
        ]
        
        for admin_data in company_admins:
            admin = User(
                email=admin_data["email"],
                password="admin123",
                name=admin_data["name"],
                role=UserRole.COMPANY_ADMIN,
                company=admin_data["company"]
            )
            db.add(admin)
        
        # Add Sample Users
        sample_users = [
            {"email": "user@crousemedical.com", "name": "John Doe", "company": "Crouse Medical Practice"},
            {"email": "employee@crousemedical.com", "name": "Jane Smith", "company": "Crouse Medical Practice"},
        ]
        
        for user_data in sample_users:
            user = User(
                email=user_data["email"],
                password="password123",
                name=user_data["name"],
                role=UserRole.USER,
                company=user_data["company"]
            )
            db.add(user)
        
        db.commit()
        print("✅ Database seeded successfully!")
        
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()