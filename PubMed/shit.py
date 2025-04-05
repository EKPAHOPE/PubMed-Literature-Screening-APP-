# test_openai_features.py
import os
from dotenv import load_dotenv
import openai

# Load environment variables
load_dotenv()

# Initialize OpenAI API
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("ERROR: OPENAI_API_KEY not found in .env file")
    exit(1)

openai.api_key = api_key

def test_api_connection():
    """Test if we can connect to OpenAI API"""
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say hello!"}
            ],
            max_tokens=10
        )
        
        print("✅ OpenAI API connection successful!")
        print("Response:", response.choices[0].message.content)
        return True
    except Exception as e:
        print("❌ OpenAI API connection failed:")
        print(str(e))
        return False

def test_term_explanation():
    """Test medical term explanation"""
    test_term = "hypertension"
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert at explaining complex medical terminology in simple language."},
                {"role": "user", "content": f"Explain the medical term '{test_term}' in plain language:"}
            ],
            max_tokens=100
        )
        
        print(f"\n✅ Term explanation for '{test_term}' successful!")
        print("Explanation:", response.choices[0].message.content)
        return True
    except Exception as e:
        print(f"\n❌ Term explanation for '{test_term}' failed:")
        print(str(e))
        return False

def main():
    """Run all tests"""
    print("Testing OpenAI API Integration")
    print("=============================")
    
    # Test API connection
    conn_success = test_api_connection()
    
    if conn_success:
        # Test term explanation
        term_success = test_term_explanation()
        
    print("\nTest Summary:")
    print(f"API Connection: {'✅ Passed' if conn_success else '❌ Failed'}")
    if conn_success:
        print(f"Term Explanation: {'✅ Passed' if term_success else '❌ Failed'}")
    
    print("\nIf all tests passed, your OpenAI integration is working correctly!")
    print("If any tests failed, check your API key and internet connection.")

if __name__ == "__main__":
    main()