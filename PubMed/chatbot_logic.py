# openai_enhanced_features.py
import streamlit as st
import openai
import re
import os
from dotenv import load_dotenv
from xml_formatter import format_response_with_xml, get_formatted_explanation, get_formatted_methodology_analysis, get_formatted_research_gaps

# Load environment variables
load_dotenv()

# Initialize OpenAI with API key
openai.api_key = os.getenv("OPENAI_API_KEY")

def detect_medical_terms(text, max_terms=8):
    """
    Use OpenAI to detect medical terminology in text
    """
    if not text or text == "No abstract available":
        return []
    
    try:
        # Check if API key is available
        if not openai.api_key:
            st.error("OpenAI API key not found. Please check your .env file.")
            return []
            
        # Use OpenAI to detect medical terms
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",  # Use a smaller model for speed and cost efficiency
            messages=[
                {"role": "system", "content": "You are a medical terminology detector. Extract specialized medical terms from the text provided. Return only the most complex or technical medical terms that a general audience would find difficult to understand. Return the response as a comma-separated list of terms only."},
                {"role": "user", "content": f"Extract medical terms from this text:\n\n{text[:2000]}"}  # Limit to first 2000 chars
            ],
            temperature=0.3,
            max_tokens=100
        )
        
        # Extract the terms from the response
        terms_text = response.choices[0].message.content.strip()
        
        # Parse the comma-separated list
        terms = [term.strip() for term in terms_text.split(',') if term.strip()]
        
        # Limit to max_terms
        return terms[:max_terms]
        
    except Exception as e:
        st.error(f"Error detecting medical terms: {str(e)}")
        return []



def explain_medical_term(term):
    """
    Generate a plain-language explanation for a medical term using OpenAI
    """
    try:
        # Check if API key is available
        if not openai.api_key:
            return "Error: OpenAI API key not found. Please check your .env file."
        
        # Use the formatter function from xml_formatter.py
        return get_formatted_explanation(term)
        
    except Exception as e:
        error_message = f"I couldn't generate an explanation for '{term}': {str(e)}"
        return format_response_with_xml("general", error_message)


def identify_research_gaps(topic=None):
    """
    Analyze current search results to identify potential research gaps using OpenAI
    """
    if not st.session_state.search_results or not st.session_state.search_results["articles"]:
        return format_response_with_xml("general", "Please perform a search first to identify research gaps.")
    
    # Extract relevant information from articles
    articles = st.session_state.search_results["articles"]
    query = st.session_state.current_query or topic or "the current topic"
    
    # Compile abstracts for analysis (limit to 5 for API efficiency)
    abstracts = [article["abstract"] for article in articles[:5] if article["abstract"] != "No abstract available"]
    if not abstracts:
        return format_response_with_xml("general", "Could not find enough abstracts to analyze. Try a different search.")
    
    try:
        # Check if API key is available
        if not openai.api_key:
            return format_response_with_xml("general", "Error: OpenAI API key not found. Please check your .env file.")
        
        # Use the formatter function from xml_formatter.py
        return get_formatted_research_gaps(query, abstracts)
        
    except Exception as e:
        error_message = f"Error analyzing research gaps: {str(e)}"
        return format_response_with_xml("general", error_message)

def analyze_methodologies(abstract=None):
    """
    Extract and summarize research methodologies from abstracts using OpenAI
    """
    # If specific abstract provided, use it; otherwise use search results
    if abstract:
        text_to_analyze = abstract
    elif st.session_state.search_results and st.session_state.search_results["articles"]:
        # Compile abstracts for analysis (limit to 3 for API efficiency)
        abstracts = [article["abstract"] for article in st.session_state.search_results["articles"][:3] 
                    if article["abstract"] != "No abstract available"]
        if not abstracts:
            return format_response_with_xml("general", "Could not find enough abstracts to analyze. Try a different search.")
        text_to_analyze = " ".join(abstracts)
    else:
        return format_response_with_xml("general", "Please perform a search first or provide a specific abstract to analyze methodologies.")
    
    try:
        # Check if API key is available
        if not openai.api_key:
            return format_response_with_xml("general", "Error: OpenAI API key not found. Please check your .env file.")
        
        # Use the formatter function from xml_formatter.py
        return get_formatted_methodology_analysis(text_to_analyze)
        
    except Exception as e:
        error_message = f"Error analyzing methodology: {str(e)}"
        return format_response_with_xml("general", error_message)

