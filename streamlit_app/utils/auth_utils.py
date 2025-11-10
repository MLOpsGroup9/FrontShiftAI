import hashlib
import streamlit as st
from .db_utils import get_connection

def hash_password(password: str):
    """SHA-256 hash (can upgrade later to bcrypt)."""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_admin(email, password):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT password FROM admin WHERE email=?", (email,))
    row = c.fetchone()
    conn.close()
    return row and password == row[0]

def verify_user(email, password):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE email=?", (email,))
    row = c.fetchone()
    conn.close()
    return row and password == row[0]

def extract_company_from_email(email: str):
    """Takes john@crousemedicalpractice.com → crousemedicalpractice"""
    try:
        company = email.split("@")[1].split(".")[0]
        return company.lower()
    except Exception:
        return None
