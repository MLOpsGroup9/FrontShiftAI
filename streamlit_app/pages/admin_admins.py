import streamlit as st
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path("/Users/sriks/Documents/Projects/FrontShiftAI")
DB_PATH = PROJECT_ROOT / "streamlit_app" / "data" / "app_users.db"

st.set_page_config(page_title="Admin - Admins", layout="wide", initial_sidebar_state="collapsed")

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
    st.title("👑 Manage Admins")
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
    if st.button("👤 Users", use_container_width=True):
        st.switch_page("pages/admin_users.py")
with nav_col3:
    st.button("👑 Admins", disabled=True, use_container_width=True)

st.divider()

# --- Helper functions ---
def get_all_admins():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT email, password FROM admin")
    rows = cur.fetchall()
    conn.close()
    return rows

def add_admin(email, password):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Prevent duplicate admins
    cur.execute("SELECT 1 FROM admin WHERE email=?", (email,))
    if cur.fetchone():
        st.error(f"❌ Admin with email '{email}' already exists.")
        conn.close()
        return

    cur.execute("INSERT INTO admin (email, password) VALUES (?, ?)", (email, password))
    conn.commit()
    conn.close()
    st.success(f"✅ Added admin '{email}' successfully!")

def delete_admin(email):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM admin")
    count = cur.fetchone()[0]
    if count <= 1:
        st.warning("⚠️ Cannot delete the only remaining admin.")
        conn.close()
        return
    cur.execute("DELETE FROM admin WHERE email=?", (email,))
    conn.commit()
    conn.close()
    st.warning(f"🗑️ Deleted admin '{email}'")

# --- Add admin ---
st.markdown("### ➕ Add New Admin")
email = st.text_input("Admin Email", placeholder="newadmin@frontshiftai.com")
password = st.text_input("Password", type="password", key="admin_pw")

if st.button("Add Admin"):
    if email and password:
        add_admin(email, password)
    else:
        st.error("❌ Please fill all fields.")

st.divider()

# --- Delete admin ---
st.markdown("### 🗑️ Delete Admin")
admins = get_all_admins()
if admins:
    selected_admin = st.selectbox("Select Admin to Delete", options=[a[0] for a in admins])
    if len(admins) > 1:
        if st.button("Delete Admin"):
            delete_admin(selected_admin)
    else:
        st.info("⚠️ Only one admin exists — deletion disabled.")
else:
    st.info("No admins found in the database.")

st.divider()

# --- List all admins ---
st.subheader("📋 Current Admins")
if admins:
    st.dataframe(
        [{"Email": a[0], "Password": a[1]} for a in admins],
        use_container_width=True
    )
else:
    st.info("No admins found yet.")
