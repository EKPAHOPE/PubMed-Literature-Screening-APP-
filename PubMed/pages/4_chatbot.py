# pages/4_chatbot.py - Updated Version
import streamlit as st
import re
import openai
import os
from dotenv import load_dotenv

# Import the existing modules
from chatbot_logic import get_chatbot_response, process_search_command
from user_experience import (
    init_user_experience, 
    process_command, 
    user_preference_ui, 
    display_tutorial, 
    display_tutorial_prompt
)
from advanced_research import (
    init_advanced_research,
    process_advanced_command,
    render_study_comparison,
    render_literature_review
)

# Load environment variables
load_dotenv()

st.set_page_config(page_title="PubMed Research Assistant", layout="wide")

# Initialize user experience features
init_user_experience()

# Initialize advanced research features
init_advanced_research()

# Check authentication
if not st.session_state.authenticated:
    st.warning("Please log in to use the Research Assistant.")
    st.stop()

# Setup XML response rendering
def render_xml_response(xml_string):
    """Identify and render different types of XML responses"""
    # Check response type
    type_match = re.search(r'<response type="([^"]+)">', xml_string, re.DOTALL)
    response_type = type_match.group(1) if type_match else "general"
    
    if response_type == "study_comparison":
        render_study_comparison(xml_string)
    elif response_type == "literature_review":
        render_literature_review(xml_string)
    elif response_type == "export":
        # Handle export
        export_match = re.search(r'<content>(.*?)</content>', xml_string, re.DOTALL)
        export_type = export_match.group(1) if export_match else None
        
        if export_type == "literature_review":
            from advanced_research import export_to_csv
            csv_data = export_to_csv("literature_review")
            if csv_data:
                topic = st.session_state.literature_review.get("query", "review").replace(" ", "_")
                st.download_button(
                    label="Download Literature Review Data",
                    data=csv_data,
                    file_name=f"literature_review_{topic}.csv",
                    mime="text/csv",
                )
                st.success("Your export is ready for download!")
            else:
                st.error("Could not export data. Please try generating the literature review again.")
    else:
        # Use the existing XML renderer for other types
        from xml_formatter import render_xml_response as base_render
        base_render(xml_string)

# Display user preferences in sidebar
with st.sidebar:
    st.title("PubMed Assistant")
    st.write(f"Logged in as: {st.session_state.current_user}")
    
    # Add user preferences UI
    user_preference_ui()
    
    # Advanced features section
    st.markdown("---")
    st.subheader("Advanced Features")
    
    # Create tabs for different feature categories
    feature_tabs = st.tabs(["Analysis", "Exporting", "Help"])
    
    with feature_tabs[0]:
        st.markdown("""
        ### Analysis Commands
        - `/compare [#] [#]` - Compare studies
        - `/review [topic]` - Generate literature review
        """)
    
    with feature_tabs[1]:
        st.markdown("""
        ### Export Commands
        - `/export review` - Export literature review
        """)
    
    with feature_tabs[2]:
        st.markdown("""
        ### Getting Help
        - `/help` - Show all commands
        - `/tutorial` - Start interactive tutorial
        - `/help [command]` - Get help on specific command
        """)
    
    # Navigation buttons
    st.markdown("---")
    if st.button("Return to Search"):
        st.switch_page("app.py")

st.title("PubMed Research Assistant")

# First check if there are pending operations from other pages
pending_operation = False

if st.session_state.pending_terms_explanation:
    terms = st.session_state.pending_terms_explanation
    article_num = st.session_state.pending_terms_article
    
    # Remove the placeholder response
    if len(st.session_state.conversation) >= 2:
        st.session_state.conversation.pop()
    
    # Generate and add the real response
    response = get_chatbot_response(f"Explain these medical terms from article #{article_num}: {terms}")
    st.session_state.conversation[-1]["content"] = response
    
    # Clear the pending flag
    st.session_state.pending_terms_explanation = None
    st.session_state.pending_terms_article = None
    pending_operation = True

elif st.session_state.pending_methodology_analysis:
    abstract = st.session_state.pending_methodology_analysis
    article_num = st.session_state.pending_methodology_article
    
    # Remove the placeholder response
    if len(st.session_state.conversation) >= 2:
        st.session_state.conversation.pop()
    
    # Generate and add the real response
    response = get_chatbot_response(f"Analyze the methodology in abstract #{article_num}")
    st.session_state.conversation[-1]["content"] = response
    
    # Clear the pending flag
    st.session_state.pending_methodology_analysis = None
    st.session_state.pending_methodology_article = None
    pending_operation = True

elif st.session_state.pending_gap_analysis:
    # Remove the placeholder response
    if len(st.session_state.conversation) >= 2:
        st.session_state.conversation.pop()
    
    # Generate and add the real response
    response = get_chatbot_response("Find research gaps in the current search results")
    st.session_state.conversation[-1]["content"] = response
    
    # Clear the pending flag
    st.session_state.pending_gap_analysis = False
    pending_operation = True

elif st.session_state.pending_research_questions:
    # Remove the placeholder response
    if len(st.session_state.conversation) >= 2:
        st.session_state.conversation.pop()
    
    # Generate and add the real response
    response = get_chatbot_response("Suggest related research questions")
    st.session_state.conversation[-1]["content"] = response
    
    # Clear the pending flag
    st.session_state.pending_research_questions = False
    pending_operation = True

# Display tutorial prompt for new users
if not pending_operation:
    display_tutorial_prompt()

# Display active tutorial if it's being shown
display_tutorial()

# Display conversation history
for i, message in enumerate(st.session_state.conversation):
    if message["role"] == "user":
        st.markdown(f"**You:** {message['content']}")
    else:
        # Check if the message content should be rendered as XML
        content = message['content']
        format_type = message.get('format', 'text')
        
        if format_type == 'xml' or content.startswith('<response'):
            st.markdown("**Assistant:**")
            render_xml_response(content)
        else:
            st.markdown(f"**Assistant:** {content}")

# Input for new messages
with st.form(key="message_form", clear_on_submit=True):
    user_input = st.text_area("Enter your message:", height=100)
    submit_button = st.form_submit_button("Send")

    if submit_button and user_input:
        # First check if this is a UX command (help, tutorial, preferences)
        ux_response = process_command(user_input)
        
        if ux_response:
            # Add both user input and command response to conversation
            st.session_state.conversation.append({"role": "user", "content": user_input})
            st.session_state.conversation.append({"role": "assistant", "content": ux_response})
        else:
            # Check if this is an advanced research command
            advanced_response = process_advanced_command(user_input)
            
            if advanced_response:
                # Add both user input and advanced command response to conversation
                st.session_state.conversation.append({"role": "user", "content": user_input})
                st.session_state.conversation.append({"role": "assistant", "content": advanced_response, "format": "xml"})
            else:
                # Get response from the chatbot logic
                response = get_chatbot_response(user_input)
                
                # Check if the response contains a search command
                if "[SEARCH:" in response:
                    search_executed = process_search_command(response)
                    if search_executed:
                        # Remove the search command from the displayed response
                        response = re.sub(r"\[SEARCH:.*?\]", "", response).strip()
            
        st.rerun()

# Add helpful info at the bottom
if not st.session_state.showing_tutorial:
    st.markdown("---")
    st.caption("💡 Tip: Try `/help` to see all commands or `/tutorial` to start the interactive guide. For advanced features, try `/compare` or `/review`.")