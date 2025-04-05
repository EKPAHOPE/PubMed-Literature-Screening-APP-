# xml_formatter.py
import streamlit as st
import re
import openai

def format_response_with_xml(response_type, content):
    """
    Format OpenAI responses with XML tags for better display
    
    Parameters:
    response_type: The type of response (term_explanation, methodology, research_gaps, etc.)
    content: The content from OpenAI
    
    Returns:
    A formatted string with XML tags
    """
    
    if response_type == "term_explanation":
        # Extract term and definition parts
        # Assuming the format is somewhat consistent from the API
        parts = content.split(":", 1) if ":" in content else [content, ""]
        term = parts[0].strip() if len(parts) > 0 else ""
        definition = parts[1].strip() if len(parts) > 1 else content
        
        # Clean any markdown from the term
        term = re.sub(r'(\*\*|__)', '', term)
        
        return f"""
<response type="term_explanation">
    <term>{term}</term>
    <definition>{definition}</definition>
</response>
"""
    
    elif response_type == "multiple_terms":
        
        terms_xml = ""
        
        # Look for terms in bold or with other markers
        term_matches = re.findall(r'(?:\*\*|__)?([\w\s-]+)(?:\*\*|__)?:\s*(.*?)(?=\n\n|\n(?:\*\*|__)?[\w\s-]+(?:\*\*|__)?:|\Z)', content, re.DOTALL)
        
        if not term_matches:
            # Try alternate format with bullets or numbers
            term_matches = re.findall(r'(?:^|\n)(?:[-•*]|\d+\.)\s*(?:\*\*|__)?([\w\s-]+)(?:\*\*|__)?:?\s*(.*?)(?=\n(?:[-•*]|\d+\.)|$)', content, re.DOTALL)
        
        if term_matches:
            for term, definition in term_matches:
                # Clean any markdown from the term
                clean_term = re.sub(r'(\*\*|__)', '', term.strip())
                terms_xml += f"<term_item>\n    <term>{clean_term}</term>\n    <definition>{definition.strip()}</definition>\n</term_item>\n"
        else:
            # Fallback to returning the whole content
            terms_xml = f"<content>{content}</content>"
        
        return f"""
<response type="multiple_terms">
    {terms_xml}
</response>
"""
    
    elif response_type == "methodology":
        # Try to identify sections in the methodology analysis
        study_design = ""
        methods = ""
        strengths = ""
        limitations = ""
        
        # Improved pattern matching to extract sections - more flexible matching
        design_match = re.search(r"(?i)(?:(?:type of|study|research) design|design type):?\s*(.*?)(?:\n\n|\n(?:[A-Z]|[0-9]\.)|$)", content, re.DOTALL)
        methods_match = re.search(r"(?i)(?:key methodolog|methods|methodology|approach):?\s*(.*?)(?:\n\n|\n(?:[A-Z]|[0-9]\.)|$)", content, re.DOTALL)
        
        # More flexible matching for strengths and limitations
        strengths_match = re.search(r"(?i)(?:strengths|advantages|benefits|positive aspects):?\s*(.*?)(?:\n\n|\n(?:[A-Z]|[0-9]\.)|$)", content, re.DOTALL)
        limitations_match = re.search(r"(?i)(?:limitations?|weaknesses|disadvantages|challenges|drawbacks|constraints):?\s*(.*?)(?:\n\n|\n(?:[A-Z]|[0-9]\.)|$)", content, re.DOTALL)
        
        # If limitations section wasn't found, look for "limitations" mentioned within other sections
        if not limitations_match:
            # Look for sections that might contain limitations info
            limitations_sections = re.findall(r"(?i)(?:.*limitations.*|.*drawbacks.*|.*challenges.*|.*weaknesses.*):?\s*(.*?)(?:\n\n|\n(?:[A-Z]|[0-9]\.)|$)", content, re.DOTALL)
            if limitations_sections:
                limitations = ". ".join([section.strip() for section in limitations_sections])
            else:
                # Default placeholder if nothing found
                limitations = "No specific limitations were identified in the analysis."
        else:
            limitations = limitations_match.group(1).strip()
        
        if design_match:
            study_design = design_match.group(1).strip()
        if methods_match:
            methods = methods_match.group(1).strip()
        if strengths_match:
            strengths = strengths_match.group(1).strip()
        
        # If sections weren't properly identified, use the full content
        if not any([study_design, methods, strengths, limitations]):
            return f"""
<response type="methodology">
    <content>{content}</content>
</response>
"""
        else:
            # Ensure all sections have content
            study_design = study_design or "Study design was not clearly identified."
            methods = methods or "Methodological details were not explicitly described."
            strengths = strengths or "Specific strengths were not highlighted in the analysis."
            
            return f"""
<response type="methodology">
    <study_design>{study_design}</study_design>
    <methods>{methods}</methods>
    <strengths>{strengths}</strengths>
    <limitations>{limitations}</limitations>
</response>
"""
    
    elif response_type == "research_gaps":
        # Try to identify numbered research gaps
        gaps = []
        
        # Look for numbered points or bullet points
        gap_matches = re.findall(r"(?:^|\n)(?:\d+\.|\*)\s*(.*?)(?=(?:\n(?:\d+\.|\*)|$))", content, re.DOTALL)
        
        if gap_matches:
            for gap in gap_matches:
                gaps.append(gap.strip())
        else:
            
            paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
            gaps = paragraphs
        
        gaps_xml = "\n    ".join(f"<gap>{gap}</gap>" for gap in gaps)
        
        return f"""
<response type="research_gaps">
    {gaps_xml}
</response>
"""
    
    else:
       
        return f"""
<response type="general">
    <content>{content}</content>
</response>
"""