def get_chatbot_response(user_input):
    """
    Process user input and return appropriate chatbot response
    """
    # Check for specific feature requests
    term_explanation_match = re.search(r"explain term(?:s|)\s*[\"']?([^\"']+)[\"']?", user_input, re.IGNORECASE)
    research_gap_match = re.search(r"(research gaps|gaps in research|unexplored areas)", user_input, re.IGNORECASE)
    methodology_match = re.search(r"(methodology|study design|research design|methods)", user_input, re.IGNORECASE)
    
    # Define behavior based on the type of request
    if term_explanation_match:
        term = term_explanation_match.group(1).strip()
        explanation = explain_medical_term(term)
        
        # Add to conversation history
        st.session_state.conversation.append({"role": "user", "content": user_input, "format": "text"})
        st.session_state.conversation.append({"role": "assistant", "content": explanation, "format": "xml"})
        
        return explanation
        
    elif research_gap_match:
        gaps_analysis = identify_research_gaps()
        
        # Add to conversation history
        st.session_state.conversation.append({"role": "user", "content": user_input, "format": "text"})
        st.session_state.conversation.append({"role": "assistant", "content": gaps_analysis, "format": "xml"})
        
        return gaps_analysis
        
    elif methodology_match:
        # Check if there's a reference to a specific article or abstract
        abstract_match = re.search(r"abstract (?:number |#)?(\d+)", user_input, re.IGNORECASE)
        abstract = None
        
        if abstract_match and st.session_state.search_results and st.session_state.search_results["articles"]:
            article_num = int(abstract_match.group(1)) - 1  # Convert to 0-based index
            if 0 <= article_num < len(st.session_state.search_results["articles"]):
                abstract = st.session_state.search_results["articles"][article_num]["abstract"]
        
        methodology_analysis = analyze_methodologies(abstract)
        
        # Add to conversation history
        st.session_state.conversation.append({"role": "user", "content": user_input, "format": "text"})
        st.session_state.conversation.append({"role": "assistant", "content": methodology_analysis, "format": "xml"})
        
        return methodology_analysis
        
    else:
        # Default PubMed assistant behavior - using OpenAI
        try:
            # Check if API key is available
            if not openai.api_key:
                error_msg = "Error: OpenAI API key not found. Please check your .env file."
                st.session_state.conversation.append({"role": "user", "content": user_input, "format": "text"})
                st.session_state.conversation.append({"role": "assistant", "content": error_msg, "format": "text"})
                return error_msg
                
            # Record user input in conversation history
            st.session_state.conversation.append({"role": "user", "content": user_input, "format": "text"})
            
            # Define system prompt for the general assistant
            system_prompt = {
                "role": "system", 
                "content": (
                    "You are a specialized assistant for a PubMed search application. Your purpose is to assist users with PubMed-related tasks, such as formulating search queries, interpreting search results, suggesting MeSH terms, or explaining PubMed syntax (e.g., AND, OR, [MeSH], [Author]). "
                    "When a user requests a search, respond with `[SEARCH: query]` to trigger a PubMed search, followed by a brief explanation of the query. "
                    "You can also assist with these specialized functions:\n"
                    "1. Explain medical terminology (respond to 'explain term X')\n"
                    "2. Identify research gaps (respond to 'find research gaps')\n"
                    "3. Analyze and summarize study methodologies (respond to 'explain methodology')\n"
                    "If the user's input is unrelated to PubMed, politely redirect them."
                )
            }
            
            # Send conversation history to OpenAI
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[system_prompt] + [
                    {"role": m["role"], "content": m["content"]} 
                    for m in st.session_state.conversation[-10:] if "format" in m
                ],
                temperature=0.5,
                max_tokens=500
            )
            
            assistant_message = response.choices[0].message.content.strip()
            
            # Post-process to ensure `[SEARCH: query]` is valid if present
            search_match = re.search(r"\[SEARCH:\s*(.*?)\]", assistant_message)
            if search_match and not search_match.group(1).strip():
                assistant_message = assistant_message.replace(search_match.group(0), "") + "\n\nPlease provide a specific query for me to search PubMed."

            # Store assistant response in conversation history
            st.session_state.conversation.append({"role": "assistant", "content": assistant_message, "format": "text"})
            
            return assistant_message
            
        except Exception as e:
            error_message = f"Error with OpenAI API: {str(e)}"
            st.session_state.conversation.append({"role": "assistant", "content": error_message, "format": "text"})
            return error_message

def process_search_command(response):
    """
    Extract and process search command from response
    """
    match = re.search(r"\[SEARCH:\s*(.*?)\]", response)
    if match and match.group(1).strip():
        query = match.group(1).strip()
        st.session_state.current_query = query
        from pubmed_api import search_pubmed
        with st.spinner("Performing PubMed search..."):
            try:
                # Execute the search
                search_results = search_pubmed(query)
                
                # Store search results in session state
                st.session_state.search_results = search_results
                
                # Add a message with the search results
                result_count = search_results.get("count", 0)
                if result_count > 0:
                    message = f"Found {result_count} results for '{query}'. You can view them on the Search page or ask me to analyze them."
                    st.session_state.conversation.append({"role": "assistant", "content": message, "format": "text"})
                else:
                    message = f"No results found for '{query}'. Try a different search term or check your syntax."
                    st.session_state.conversation.append({"role": "assistant", "content": message, "format": "text"})
                
                return True
            except Exception as e:
                error_message = f"Error searching PubMed: {str(e)}"
                st.session_state.conversation.append({"role": "assistant", "content": error_message, "format": "text"})
                return False
    return False