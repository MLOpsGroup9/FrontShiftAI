"""
SQLAlchemy database models
"""
from sqlalchemy import Column, String, DateTime, Enum, Integer, Float, Boolean, Date, UniqueConstraint
from db.connection import Base
from datetime import datetime, timezone
import enum

# ==========================================
# ENUMS
# ==========================================
class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    COMPANY_ADMIN = "company_admin"
    USER = "user"

class PTOStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    CANCELLED = "cancelled"

# ==========================================
# MODELS
# ==========================================
class Company(Base):
    __tablename__ = "companies"
    
    name = Column(String, primary_key=True, index=True)
    domain = Column(String)  # Healthcare, Retail, etc.
    email_domain = Column(String, unique=True, index=True)
    url = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class User(Base):
    __tablename__ = "users"
    
    email = Column(String, primary_key=True, index=True)
    password = Column(String)  # In production, use hashed passwords
    name = Column(String)
    role = Column(Enum(UserRole), default=UserRole.USER)
    company = Column(String, nullable=True)  # None for super_admin
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class PTOBalance(Base):
    __tablename__ = "pto_balances"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, index=True)
    company = Column(String)
    year = Column(Integer, default=2025)
    total_days = Column(Float, default=15.0)  # Annual PTO allocation
    used_days = Column(Float, default=0.0)
    pending_days = Column(Float, default=0.0)  # Days in pending requests
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        UniqueConstraint('email', 'year', name='unique_email_year'),
    )
    
    @property
    def remaining_days(self):
        """Calculate remaining days dynamically"""
        return self.total_days - self.used_days - self.pending_days

class PTORequest(Base):
    __tablename__ = "pto_requests"
    
    id = Column(String, primary_key=True)  # UUID
    email = Column(String, index=True)
    company = Column(String, index=True)
    start_date = Column(Date)
    end_date = Column(Date)
    days_requested = Column(Float)  # Business days (can be 0.5 for half days)
    reason = Column(String, nullable=True)
    status = Column(Enum(PTOStatus), default=PTOStatus.PENDING)
    admin_notes = Column(String, nullable=True)
    approved_by = Column(String, nullable=True)  # Admin email
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class CompanyHoliday(Base):
    """Official company holidays (non-working days)"""
    __tablename__ = "company_holidays"
    
    id = Column(String, primary_key=True)  # UUID
    company = Column(String, index=True)
    holiday_name = Column(String)
    holiday_date = Column(Date)
    is_recurring = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class CompanyBlackoutDate(Base):
    """Date ranges where PTO requests are not allowed"""
    __tablename__ = "company_blackout_dates"
    
    id = Column(String, primary_key=True)  # UUID
    company = Column(String, index=True)
    period_name = Column(String)
    start_date = Column(Date)
    end_date = Column(Date)
    reason = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))