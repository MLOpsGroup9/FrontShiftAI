import streamlit as st
import json
from pathlib import Path

PROJECT_ROOT = Path("/Users/sriks/Documents/Projects/FrontShiftAI")
URL_JSON = PROJECT_ROOT / "data_pipeline" / "data" / "url.json"

st.set_page_config(page_title="Admin - Companies", layout="wide", initial_sidebar_state="collapsed")

# Hide sidebar & toolbar
st.markdown("""
    <style>
        [data-testid="stSidebar"], [data-testid="collapsedControl"], div[data-testid="stToolbar"] {display: none;}
        .logout-btn {position: fixed; top: 15px; right: 30px;}
    </style>
""", unsafe_allow_html=True)

# --- Header ---
col1, col2 = st.columns([9, 1])
with col1:
    st.title("🏢 Manage Companies")
with col2:
    if st.button("🚪 Logout", key="logout_btn"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.switch_page("app.py")

# --- Navbar ---
nav_col1, nav_col2, nav_col3 = st.columns(3)
with nav_col1:
    st.button("🏢 Companies", disabled=True, use_container_width=True)
with nav_col2:
    if st.button("👤 Users", use_container_width=True):
        st.switch_page("pages/admin_users.py")
with nav_col3:
    if st.button("👑 Admins", use_container_width=True):
        st.switch_page("pages/admin_admins.py")

st.divider()

# --- Load and Add Companies ---
def load_companies():
    if URL_JSON.exists():
        with open(URL_JSON, "r") as f:
            data = json.load(f)
            return data
    return []

def add_company(domain, company, url):
    data = load_companies()
    data.append({"domain": domain, "company": company, "url": url})
    with open(URL_JSON, "w") as f:
        json.dump(data, f, indent=4)
    st.success(f"✅ Added company '{company}' to url.json")

# Add form
with st.expander("➕ Add New Company"):
    domain = st.text_input("Domain", placeholder="e.g., Healthcare, Retail, Construction")
    company = st.text_input("Company Name", placeholder="e.g., Nova Tech Industries")
    url = st.text_input("Company Handbook URL", placeholder="https://example.com/handbook.pdf")
    if st.button("Add Company"):
        if domain and company and url:
            add_company(domain, company, url)
        else:
            st.error("Please fill all fields")

st.divider()

# Display companies
companies = load_companies()
if companies:
    st.dataframe(companies, use_container_width=True)
else:
    st.info("No companies found.")