def render_xml_response(xml_string):
    """
    Render XML response in Streamlit with custom styling
    """
    try:
        # Simplistic XML parsing to extract content
        response_type_match = re.search(r'<response type="([^"]+)">', xml_string)
        response_type = response_type_match.group(1) if response_type_match else "general"
        
        if response_type == "term_explanation":
            term_match = re.search(r'<term>(.*?)</term>', xml_string, re.DOTALL)
            definition_match = re.search(r'<definition>(.*?)</definition>', xml_string, re.DOTALL)
            
            term = term_match.group(1) if term_match else ""
            definition = definition_match.group(1) if definition_match else ""
            
            # Clean any markdown formatting characters
            term = re.sub(r'(\*\*|__)', '', term)
            
            st.markdown(f"### Medical Term: {term}")
            st.markdown(f"{definition}")
            
        elif response_type == "multiple_terms":
            # Extract and display multiple terms
            term_items = re.findall(r'<term_item>\s*<term>(.*?)</term>\s*<definition>(.*?)</definition>\s*</term_item>', xml_string, re.DOTALL)
            
            if term_items:
                st.markdown("### Medical Terms")
                for term, definition in term_items:
                    # Clean any markdown formatting characters
                    term = re.sub(r'(\*\*|__)', '', term)
                    st.markdown(f"**{term.strip()}**: {definition.strip()}")
            else:
                # Fallback to general content display
                content_match = re.search(r'<content>(.*?)</content>', xml_string, re.DOTALL)
                if content_match:
                    st.markdown(content_match.group(1))
                else:
                    st.markdown(xml_string)
            
        elif response_type == "methodology":
            study_design_match = re.search(r'<study_design>(.*?)</study_design>', xml_string, re.DOTALL)
            methods_match = re.search(r'<methods>(.*?)</methods>', xml_string, re.DOTALL)
            strengths_match = re.search(r'<strengths>(.*?)</strengths>', xml_string, re.DOTALL)
            limitations_match = re.search(r'<limitations>(.*?)</limitations>', xml_string, re.DOTALL)
            content_match = re.search(r'<content>(.*?)</content>', xml_string, re.DOTALL)
            
            if content_match and not study_design_match:
                # If we just have general content
                st.markdown(content_match.group(1))
            else:
                study_design = study_design_match.group(1) if study_design_match else ""
                methods = methods_match.group(1) if methods_match else ""
                strengths = strengths_match.group(1) if strengths_match else ""
                limitations = limitations_match.group(1) if limitations_match else ""
                
                st.markdown("### Study Design")
                st.markdown(study_design)
                
                if methods:
                    st.markdown("### Key Methodological Elements")
                    st.markdown(methods)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("### Strengths")
                    st.markdown(strengths)
                with col2:
                    st.markdown("### Limitations")
                    st.markdown(limitations)
            
        elif response_type == "research_gaps":
            gap_matches = re.findall(r'<gap>(.*?)</gap>', xml_string, re.DOTALL)
            
            st.markdown("### Potential Research Gaps")
            for i, gap in enumerate(gap_matches, 1):
                st.markdown(f"**{i}.** {gap}")
                
        else:
            # Extract general content
            content_match = re.search(r'<content>(.*?)</content>', xml_string, re.DOTALL)
            content = content_match.group(1) if content_match else xml_string
            st.markdown(content)
                
    except Exception as e:
        # If XML parsing fails, just render the original content
        st.markdown(xml_string)
        st.error(f"Error rendering formatted response: {str(e)}")


