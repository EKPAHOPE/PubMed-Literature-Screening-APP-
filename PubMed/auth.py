# auth.py
import streamlit as st
import smtplib
import random
import string
from email.mime.text import MIMEText
from config import EMAIL, APP_PASSWORD
from database import register_user

def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))

def send_otp_email(email, otp):
    try:
        msg = MIMEText(f"Your OTP for registration is: {otp}")
        msg['Subject'] = 'PubMed Search Registration OTP'
        msg['From'] = EMAIL
        msg['To'] = email
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL, APP_PASSWORD.replace(" ", ""))
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Failed to send OTP: {e}")
        return False

def registration_page():
    st.title("Register")
    if st.session_state.get('otp') is None:
        with st.form(key='email_form'):
            email = st.text_input("Email")
            submit_email = st.form_submit_button(label="Send OTP")
            if submit_email and email:
                otp = generate_otp()
                if send_otp_email(email, otp):
                    st.session_state.otp = otp
                    st.session_state.otp_email = email
                    st.success("OTP sent to your email.")
                    st.rerun()
    else:
        with st.form(key='registration_form'):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            otp_input = st.text_input("Enter OTP from email")
            submit_button = st.form_submit_button(label="Register")
            if submit_button:
                if not all([username, password, otp_input]):
                    st.error("Please fill in all fields")
                elif password != confirm_password:
                    st.error("Passwords do not match")
                elif otp_input != st.session_state.otp:
                    st.error("Invalid OTP")
                elif register_user(username, password, st.session_state.otp_email):
                    st.session_state.otp = None
                    st.session_state.otp_email = None
                    st.success("Registration successful! Please login.")
                    st.rerun()
                else:
                    st.error("Username already exists")

def login_page():
    st.title("Login")
    with st.form(key='login_form'):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit_button = st.form_submit_button(label="Login")
        if submit_button:
            from database import verify_user
            if verify_user(username, password):
                st.session_state.authenticated = True
                st.session_state.current_user = username
                st.success(f"Welcome, {username}!")
                st.rerun()
            else:
                st.error("Invalid username or password")