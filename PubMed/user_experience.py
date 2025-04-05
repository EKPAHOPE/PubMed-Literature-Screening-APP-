# user_experience.py
import streamlit as st
import json
import os
from datetime import datetime

# File to store user preferences
USER_PREFS_DIR = "user_preferences"
TOUR_COMPLETED_KEY = "tour_completed"

def init_user_experience():
    """Initialize user experience features"""
    # Add new session state variables for user experience features
    if 'help_expanded' not in st.session_state:
        st.session_state.help_expanded = False
    if 'current_tutorial_step' not in st.session_state:
        st.session_state.current_tutorial_step = 0
    if 'user_preferences' not in st.session_state:
        st.session_state.user_preferences = load_user_preferences()
    if 'showing_tutorial' not in st.session_state:
        st.session_state.showing_tutorial = False
    if 'capabilities_list' not in st.session_state:
        st.session_state.capabilities_list = get_chatbot_capabilities()
    
    # Create preferences directory if it doesn't exist
    if not os.path.exists(USER_PREFS_DIR):
        os.makedirs(USER_PREFS_DIR)

def get_chatbot_capabilities():
    """Return a structured list of chatbot capabilities"""
    return [
        {
            "category": "Literature Search",
            "features": [
                {"name": "Search PubMed", "command": "/search [terms]", "description": "Search PubMed for scientific articles with your query"},
                {"name": "Refine Search", "command": "/refine [filters]", "description": "Add filters to your current search results (date, type, author, etc.)"},
                {"name": "Get Citation", "command": "/cite [article number]", "description": "Get formatted citation for a specific article"}
            ]
        },
        {
            "category": "Medical Terminology",
            "features": [
                {"name": "Explain Terms", "command": "/explain [term]", "description": "Get plain-language explanation of medical terminology"},
                {"name": "Find Terms in Abstract", "command": "/terms [article number]", "description": "Identify complex terms in a specific article abstract"}
            ]
        },
        {
            "category": "Research Analysis",
            "features": [
                {"name": "Analyze Methodology", "command": "/methodology [article number]", "description": "Analyze research methodology in a paper"},
                {"name": "Find Research Gaps", "command": "/gaps", "description": "Identify potential research gaps in current search results"},
                {"name": "Compare Studies", "command": "/compare [article #1] [article #2]", "description": "Compare methodologies and findings between studies"},
                {"name": "Suggest Questions", "command": "/questions", "description": "Generate research questions based on current search"}
            ]
        },
        {
            "category": "User Preferences",
            "features": [
                {"name": "Set Complexity Level", "command": "/complexity [basic|intermediate|advanced]", "description": "Set your preferred explanation complexity"},
                {"name": "Set Detail Level", "command": "/detail [brief|standard|detailed]", "description": "Set your preferred level of detail in responses"},
                {"name": "View Preferences", "command": "/preferences", "description": "View your current preference settings"}
            ]
        },
        {
            "category": "Help & Learning",
            "features": [
                {"name": "Get Help", "command": "/help [optional: topic]", "description": "Display available commands or get help on a specific topic"},
                {"name": "Start Tutorial", "command": "/tutorial", "description": "Start an interactive tutorial of the features"},
                {"name": "Show Examples", "command": "/examples", "description": "Show example usage scenarios"}
            ]
        }
    ]

def process_help_command(user_input):
    """Process help commands and return appropriate response"""
    # Check if this is a help command
    if user_input.lower().startswith('/help'):
        parts = user_input.split(maxsplit=1)
        topic = parts[1].lower() if len(parts) > 1 else None
        
        # If a specific topic was requested
        if topic:
            for category in st.session_state.capabilities_list:
                for feature in category['features']:
                    if topic in feature['name'].lower() or topic in feature['command'].lower():
                        return f"""
## Help: {feature['name']}

**Command:** `{feature['command']}`

{feature['description']}

**Example usage:**
{get_example_for_feature(feature['command'].split()[0])}
"""
            
            # If we got here, no matching topic was found
            return f"Sorry, I couldn't find help on '{topic}'. Try '/help' to see all available commands."
        else:
            # Return the general help menu
            help_text = "# Available Commands\n\n"
            for category in st.session_state.capabilities_list:
                help_text += f"## {category['category']}\n\n"
                for feature in category['features']:
                    help_text += f"- **{feature['command']}**: {feature['description']}\n"
                help_text += "\n"
            
            help_text += "\nTip: You can get detailed help on any command with `/help [command]`"
            return help_text
    
    # Not a help command
    return None

def get_example_for_feature(command):
    """Return usage examples for specific commands"""
    examples = {
        "/search": "`/search diabetes type 2 treatment`",
        "/explain": "`/explain hyperglycemia`",
        "/methodology": "`/methodology 3`  (analyzes the third article in your results)",
        "/gaps": "`/gaps`  (analyzes your current search results)",
        "/complexity": "`/complexity intermediate`",
        "/tutorial": "`/tutorial`",
        "/compare": "`/compare 1 4`  (compares the first and fourth articles)"
    }
    
    return examples.get(command, "No example available for this command.")

