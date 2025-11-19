"""
Company mapping helper functions
Data is stored in database, these are just utility functions
"""

from database import SessionLocal, User, Company, UserRole

def get_company_from_email(email: str) -> str:
    """Extract company name from email"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email.lower()).first()
        if user:
            return user.company
        
        # If user doesn't exist, try to extract from domain
        if "@" not in email:
            return None
        
        domain = email.split("@")[1].lower()
        company = db.query(Company).filter(Company.email_domain == domain).first()
        return company.name if company else None
    finally:
        db.close()

def validate_credentials(email: str, password: str):
    """Validate user credentials and return (success, company_name, role)"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email.lower()).first()
        
        if not user:
            return False, None, None
        
        if user.password != password:
            return False, None, None
        
        return True, user.company, user.role.value
    finally:
        db.close()

def get_user_role(email: str) -> str:
    """Get user role"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email.lower()).first()
        return user.role.value if user else "user"
    finally:
        db.close()

def is_super_admin(email: str) -> bool:
    """Check if user is super admin"""
    return get_user_role(email) == "super_admin"

def is_company_admin(email: str) -> bool:
    """Check if user is company admin"""
    return get_user_role(email) == "company_admin"

def get_all_companies() -> list:
    """Get all companies"""
    db = SessionLocal()
    try:
        companies = db.query(Company).all()
        return [
            {
                "name": c.name,
                "domain": c.domain,
                "email_domain": c.email_domain,
                "url": c.url
            }
            for c in companies
        ]
    finally:
        db.close()

def get_all_company_admins() -> list:
    """Get all company admins"""
    db = SessionLocal()
    try:
        admins = db.query(User).filter(User.role == UserRole.COMPANY_ADMIN).all()
        return [
            {
                "email": admin.email,
                "name": admin.name,
                "company": admin.company,
                "role": admin.role.value,
                "created_at": admin.created_at.isoformat() if admin.created_at else None
            }
            for admin in admins
        ]
    finally:
        db.close()

def get_users_by_company(company: str) -> list:
    """Get all users for a specific company"""
    db = SessionLocal()
    try:
        users = db.query(User).filter(
            User.company == company,
            User.role == UserRole.USER
        ).all()
        
        return [
            {
                "email": user.email,
                "name": user.name,
                "role": user.role.value,
                "password": user.password,  # Only for admin view
                "created_at": user.created_at.isoformat() if user.created_at else None
            }
            for user in users
        ]
    finally:
        db.close()

def add_user(email: str, password: str, company: str, name: str = "", role: str = "user"):
    """Add a new user to database"""
    db = SessionLocal()
    try:
        # Check if user already exists
        existing = db.query(User).filter(User.email == email.lower()).first()
        if existing:
            return False, "User already exists"
        
        # Map string role to enum
        role_enum = UserRole.USER
        if role == "company_admin":
            role_enum = UserRole.COMPANY_ADMIN
        elif role == "super_admin":
            role_enum = UserRole.SUPER_ADMIN
        
        new_user = User(
            email=email.lower(),
            password=password,
            name=name,
            role=role_enum,
            company=company if role != "super_admin" else None
        )
        
        db.add(new_user)
        db.commit()
        return True, "User added successfully"
    except Exception as e:
        db.rollback()
        return False, str(e)
    finally:
        db.close()

def delete_user(email: str):
    """Delete a user from database"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email.lower()).first()
        
        if not user:
            return False, "User not found"
        
        # Prevent deleting super admin
        if user.role == UserRole.SUPER_ADMIN:
            return False, "Cannot delete super admin"
        
        db.delete(user)
        db.commit()
        return True, "User deleted successfully"
    except Exception as e:
        db.rollback()
        return False, str(e)
    finally:
        db.close()

def update_user_password(email: str, new_password: str):
    """Update user password"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email.lower()).first()
        
        if not user:
            return False, "User not found"
        
        user.password = new_password
        db.commit()
        return True, "Password updated successfully"
    except Exception as e:
        db.rollback()
        return False, str(e)
    finally:
        db.close()