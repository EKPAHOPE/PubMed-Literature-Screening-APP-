# app.py
import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from database import init_db
from auth import login_page, registration_page
from pubmed_api import search_pubmed
from chatbot_logic import get_chatbot_response, process_search_command, detect_medical_terms

# Load environment variables
load_dotenv()

st.set_page_config(page_title="PubMed Search App", layout="wide")

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'otp' not in st.session_state:
    st.session_state.otp = None
if 'conversation' not in st.session_state:
    st.session_state.conversation = []
if 'search_results' not in st.session_state:
    st.session_state.search_results = None
if 'current_query' not in st.session_state:
    st.session_state.current_query = None
if 'page_number' not in st.session_state:
    st.session_state.page_number = 0
if 'sort_by' not in st.session_state:
    st.session_state.sort_by = "Relevance"
if 'webenv' not in st.session_state:
    st.session_state.webenv = None
if 'query_key' not in st.session_state:
    st.session_state.query_key = None
# New session state variables for enhanced features
if 'explained_terms' not in st.session_state:
    st.session_state.explained_terms = {}
if 'detected_methodologies' not in st.session_state:
    st.session_state.detected_methodologies = []
if 'pending_terms_explanation' not in st.session_state:
    st.session_state.pending_terms_explanation = None
if 'pending_terms_article' not in st.session_state:
    st.session_state.pending_terms_article = None
if 'pending_methodology_analysis' not in st.session_state:
    st.session_state.pending_methodology_analysis = None
if 'pending_methodology_article' not in st.session_state:
    st.session_state.pending_methodology_article = None
if 'pending_gap_analysis' not in st.session_state:
    st.session_state.pending_gap_analysis = False
if 'pending_research_questions' not in st.session_state:
    st.session_state.pending_research_questions = False

def init_nltk():
    """Initialize NLTK resources if needed"""
    try:
        nltk.data.find('tokenizers/punkt')
        nltk.data.find('corpora/stopwords')
    except LookupError:
        with st.spinner("Downloading language resources (one-time setup)..."):
            nltk.download('punkt')
            nltk.download('stopwords')

