import streamlit as st
import openai
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import time
import plotly.express as px
import plotly.graph_objs as go
import sqlite3
import bcrypt
import smtplib
import random
import string
from email.mime.text import MIMEText
import re
from dotenv import load_dotenv
import os 
load_dotenv()
st.set_page_config(page_title="PubMed Search", layout="wide")

# Base URLs for NCBI E-utilities
BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
EMAIL = "ebulamicheal@gmail.com"  # Your Gmail address
APP_PASSWORD = "emoe bukc enmk yege"  # Your Gmail App Password
TOOL = "streamlit-pubmed-app"

# OpenAI API Setup - Securely load API key from Streamlit secrets
try:
    openai.api_key = os.getenv("OPENAI_API_KEY")
except KeyError:
    st.error("OpenAI API key not found. Please add OPENAI_API_KEY to your Streamlit secrets.")
    st.stop()

# Database setup
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, email TEXT)''')
    conn.commit()
    conn.close()

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'otp' not in st.session_state:
    st.session_state.otp = None
if 'otp_email' not in st.session_state:
    st.session_state.otp_email = None
if 'conversation' not in st.session_state:
    st.session_state.conversation = []
if 'search_results' not in st.session_state:
    st.session_state.search_results = None
if 'current_query' not in st.session_state:
    st.session_state.current_query = None

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

def search_pubmed(query, max_results=20, start=0):
    search_url = f"{BASE_URL}esearch.fcgi"
    search_params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "retstart": start,
        "sort": "relevance",
        "retmode": "xml",
        "tool": TOOL,
        "email": EMAIL,
        "usehistory": "y"
    }
    try:
        search_response = requests.get(search_url, params=search_params)
        search_response.raise_for_status()
        search_tree = ET.fromstring(search_response.content)
        count_elem = search_tree.find(".//Count")
        count = int(count_elem.text) if count_elem is not None else 0
        webenv_elem = search_tree.find(".//WebEnv")
        query_key_elem = search_tree.find(".//QueryKey")
        if webenv_elem is None or query_key_elem is None:
            return {"count": 0, "articles": []}
        webenv = webenv_elem.text
        query_key = query_key_elem.text
        id_list = [id_elem.text for id_elem in search_tree.findall(".//IdList/Id")]
        if not id_list:
            return {"count": 0, "articles": []}
        fetch_url = f"{BASE_URL}efetch.fcgi"
        fetch_params = {
            "db": "pubmed",
            "retmode": "xml",
            "rettype": "abstract",
            "WebEnv": webenv,
            "query_key": query_key,
            "retmax": max_results,
            "tool": TOOL,
            "email": EMAIL
        }
        fetch_response = requests.get(fetch_url, params=fetch_params)
        fetch_response.raise_for_status()
        articles = parse_pubmed_xml(fetch_response.content)
        return {"count": count, "articles": articles}
    except requests.exceptions.RequestException as e:
        st.error(f"API request error: {e}")
        return {"count": 0, "articles": []}
    except ET.ParseError as e:
        st.error(f"XML parsing error: {e}")
        return {"count": 0, "articles": []}
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        return {"count": 0, "articles": []}

def parse_pubmed_xml(xml_content):
    root = ET.fromstring(xml_content)
    articles = []
    for article_elem in root.findall(".//PubmedArticle"):
        try:
            pmid = article_elem.find(".//PMID").text
            title_elem = article_elem.find(".//ArticleTitle")
            title = title_elem.text if title_elem is not None and title_elem.text else "No title available"
            abstract_parts = article_elem.findall(".//AbstractText")
            abstract = " ".join([part.text for part in abstract_parts if part.text]) if abstract_parts else "No abstract available"
            author_list = article_elem.findall(".//Author")
            authors = []
            for author in author_list:
                last_name = author.find("LastName")
                fore_name = author.find("ForeName")
                if last_name is not None and last_name.text:
                    author_name = last_name.text
                    if fore_name is not None and fore_name.text:
                        author_name = f"{fore_name.text} {author_name}"
                    authors.append(author_name)
            journal_elem = article_elem.find(".//Journal/Title")
            journal = journal_elem.text if journal_elem is not None else "Unknown Journal"
            year_elem = article_elem.find(".//PubDate/Year")
            year = year_elem.text if year_elem is not None else "Unknown Year"
            month_elem = article_elem.find(".//PubDate/Month")
            month = month_elem.text if month_elem is not None else ""
            pub_date = f"{month} {year}".strip()
            doi = None
            article_ids = article_elem.findall(".//ArticleId")
            for id_elem in article_ids:
                if id_elem.get("IdType") == "doi" and id_elem.text:
                    doi = id_elem.text
                    break
            article = {
                "pmid": pmid,
                "title": title,
                "abstract": abstract,
                "authors": ", ".join(authors) if authors else "Unknown",
                "journal": journal,
                "pub_date": pub_date,
                "year": year,
                "doi": doi,
                "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            }
            articles.append(article)
        except Exception as e:
            st.warning(f"Error parsing article: {e}")
            continue
    return articles

def get_yearly_publication_trends(articles):
    yearly_trends = {}
    for article in articles:
        year = article.get('year', 'Unknown')
        if year != 'Unknown':
            yearly_trends[year] = yearly_trends.get(year, 0) + 1
    return dict(sorted(yearly_trends.items(), key=lambda x: x[0]))

def get_journal_publication_counts(articles):
    journal_counts = {}
    for article in articles:
        journal = article.get('journal', 'Unknown')
        journal_counts[journal] = journal_counts.get(journal, 0) + 1
    return dict(sorted(journal_counts.items(), key=lambda x: x[1], reverse=True)[:10])

def registration_page():
    st.title("Register")
    if st.session_state.otp is None:
        with st.form(key='email_form'):
            email = st.text_input("Email")
            submit_email = st.form_submit_button(label="Send OTP")
            if submit_email:
                if not email:
                    st.error("Please enter an email address")
                else:
                    otp = generate_otp()
                    if send_otp_email(email, otp):
                        st.session_state.otp = otp
                        st.session_state.otp_email = email
                        st.success("OTP sent to your email. Check your inbox (and spam folder).")
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
                else:
                    conn = sqlite3.connect('users.db')
                    c = conn.cursor()
                    try:
                        hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
                        c.execute("INSERT INTO users (username, password, email) VALUES (?, ?, ?)",
                                  (username, hashed_pw, st.session_state.otp_email))
                        conn.commit()
                        st.session_state.otp = None
                        st.session_state.otp_email = None
                        st.success("Registration successful! Please login.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Username already exists")
                    finally:
                        conn.close()

def login_page():
    st.title("Login")
    with st.form(key='login_form'):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit_button = st.form_submit_button(label="Login")
        if submit_button:
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute("SELECT password FROM users WHERE username = ?", (username,))
            result = c.fetchone()
            conn.close()
            if result:
                stored_password = result[0]
                if bcrypt.checkpw(password.encode(), stored_password):
                    st.session_state.authenticated = True
                    st.session_state.current_user = username
                    st.success(f"Welcome, {username}!")
                    st.rerun()
                else:
                    st.error("Incorrect password")
            else:
                st.error("Username not found")

# Chatbot Functions
def get_chatbot_response(user_input):
    system_prompt = {
        "role": "system",
        "content": (
            "You are a helpful assistant for a PubMed search application. "
            "Assist users with formulating search queries, interpreting results, and providing guidance. "
            "When asked to search, include `[SEARCH: query]` in your response to trigger a search. "
            "For example, if the user says 'find studies on diabetes', respond with '[SEARCH: diabetes]'. "
            "If the user provides a simple term like 'breast cancer', respond with '[SEARCH: breast cancer]'. "
            "Provide clear and concise answers, and offer tips on PubMed syntax when relevant."
        )
    }
    st.session_state.conversation.append({"role": "user", "content": user_input})
    try:
        # Updated to use the new OpenAI API syntax
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[system_prompt] + st.session_state.conversation,
            temperature=0.7
        )
        # Extract the assistant's message from the new response structure
        assistant_message = response.choices[0].message.content
        st.session_state.conversation.append({"role": "assistant", "content": assistant_message})
        return assistant_message
    except Exception as e:
        error_message = f"Error with OpenAI API: {str(e)}"
        st.session_state.conversation.append({"role": "assistant", "content": error_message})
        st.error(error_message)
        return error_message

def process_search_command(response):
    search_pattern = r"\[SEARCH:\s*(.*?)\]"
    match = re.search(search_pattern, response)
    if match:
        query = match.group(1).strip()
        st.session_state.current_query = query
        with st.spinner("Performing PubMed search..."):
            result = search_pubmed(query)
            st.session_state.search_results = result
        return True
    return False

def search_page():
    st.title("PubMed Literature Search with AI Chatbot")
    
    # Chat interface
    st.subheader("Chat with the Assistant")
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.conversation:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    
    user_input = st.chat_input("Ask me anything about PubMed searches...")
    if user_input:
        assistant_response = get_chatbot_response(user_input)
        if process_search_command(assistant_response):
            assistant_response += "\n\nSearch performed. See results below."
        st.rerun()

    # Sidebar for manual search
    with st.sidebar:
        if st.session_state.authenticated:
            st.write(f"Logged in as: {st.session_state.current_user}")
            if st.button("Logout"):
                st.session_state.authenticated = False
                st.session_state.current_user = None
                st.session_state.conversation = []
                st.session_state.search_results = None
                st.rerun()
        
        st.header("Manual Search Options")
        query = st.text_input("Enter search terms:", help="Enter keywords, author names, or MeSH terms")
        with st.expander("Advanced Options"):
            max_results = st.slider("Results per page:", min_value=5, max_value=100, value=20, step=5)
            sort_by = st.selectbox("Sort by:", ["Relevance", "Most Recent", "First Author"])
            st.subheader("Date Range")
            col1, col2 = st.columns(2)
            with col1:
                start_year = st.number_input("From year:", min_value=1800, max_value=2025, value=2020)
            with col2:
                end_year = st.number_input("To year:", min_value=1800, max_value=2025, value=2025)
            use_date_range = st.checkbox("Apply date filter")
            st.subheader("Publication Types")
            filter_books = st.checkbox("Books and Documents")
            filter_clinical = st.checkbox("Clinical Trial")
            filter_meta = st.checkbox("Meta-Analysis")
            filter_rct = st.checkbox("Randomized Controlled Trial")
            filter_review = st.checkbox("Review")
            filter_systematic = st.checkbox("Systematic Review")
        search_button = st.button("Search PubMed")

    # Handle manual search
    if search_button and query:
        full_query = query
        if use_date_range:
            date_query = f" AND ({start_year}[PDAT]:{end_year}[PDAT])"
            full_query += date_query
        pub_types = []
        if filter_books:
            pub_types.append('"Book" OR "Document"')
        if filter_clinical:
            pub_types.append('"Clinical Trial"[PT]')
        if filter_meta:
            pub_types.append('"Meta-Analysis"[PT]')
        if filter_rct:
            pub_types.append('"Randomized Controlled Trial"[PT]')
        if filter_review:
            pub_types.append('"Review"[PT]')
        if filter_systematic:
            pub_types.append('"Systematic Review"[PT]')
        if pub_types:
            full_query += " AND (" + " OR ".join(pub_types) + ")"
        st.write(f"Searching: `{full_query}`")
        with st.spinner("Searching PubMed..."):
            time.sleep(0.33)
            result = search_pubmed(full_query, max_results=max_results)
            st.session_state.search_results = result
            st.session_state.current_query = full_query
            st.rerun()

    # Display search results (from either chatbot or manual search)
    if st.session_state.search_results:
        st.subheader("Search Results")
        result = st.session_state.search_results
        if result is not None and isinstance(result, dict) and "count" in result:
            if result["count"] > 0:
                st.success(f"Found {result['count']} results. Showing {len(result['articles'])} articles.")
                tab1, tab2, tab3 = st.tabs(["Search Results", "Publication Trends", "Top Journals"])
                with tab1:
                    for i, article in enumerate(result["articles"]):
                        with st.expander(f"{i+1}. {article['title']}", expanded=i==0):
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                st.markdown(f"**Authors:** {article['authors']}")
                                st.markdown(f"**Journal:** {article['journal']}")
                                st.markdown(f"**Published:** {article['pub_date']}")
                                st.markdown("### Abstract")
                                st.markdown(article['abstract'])
                            with col2:
                                st.markdown("### Links")
                                st.markdown(f"[View on PubMed]({article['pubmed_url']})")
                                if article['doi']:
                                    st.markdown(f"[DOI: {article['doi']}](https://doi.org/{article['doi']})")
                                st.markdown("### Citation")
                                citation = f"{article['authors']}. {article['title']}. *{article['journal']}*. {article['pub_date']}."
                                st.markdown(citation)
                    if result["articles"]:
                        df = pd.DataFrame(result["articles"])
                        csv = df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="Download results as CSV",
                            data=csv,
                            file_name=f"pubmed_search_{st.session_state.current_query.replace(' ', '_')}.csv",
                            mime='text/csv',
                        )
                with tab2:
                    yearly_trends = get_yearly_publication_trends(result["articles"])
                    st.subheader("Yearly Publication Trends")
                    line_fig = go.Figure(data=go.Scatter(
                        x=list(yearly_trends.keys()), 
                        y=list(yearly_trends.values()), 
                        mode='lines+markers',
                        line=dict(color='blue', width=3),
                        marker=dict(size=10)
                    ))
                    line_fig.update_layout(
                        title="Publication Trends Over Years",
                        xaxis_title="Year",
                        yaxis_title="Number of Publications"
                    )
                    st.plotly_chart(line_fig, use_container_width=True)
                with tab3:
                    journal_counts = get_journal_publication_counts(result["articles"])
                    st.subheader("Top 10 Journals")
                    bar_fig = go.Figure(data=go.Bar(
                        x=list(journal_counts.keys()), 
                        y=list(journal_counts.values()),
                        marker_color='green'
                    ))
                    bar_fig.update_layout(
                        title="Publication Distribution Across Journals",
                        xaxis_title="Journal",
                        yaxis_title="Number of Publications",
                        xaxis_tickangle=-90
                    )
                    st.plotly_chart(bar_fig, use_container_width=True)
            else:
                st.warning("No results found. Try modifying your search terms.")
        else:
            st.error("Search failed. Please try again or check your internet connection.")
    elif not st.session_state.conversation:
        st.markdown("""
        ## Welcome to the PubMed Search Tool
        
        This tool allows you to search through millions of biomedical literature citations and abstracts from MEDLINE, life science journals, and online books using the PubMed API.
        
        ### Search Tips:
        - Use quotation marks for exact phrases: `"breast cancer"`
        - Combine terms with AND, OR, NOT: `cancer AND therapy NOT metastatic`
        - Use author search: `Smith J[Author]`
        - Use MeSH terms with tags: `Neoplasms[MeSH]`
        - Filter by publication type in Advanced Options
        - Chat with the assistant above for help!
        
        Enter your search terms in the sidebar or ask the chatbot to begin.
        """)

def main():
    init_db()
    if not st.session_state.authenticated:
        page = st.sidebar.selectbox("Select Page", ["Login", "Register"])
        if page == "Login":
            login_page()
        else:
            registration_page()
    else:
        search_page()
    st.markdown("---")
    st.markdown("""
    **Note:** This application uses the NCBI E-utilities API to search PubMed. Please be mindful of [NCBI's usage policies](https://www.ncbi.nlm.nih.gov/home/about/policies/).
    """)

if __name__ == "__main__":
    main()