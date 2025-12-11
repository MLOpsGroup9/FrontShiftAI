import sys
import os
from sqlalchemy.orm import Session

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import SessionLocal, User
from services.auth_service import get_password_hash, verify_password

def migrate_passwords():
    """
    Migrate all plaintext passwords to bcrypt hashes.
    """
    db: Session = SessionLocal()
    try:
        users = db.query(User).all()
        print(f"Found {len(users)} users. Checking for plaintext passwords...")
        
        migrated_count = 0
        
        for user in users:
            # Check if password is already hashed (bcrypt hashes start with $2b$ or $2a$)
            if user.password.startswith("$2b$") or user.password.startswith("$2a$"):
                continue
            
            print(f"Migrating password for user: {user.email}")
            
            # Hash the plaintext password
            hashed_password = get_password_hash(user.password)
            user.password = hashed_password
            migrated_count += 1
        
        if migrated_count > 0:
            db.commit()
            print(f"Successfully migrated {migrated_count} passwords.")
        else:
            print("No plaintext passwords found.")
            
    except Exception as e:
        print(f"Error during migration: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate_passwords()