def search_page():
    st.title("PubMed Literature Search")
    RESULTS_PER_PAGE = 50

    # Define sort mapping at function scope
    sort_mapping = {
        "Relevance": "relevance",
        "Most Recent": "date",
        "First Author": "author"
    }

    # Sidebar for manual search
    with st.sidebar:
        if st.session_state.authenticated:
            st.write(f"Logged in as: {st.session_state.current_user}")
            if st.button("Logout"):
                st.session_state.authenticated = False
                st.session_state.current_user = None
                st.session_state.conversation = []
                st.session_state.search_results = None
                st.session_state.page_number = 0
                st.session_state.sort_by = "Relevance"
                st.session_state.webenv = None
                st.session_state.query_key = None
                st.rerun()
        
        st.header("Manual Search Options")
        query = st.text_input("Enter search terms:", help="Enter keywords, author names, or MeSH terms")
        with st.expander("Advanced Options"):
            st.session_state.sort_by = st.selectbox("Sort by:", ["Relevance", "Most Recent", "First Author"], index=["Relevance", "Most Recent", "First Author"].index(st.session_state.sort_by))
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
        
        # Add AI Research Assistant button in sidebar
        st.markdown("---")
        st.subheader("AI Research Assistant")
        if st.button("Open Assistant"):
            st.switch_page("pages/4_chatbot.py")

    # Handle manual search
    if search_button and query:
        full_query = query
        if use_date_range:
            full_query += f" AND ({start_year}[PDAT]:{end_year}[PDAT])"
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
        st.session_state.current_query = full_query
        st.session_state.page_number = 0  # Reset to first page
        with st.spinner("Searching PubMed..."):
            start = st.session_state.page_number * RESULTS_PER_PAGE
            initial_results = search_pubmed(full_query, max_results=RESULTS_PER_PAGE, start=start, sort=sort_mapping[st.session_state.sort_by])
            st.session_state.search_results = initial_results
            st.session_state.webenv = initial_results["webenv"]
            st.session_state.query_key = initial_results["query_key"]
        st.rerun()

    # Display search results with pagination
    if st.session_state.search_results and st.session_state.search_results["count"] > 0:
        total_results = st.session_state.search_results["count"]
        current_page = st.session_state.page_number
        total_pages = (total_results + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE
        
        st.subheader(f"Results for: {st.session_state.current_query}")
        st.success(f"Found {total_results} results. Showing page {current_page + 1} of {total_pages} ({len(st.session_state.search_results['articles'])} articles).")
        
        # Display current page results
        for i, article in enumerate(st.session_state.search_results["articles"]):
            with st.expander(f"{i + 1 + (current_page * RESULTS_PER_PAGE)}. {article['title']}", expanded=i==0):
                # Main columns for article display
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**Authors:** {article['authors']}")
                    st.markdown(f"**Journal:** {article['journal']}")
                    st.markdown(f"**Published:** {article['pub_date']}")
                    st.markdown("### Abstract")
                    st.markdown(article['abstract'])
                    
                    # Add enhanced features for medical terms directly in the main content
                    if article['abstract'] != "No abstract available":
                        medical_terms = detect_medical_terms(article['abstract'])
                        if medical_terms:
                            st.markdown("### 📚 Medical Terms Detected")
                            st.write("The following medical terms were detected in this abstract:")
                            terms_list = ", ".join(medical_terms)
                            st.info(terms_list)
                            if st.button(f"Explain These Terms", key=f"explain_{i}"):
                                # Add both the user query and a placeholder response
                                st.session_state.conversation.append({
                                    "role": "user", 
                                    "content": f"Explain these medical terms from article #{i+1}: {terms_list}"
                                })
                                st.session_state.conversation.append({
                                    "role": "assistant", 
                                    "content": f"Processing request to explain: {terms_list}... Please wait."
                                })
                                # Set a flag to trigger immediate processing when the chatbot page loads
                                st.session_state.pending_terms_explanation = terms_list
                                st.session_state.pending_terms_article = i+1
                                st.switch_page("pages/4_chatbot.py")
                
                with col2:
                    st.markdown("### Links")
                    st.markdown(f"[View on PubMed]({article['pubmed_url']})")
                    if article['doi']:
                        st.markdown(f"[DOI: {article['doi']}](https://doi.org/{article['doi']})")
                    st.markdown("### Citation")
                    citation = f"{article['authors']}. {article['title']}. *{article['journal']}*. {article['pub_date']}."
                    st.markdown(citation)
                    
                    # Add AI analysis buttons
                    st.markdown("### AI Analysis")
                    if st.button("🔬 Analyze Methodology", key=f"method_{i}"):
                        # Add both the user query and a placeholder response
                        abstract = article['abstract']
                        st.session_state.conversation.append({
                            "role": "user", 
                            "content": f"Analyze the methodology in this abstract #{i+1}"
                        })
                        st.session_state.conversation.append({
                            "role": "assistant", 
                            "content": "Analyzing research methodology... Please wait."
                        })
                        # Set a flag to trigger immediate processing
                        st.session_state.pending_methodology_analysis = abstract
                        st.session_state.pending_methodology_article = i+1
                        st.switch_page("pages/4_chatbot.py")

        # Pagination controls
        col1, col2, col3 = st.columns([1, 1, 3])
        with col1:
            if st.button("Previous", disabled=current_page <= 0):
                st.session_state.page_number -= 1
                start = st.session_state.page_number * RESULTS_PER_PAGE
                with st.spinner("Loading previous page..."):
                    st.session_state.search_results = search_pubmed(
                        st.session_state.current_query, max_results=RESULTS_PER_PAGE, start=start,
                        sort=sort_mapping[st.session_state.sort_by], webenv=st.session_state.webenv, query_key=st.session_state.query_key
                    )
                st.rerun()
        with col2:
            if st.button("Next", disabled=(current_page + 1) >= total_pages):
                st.session_state.page_number += 1
                start = st.session_state.page_number * RESULTS_PER_PAGE
                with st.spinner("Loading next page..."):
                    st.session_state.search_results = search_pubmed(
                        st.session_state.current_query, max_results=RESULTS_PER_PAGE, start=start,
                        sort=sort_mapping[st.session_state.sort_by], webenv=st.session_state.webenv, query_key=st.session_state.query_key
                    )
                st.rerun()
        
        # Research gap analysis for current results
        st.markdown("---")
        st.subheader("Research Analysis")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🧩 Find Research Gaps in These Results"):
                # Add both the user query and a placeholder response
                st.session_state.conversation.append({
                    "role": "user", 
                    "content": f"Find research gaps in my search results for: {st.session_state.current_query}"
                })
                st.session_state.conversation.append({
                    "role": "assistant", 
                    "content": "Analyzing research gaps... Please wait. This may take a moment."
                })
                # Set a flag to trigger immediate processing
                st.session_state.pending_gap_analysis = True
                st.switch_page("pages/4_chatbot.py")
        with col2:
            if st.button("💡 Suggest Related Research Questions"):
                st.session_state.conversation.append({
                    "role": "user", 
                    "content": f"Suggest related research questions based on my search for: {st.session_state.current_query}"
                })
                st.session_state.conversation.append({
                    "role": "assistant", 
                    "content": "Generating research questions... Please wait. This may take a moment."
                })
                # Set a flag to trigger immediate processing
                st.session_state.pending_research_questions = True
                st.switch_page("pages/4_chatbot.py")

        # Download options
        df = pd.DataFrame(st.session_state.search_results["articles"])
        st.download_button(
            label=f"Download Page {current_page + 1} as CSV",
            data=df.to_csv(index=False).encode('utf-8'),
            file_name=f"pubmed_{st.session_state.current_query.replace(' ', '_')}_page_{current_page + 1}.csv",
            mime='text/csv'
        )
        st.info("View visualizations on the Dashboard page.")
    elif st.session_state.search_results:
        st.warning("No results found. Try a different query.")
    elif st.session_state.authenticated:
        st.markdown("""
        ## Welcome to the PubMed Search Tool
        
        This enhanced version includes AI-powered research assistance features:
        
        - **Term Explanations**: Get plain-language explanations of complex medical terminology
        - **Research Gap Analysis**: Identify potential underexplored areas in your field
        - **Methodology Analysis**: Understand the research methods used in studies
        
        Use the sidebar to search PubMed or navigate to the AI Research Assistant for more help.
        """)
        
        # Quick access buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔍 Start Searching"):
                st.session_state.current_page = "search"
        with col2:
            if st.button("🤖 Ask Research Assistant"):
                st.switch_page("pages/4_chatbot.py")

def check_environment():
    """Check if required environment variables are set"""
    missing_vars = []
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        missing_vars.append("OPENAI_API_KEY")
    
    if missing_vars:
        st.sidebar.warning(f"Missing environment variables: {', '.join(missing_vars)}")
        with st.sidebar.expander("Environment Setup Help"):
            st.markdown("""
            ### Setting up environment variables
            
            1. Create a `.env` file in the project root directory
            2. Add the following lines with your actual API keys:
            ```
            OPENAI_API_KEY=your_openai_api_key_here
            GMAIL_ADDRESS=your_email@gmail.com
            GMAIL_APP_PASSWORD=your_app_password
            ```
            3. Restart the application
            """)
        return False
    return True

def main():
    # Initialize resources
    init_db()
    
    # Check environment variables
    env_ok = check_environment()
    
    # Main app flow
    if not st.session_state.authenticated:
        page = st.sidebar.selectbox("Select Page", ["Login", "Register"])
        if page == "Login":
            login_page()
        else:
            registration_page()
    else:
        if not env_ok:
            st.warning("Some features may not work properly due to missing environment variables.")
        search_page()

if __name__ == "__main__":
    main()