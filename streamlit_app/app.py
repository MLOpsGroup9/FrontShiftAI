import streamlit as st
from utils.db_utils import init_db
from utils.auth_utils import verify_admin, verify_user, extract_company_from_email

st.set_page_config(
    page_title="FrontShiftAI Login",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Hide sidebar and hamburger menu
hide_sidebar = """
    <style>
        [data-testid="stSidebar"] {display: none;}
        [data-testid="collapsedControl"] {display: none;}
    </style>
"""
st.markdown(hide_sidebar, unsafe_allow_html=True)

# Initialize DB
init_db()

# Maintain session state
if "role" not in st.session_state:
    st.session_state.role = None

st.title("🔐 FrontShiftAI Login")

email = st.text_input("Email", placeholder="you@company.com")
password = st.text_input("Password", type="password")
login_btn = st.button("Login")

if login_btn:
    # --- Admin login ---
    if email == "admin@frontshiftai.com" and verify_admin(email, password):
        st.session_state.role = "admin"
        st.success("✅ Admin login successful!")
        # redirect to Companies page (first page in navbar)
        st.switch_page("pages/admin_companies.py")

    # --- User login ---
    elif verify_user(email, password):
        company = extract_company_from_email(email)
        st.session_state.role = "user"
        st.session_state.company = company
        st.session_state.email = email
        st.success(f"✅ Welcome {email}! Company: {company}")
        st.switch_page("pages/user_chat.py")

    # --- Invalid ---
    else:
        st.error("❌ Invalid credentials. Please check your email or password.")
