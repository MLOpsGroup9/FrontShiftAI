import sqlite3
from pathlib import Path

# Path to the app_users.db inside streamlit_app/data/
DB_PATH = Path(__file__).resolve().parents[1] / "data" / "app_users.db"

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Companies table
    c.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)

    # Users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            company_id INTEGER,
            FOREIGN KEY (company_id) REFERENCES companies (id)
        )
    """)

    # Admin table (only one fixed admin)
    c.execute("""
        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    c.execute("SELECT * FROM admin WHERE email='admin@frontshiftai.com'")
    if not c.fetchone():
        c.execute(
            "INSERT INTO admin (email, password) VALUES (?, ?)",
            ("admin@frontshiftai.com", "admin123")
        )

    conn.commit()
    conn.close()

def get_connection():
    return sqlite3.connect(DB_PATH)
