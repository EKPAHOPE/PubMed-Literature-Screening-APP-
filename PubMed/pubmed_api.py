# pubmed_api.py
import requests
import xml.etree.ElementTree as ET
import streamlit as st
from config import BASE_URL, EMAIL, TOOL

def search_pubmed(query, max_results=20, start=0, sort="relevance", webenv=None, query_key=None):
    if webenv is None or query_key is None:
        # Initial search to get WebEnv and query_key
        search_url = f"{BASE_URL}esearch.fcgi"
        search_params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retstart": 0,  # Start at 0 for initial search
            "sort": sort,
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
                return {"count": 0, "articles": [], "webenv": None, "query_key": None}
            webenv = webenv_elem.text
            query_key = query_key_elem.text
        except requests.exceptions.RequestException as e:
            st.error(f"API request error: {e}")
            return {"count": 0, "articles": [], "webenv": None, "query_key": None}
        except ET.ParseError as e:
            st.error(f"XML parsing error: {e}")
            return {"count": 0, "articles": [], "webenv": None, "query_key": None}
    else:
        # Use existing WebEnv and query_key for pagination
        count = None  # Count is only set on initial search; reuse previous count from session state

    # Fetch articles using efetch
    fetch_url = f"{BASE_URL}efetch.fcgi"
    fetch_params = {
        "db": "pubmed",
        "retmode": "xml",
        "rettype": "abstract",
        "WebEnv": webenv,
        "query_key": query_key,
        "retmax": max_results,
        "retstart": start,
        "tool": TOOL,
        "email": EMAIL
    }
    try:
        fetch_response = requests.get(fetch_url, params=fetch_params)
        fetch_response.raise_for_status()
        articles = parse_pubmed_xml(fetch_response.content)
        return {"count": count if count is not None else st.session_state.search_results["count"], "articles": articles, "webenv": webenv, "query_key": query_key}
    except requests.exceptions.RequestException as e:
        st.error(f"API request error: {e}")
        return {"count": 0, "articles": [], "webenv": webenv, "query_key": query_key}
    except ET.ParseError as e:
        st.error(f"XML parsing error: {e}")
        return {"count": 0, "articles": [], "webenv": webenv, "query_key": query_key}

def parse_pubmed_xml(xml_content):
    root = ET.fromstring(xml_content)
    articles = []
    for article_elem in root.findall(".//PubmedArticle"):
        try:
            pmid = article_elem.find(".//PMID").text
            title = article_elem.find(".//ArticleTitle").text or "No title available"
            abstract = " ".join([part.text for part in article_elem.findall(".//AbstractText") if part.text]) or "No abstract available"
            authors = [f"{a.find('ForeName').text} {a.find('LastName').text}" 
                      for a in article_elem.findall(".//Author") if a.find("LastName") is not None] or ["Unknown"]
            journal = article_elem.find(".//Journal/Title").text or "Unknown Journal"
            year = article_elem.find(".//PubDate/Year")
            if year is None:
                medline_date = article_elem.find(".//PubDate/MedlineDate")
                year = medline_date.text[:4] if medline_date is not None else "Unknown Year"
            else:
                year = year.text
            month = article_elem.find(".//PubDate/Month").text or ""
            pub_date = f"{month} {year}".strip()
            doi = next((id_elem.text for id_elem in article_elem.findall(".//ArticleId") 
                        if id_elem.get("IdType") == "doi"), None)
            articles.append({
                "pmid": pmid, "title": title, "abstract": abstract, "authors": ", ".join(authors),
                "journal": journal, "pub_date": pub_date, "year": year, "doi": doi,
                "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            })
        except Exception as e:
            st.warning(f"Error parsing article: {e}")
    return articles