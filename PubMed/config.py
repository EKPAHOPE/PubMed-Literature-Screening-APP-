# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# NCBI E-utilities
BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
EMAIL = os.getenv("GMAIL_ADDRESS", "ekpahopejames@gmail.com")
APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "bwrd zwvi jxlv snzg")
TOOL = "streamlit-pubmed-app"

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")