def user_preference_ui():
    """Display and manage user preferences in the sidebar"""
    with st.sidebar.expander("Preferences", expanded=False):
        st.subheader("Your Preferences")
        
        # Complexity preference
        complexity_options = ["Basic", "Intermediate", "Advanced"]
        current_complexity = st.session_state.user_preferences.get("complexity", "Intermediate")
        new_complexity = st.select_slider(
            "Explanation Complexity",
            options=complexity_options,
            value=current_complexity
        )
        
        # Detail level preference
        detail_options = ["Brief", "Standard", "Detailed"]
        current_detail = st.session_state.user_preferences.get("detail_level", "Standard")
        new_detail = st.select_slider(
            "Response Detail",
            options=detail_options,
            value=current_detail
        )
        
        # Citation style preference
        citation_options = ["APA", "MLA", "Chicago", "Vancouver"]
        current_citation = st.session_state.user_preferences.get("citation_style", "Vancouver")
        new_citation = st.selectbox(
            "Citation Style",
            options=citation_options,
            index=citation_options.index(current_citation)
        )
        
        # Check if preferences have changed
        if (new_complexity != current_complexity or 
            new_detail != current_detail or 
            new_citation != current_citation):
            
            # Update preferences
            st.session_state.user_preferences["complexity"] = new_complexity
            st.session_state.user_preferences["detail_level"] = new_detail
            st.session_state.user_preferences["citation_style"] = new_citation
            
            # Save to file
            save_user_preferences()
            
            # Show confirmation
            st.success("Preferences updated!")

