import streamlit as st
import sqlite3
import json
from pathlib import Path

PROJECT_ROOT = Path("/Users/sriks/Documents/Projects/FrontShiftAI")
DB_PATH = PROJECT_ROOT / "streamlit_app" / "data" / "app_users.db"
URL_JSON = PROJECT_ROOT / "data_pipeline" / "data" / "url.json"

st.set_page_config(page_title="Admin - Users", layout="wide", initial_sidebar_state="collapsed")

# Hide sidebar
st.markdown("""
    <style>
        [data-testid="stSidebar"], [data-testid="collapsedControl"], div[data-testid="stToolbar"] {display: none;}
        .logout-btn {position: fixed; top: 15px; right: 30px;}
    </style>
""", unsafe_allow_html=True)

# --- Header ---
col1, col2 = st.columns([9, 1])
with col1:
    st.title("👤 Manage Users")
with col2:
    if st.button("🚪 Logout", key="logout_btn"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.switch_page("app.py")

# --- Navbar ---
nav_col1, nav_col2, nav_col3 = st.columns(3)
with nav_col1:
    if st.button("🏢 Companies", use_container_width=True):
        st.switch_page("pages/admin_companies.py")
with nav_col2:
    st.button("👤 Users", disabled=True, use_container_width=True)
with nav_col3:
    if st.button("👑 Admins", use_container_width=True):
        st.switch_page("pages/admin_admins.py")

st.divider()

# --- Helper functions ---
def load_companies():
    if URL_JSON.exists():
        with open(URL_JSON, "r") as f:
            return [item["company"] for item in json.load(f)]
    return []

def add_user(email, password, company_name):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Check if user already exists
    cur.execute("SELECT 1 FROM users WHERE email=?", (email,))
    if cur.fetchone():
        st.error(f"❌ User with email '{email}' already exists.")
        conn.close()
        return

    # Get or create company
    cur.execute("SELECT id FROM companies WHERE name=?", (company_name,))
    row = cur.fetchone()
    if not row:
        cur.execute("INSERT INTO companies (name) VALUES (?)", (company_name,))
        company_id = cur.lastrowid
    else:
        company_id = row[0]

    cur.execute("INSERT INTO users (email, password, company_id) VALUES (?, ?, ?)", (email, password, company_id))
    conn.commit()
    conn.close()
    st.success(f"✅ User '{email}' added for {company_name}")

def delete_user(email):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE email=?", (email,))
    conn.commit()
    conn.close()
    st.warning(f"🗑️ Deleted user '{email}'")

# --- Add user ---
st.markdown("### ➕ Add New User")
companies = load_companies()
email = st.text_input("User Email", placeholder="john@crousemedicalpractice.com")
password = st.text_input("Password", type="password")
company_choice = st.selectbox("Select Company", options=companies)

if st.button("Add User"):
    if email and password and company_choice:
        add_user(email, password, company_choice)
    else:
        st.error("❌ Please fill all details.")

st.divider()

# --- Delete user (company-wise) ---
st.markdown("### 🗑️ Delete User")
selected_company = st.selectbox("Select Company to View Users", options=companies, key="del_company")

if selected_company:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT u.email FROM users u
        JOIN companies c ON u.company_id = c.id
        WHERE c.name = ?
    """, (selected_company,))
    users = [row[0] for row in cur.fetchall()]
    conn.close()

    if users:
        selected_user = st.selectbox("Select User to Delete", options=users)
        if st.button("Delete Selected User"):
            delete_user(selected_user)
    else:
        st.info(f"No users found for {selected_company}.")

st.divider()

# --- Show all users ---
st.subheader("📋 Current Users")
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("""
    SELECT u.email, u.password, c.name
    FROM users u LEFT JOIN companies c ON u.company_id = c.id
""")
rows = cur.fetchall()
conn.close()

if rows:
    st.dataframe(
        [{"Email": r[0], "Password": r[1], "Company": r[2]} for r in rows],
        use_container_width=True
    )
else:
    st.info("No users found yet.")
