#!/usr/bin/env python3
"""
Generate a JWT token for the voice agent
This token represents a user who can access the backend API
"""
import os
import sys
from pathlib import Path
from datetime import timedelta, datetime, timezone
import jwt
from dotenv import load_dotenv

# Load environment from backend
backend_env = Path(__file__).parents[2] / "backend" / ".env"
if backend_env.exists():
    load_dotenv(backend_env)

# Get JWT secret from environment
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    print("❌ JWT_SECRET_KEY not found in backend/.env")
    sys.exit(1)

ALGORITHM = "HS256"
# Create a token that expires in 365 days (for voice agent service account)
ACCESS_TOKEN_EXPIRE_DAYS = 365

def create_voice_agent_token():
    """
    Create a long-lived JWT token for the voice agent service account
    Uses the test user: user@crousemedical.com
    """
    # Token data for a test user
    token_data = {
        "sub": "user@crousemedical.com",  # User email
        "company": "Crouse Medical Practice",  # User's company
        "role": "user"  # User role
    }

    # Create expiration time (365 days from now)
    expire = datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    token_data.update({"exp": expire})

    # Encode JWT
    encoded_jwt = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt

if __name__ == "__main__":
    token = create_voice_agent_token()
    print("✅ Generated JWT token for voice agent (expires in 365 days):")
    print(f"\nVOICE_AGENT_JWT={token}")
    print("\n📋 Add this to voice_pipeline/scripts/.env file")
    print(f"\n🔑 Token represents user: user@crousemedical.com")
    print(f"🏢 Company: Crouse Medical Practice")