def load_user_preferences():
    """Load user preferences from file"""
    if not st.session_state.authenticated:
        return get_default_preferences()
        
    username = st.session_state.current_user
    prefs_file = os.path.join(USER_PREFS_DIR, f"{username}.json")
    
    if os.path.exists(prefs_file):
        try:
            with open(prefs_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Error loading preferences: {str(e)}")
            return get_default_preferences()
    else:
        return get_default_preferences()

def save_user_preferences():
    """Save user preferences to file"""
    if not st.session_state.authenticated:
        return
        
    username = st.session_state.current_user
    prefs_file = os.path.join(USER_PREFS_DIR, f"{username}.json")
    
    try:
        # Add last updated timestamp
        st.session_state.user_preferences["last_updated"] = datetime.now().isoformat()
        
        with open(prefs_file, 'w') as f:
            json.dump(st.session_state.user_preferences, f, indent=2)
    except Exception as e:
        st.error(f"Error saving preferences: {str(e)}")

def get_default_preferences():
    """Return default user preferences"""
    return {
        "complexity": "Intermediate",
        "detail_level": "Standard",
        "citation_style": "Vancouver",
        "created_at": datetime.now().isoformat()
    }

def process_preference_command(user_input):
    """Process commands related to preferences"""
    if user_input.lower().startswith('/complexity'):
        parts = user_input.lower().split(maxsplit=1)
        if len(parts) > 1:
            level = parts[1].capitalize()
            valid_levels = ["Basic", "Intermediate", "Advanced"]
            if level in valid_levels:
                st.session_state.user_preferences["complexity"] = level
                save_user_preferences()
                return f"Your explanation complexity preference has been set to {level}."
            else:
                return f"Invalid complexity level. Please choose from: {', '.join(valid_levels)}"
        else:
            return f"Current complexity level: {st.session_state.user_preferences.get('complexity', 'Intermediate')}"
            
    elif user_input.lower().startswith('/detail'):
        parts = user_input.lower().split(maxsplit=1)
        if len(parts) > 1:
            level = parts[1].capitalize()
            valid_levels = ["Brief", "Standard", "Detailed"]
            if level in valid_levels:
                st.session_state.user_preferences["detail_level"] = level
                save_user_preferences()
                return f"Your response detail preference has been set to {level}."
            else:
                return f"Invalid detail level. Please choose from: {', '.join(valid_levels)}"
        else:
            return f"Current detail level: {st.session_state.user_preferences.get('detail_level', 'Standard')}"
            
    elif user_input.lower() == '/preferences':
        response = "## Your Current Preferences\n\n"
        for key, value in st.session_state.user_preferences.items():
            if key not in ['created_at', 'last_updated']:
                response += f"- **{key.replace('_', ' ').title()}**: {value}\n"
        return response
        
    return None

def get_tutorial_steps():
    """Return the tutorial steps"""
    return [
        {
            "title": "Welcome to the PubMed Assistant",
            "content": """
Welcome to the interactive tutorial for the PubMed Assistant! This tutorial will guide you through the main features of the assistant.

The assistant has several powerful capabilities to help you with medical research:

1. **Literature Search**: Find and navigate PubMed articles
2. **Medical Terminology**: Get explanations of complex terms
3. **Research Analysis**: Analyze methodologies and identify research gaps
4. **Personalization**: Set your preferences for how information is presented

Click 'Next' to continue or 'Skip Tutorial' to exit.
            """
        },
        {
            "title": "Literature Search Commands",
            "content": """
You can search PubMed directly from the chat interface:

- Type `/search diabetes treatment` to search for articles about diabetes treatment
- Type `/refine 2020:2023` to filter your results to these years
- Type `/cite 3` to get a citation for the third article in your results

Try `/search` followed by any medical topic you're interested in!
            """
        },
        {
            "title": "Understanding Medical Terminology",
            "content": """
The assistant can explain complex medical terminology:

- Type `/explain hyperglycemia` to get a plain-language explanation
- When viewing articles, click "Explain These Terms" to explain all technical terms at once
- You can ask "what does [term] mean?" in natural language too

The system will adapt explanations to your preferred complexity level.
            """
        },
        {
            "title": "Research Analysis Features",
            "content": """
Analyze research papers and identify gaps:

- Type `/methodology 2` to analyze the methods used in the second article
- Type `/gaps` to identify potential research gaps in your current search results
- Type `/compare 1 3` to compare the first and third articles
- Type `/questions` to get suggested research questions based on your search

These features help you quickly understand research methods and findings.
            """
        },
        {
            "title": "Personalizing Your Experience",
            "content": """
You can customize how the assistant interacts with you:

- Type `/complexity [basic|intermediate|advanced]` to set explanation detail
- Type `/detail [brief|standard|detailed]` to set response length
- Find these settings and more in the Preferences panel in the sidebar

Your preferences are saved between sessions for a consistent experience.
            """
        },
        {
            "title": "Getting Help",
            "content": """
Whenever you need help, you have several options:

- Type `/help` to see all available commands
- Type `/help [topic]` to get help on a specific feature
- Type `/examples` to see example usage scenarios
- Type `/tutorial` to restart this tutorial at any time

You're now ready to use the PubMed Assistant! Click 'Finish' to start exploring.
            """
        }
    ]

def process_tutorial_command(user_input):
    """Process tutorial command and start the tutorial"""
    if user_input.lower() == '/tutorial':
        st.session_state.showing_tutorial = True
        st.session_state.current_tutorial_step = 0
        return "Starting interactive tutorial. I'll guide you through the main features of the PubMed Assistant."
    return None

def display_tutorial():
    """Display the interactive tutorial"""
    if not st.session_state.showing_tutorial:
        return
    
    # Get tutorial steps
    tutorial_steps = get_tutorial_steps()
    current_step = st.session_state.current_tutorial_step
    
    # Display current tutorial step
    st.info(f"### Tutorial: {tutorial_steps[current_step]['title']}")
    st.markdown(tutorial_steps[current_step]['content'])
    
    # Navigation buttons
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if current_step > 0:
            if st.button("Previous"):
                st.session_state.current_tutorial_step -= 1
                st.rerun()
                
    with col2:
        if st.button("Skip Tutorial"):
            st.session_state.showing_tutorial = False
            # Mark tutorial as completed
            st.session_state.user_preferences[TOUR_COMPLETED_KEY] = True
            save_user_preferences()
            st.rerun()
            
    with col3:
        if current_step < len(tutorial_steps) - 1:
            next_button = st.button("Next")
            if next_button:
                st.session_state.current_tutorial_step += 1
                st.rerun()
        else:
            finish_button = st.button("Finish")
            if finish_button:
                st.session_state.showing_tutorial = False
                # Mark tutorial as completed
                st.session_state.user_preferences[TOUR_COMPLETED_KEY] = True
                save_user_preferences()
                st.success("Tutorial completed! You can restart it at any time with the `/tutorial` command.")
                st.rerun()

def should_show_tutorial_prompt():
    """Check if we should prompt the user to take the tutorial"""
    if not st.session_state.authenticated:
        return False
        
    # Check if the user has completed the tutorial before
    completed = st.session_state.user_preferences.get(TOUR_COMPLETED_KEY, False)
    return not completed

def display_tutorial_prompt():
    """Display a prompt to take the tutorial"""
    if should_show_tutorial_prompt():
        st.info("It looks like you're new to the PubMed Assistant. Would you like to take a quick tutorial?")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Yes, show me around"):
                st.session_state.showing_tutorial = True
                st.session_state.current_tutorial_step = 0
                st.rerun()
        with col2:
            if st.button("No, skip tutorial"):
                st.session_state.user_preferences[TOUR_COMPLETED_KEY] = True
                save_user_preferences()
                st.rerun()

def process_command(user_input):
    """Process all user experience commands"""
    # First check help command
    response = process_help_command(user_input)
    if response:
        return response
        
    # Then check tutorial command
    response = process_tutorial_command(user_input)
    if response:
        return response
        
    # Then check preference commands
    response = process_preference_command(user_input)
    if response:
        return response
        
    # No user experience command detected
    return None