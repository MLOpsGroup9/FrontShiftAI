import streamlit as st

st.title("💬 User Chat (Coming Soon)")

if "company" in st.session_state:
    st.write(f"Connected to **{st.session_state.company}** handbook.")
else:
    st.error("No company info found. Please login again.")
