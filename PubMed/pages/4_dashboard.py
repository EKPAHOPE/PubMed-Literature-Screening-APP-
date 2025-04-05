# pages/dashboard.py
import streamlit as st
from visualization import get_yearly_publication_trends, get_journal_publication_counts, plot_yearly_trends, plot_journal_counts

st.title("Dashboard - Visualization Insights")

if st.session_state.authenticated:
    if st.session_state.search_results and st.session_state.search_results["count"] > 0:
        st.subheader(f"Visualizations for: {st.session_state.current_query}")
        st.success(f"Based on {st.session_state.search_results['count']} results.")
        
        tab1, tab2 = st.tabs(["Yearly Trends", "Top Journals"])
        with tab1:
            trends = get_yearly_publication_trends(st.session_state.search_results["articles"])
            plot_yearly_trends(trends)
        with tab2:
            counts = get_journal_publication_counts(st.session_state.search_results["articles"])
            plot_journal_counts(counts)
    elif st.session_state.search_results:
        st.warning("No results to visualize. Perform a search on the main page or via Chatbot.")
    else:
        st.info("Perform a search on the main page or Chatbot to see visualizations here.")
else:
    st.warning("Please log in to access the dashboard.")