def get_formatted_explanation(terms):
    """Get term explanation with XML formatting - supports multiple terms"""
    
    term_list = []
    if isinstance(terms, str):
        if ',' in terms:
            term_list = [t.strip() for t in terms.split(',')]
        else:
            
            list_items = re.findall(r'(?:^|\n)(?:[-•*]|\d+\.)\s*(.*?)(?=(?:\n(?:[-•*]|\d+\.)|$))', terms, re.DOTALL)
            if list_items:
                term_list = [item.strip() for item in list_items]
            else:
                term_list = [terms.strip()]
    
    
    if len(term_list) > 1:
        # Create a multi-term request
        terms_joined = "\n".join([f"- {term}" for term in term_list])
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a medical terminology expert. Explain each of the listed medical terms in simple language that anyone can understand. Format your response with each term on a new line, followed by a colon and then the explanation. Do not use asterisks, markdown formatting, or other special characters in your response."},
                {"role": "user", "content": f"Explain these medical terms in plain language:\n{terms_joined}"}
            ],
            temperature=0.5,
            max_tokens=800  
        )
        
        explanation = response.choices[0].message.content.strip()
        
       
        explanation = re.sub(r'(\*\*|__)', '', explanation)
        
        return format_response_with_xml("multiple_terms", explanation)
    else:
        # Single term explanation (original code)
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert at explaining complex medical terminology in simple language. Provide a clear, concise explanation of the term. Do not use asterisks, markdown formatting, or other special characters in your response."},
                {"role": "user", "content": f"Explain the medical term '{term_list[0]}' in plain language:"}
            ],
            temperature=0.5,
            max_tokens=150
        )
        
        explanation = response.choices[0].message.content.strip()
        
        # Clean any markdown formatting that might have been added
        explanation = re.sub(r'(\*\*|__)', '', explanation)
        
        return format_response_with_xml("term_explanation", explanation)


def get_formatted_methodology_analysis(abstract):
    """Get methodology analysis with XML formatting"""
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a research methodology expert. Analyze the provided text to identify and explain the research methodology. Structure your response with clear sections, each with a heading: 1) Study Design, 2) Key Methodological Elements, 3) Strengths, and 4) Limitations. Always include all four sections, especially the limitations section. If limitations aren't explicitly stated, analyze what potential limitations might exist based on the study design. Do not use asterisks or other markdown formatting in your response."},
            {"role": "user", "content": f"Analyze and explain the research methodology in this text:\n\n{abstract[:3500]}"}
        ],
        temperature=0.4,
        max_tokens=800
    )
    
    analysis = response.choices[0].message.content.strip()
    
    # Clean any markdown formatting
    analysis = re.sub(r'(\*\*|__)', '', analysis)
    
    return format_response_with_xml("methodology", analysis)


def get_formatted_research_gaps(query, abstracts):
    """Get research gaps analysis with XML formatting"""
    context = f"""
    Topic: {query}
    Number of results found: {len(abstracts)}
    
    Sample abstracts:
    {' '.join(abstracts[:3])}
    """
    
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a research gap analysis expert. Identify 3-5 potential research gaps related to the topic. Format your response as clearly numbered points. Do not use asterisks or other markdown formatting in your response."},
            {"role": "user", "content": f"Analyze these PubMed search results and identify research gaps:\n\n{context[:3500]}"}
        ],
        temperature=0.4,
        max_tokens=800
    )
    
    analysis = response.choices[0].message.content.strip()
    
    
    analysis = re.sub(r'(\*\*|__)', '', analysis)
    
    return format_response_with_xml("research_gaps", analysis)