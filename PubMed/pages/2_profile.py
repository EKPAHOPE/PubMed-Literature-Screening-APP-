# pages/profile.py
import streamlit as st
import sqlite3

st.title("User Profile")

def get_user_info(username):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT username, email FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    return {"username": result[0], "email": result[1]} if result else None

if st.session_state.authenticated:
    user_info = get_user_info(st.session_state.current_user)
    if user_info:
        st.subheader(f"Welcome, {user_info['username']}!")
        st.markdown(f"**Email:** {user_info['email']}")
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.current_user = None
            st.session_state.conversation = []
            st.session_state.search_results = None
            st.rerun()
    else:
        st.error("User data not found.")
else:
    st.warning("Please log in to view your profile.")
    st.markdown("[Go to Login](#)")  # Placeholder link; Streamlit handles navigation via sidebar