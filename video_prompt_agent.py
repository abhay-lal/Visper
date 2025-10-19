from google import genai
import os
import json
from urllib.parse import urlparse

from vectara_qna import VectaraQnA


def extract_repo_title(git_url):
    """Extract repository title from GitHub URL (anything after github.com/)"""
    try:
        parsed = urlparse(git_url)
        # Remove leading/trailing slashes and get path
        path = parsed.path.strip('/')
        if path:
            return path
        return "Unknown Repository"
    except Exception:
        return "Unknown Repository"


def analyze_repository(git_url):
    """
    Analyze a repository and return structured information.
    
    Args:
        git_url (str): The GitHub repository URL
        
    Returns:
        dict: Dictionary containing title, description, user_journey, and repository URL
    """
    qna = VectaraQnA()
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
    # Store all the information
    repo_info = {
        "title": extract_repo_title(git_url),
        "description": "",
        "user_journey": "",
        "repository": git_url
    }
    
    # 1. Get repository description
    question = "What does this repository do? What is its main purpose?"
    response = qna.ask(question)
    
    if response is not None:
        gemini_response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"Summarize the following information: {response['answer']} and sources: {response['sources']}. Provide a concise 2-3 sentence description of what this repository does."
        )
        repo_info["description"] = gemini_response.text.strip()
    
    # 2. Get user journey
    question = "Can you explain the user flow or user journey of the repository? How do users interact with this application?"
    response = qna.ask(question)
    
    if response is not None:
        gemini_response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"Based on this information: {response['answer']} and sources: {response['sources']}, describe the user journey in 2-3 sentences. Explain how users interact with the application."
        )
        repo_info["user_journey"] = gemini_response.text.strip()
    
    return repo_info


def main():
    """Main function for command-line usage"""
    import sys
    
    # Get git URL from command line argument or use default
    if len(sys.argv) > 1:
        git_url = sys.argv[1]
    else:
        git_url = input("Enter GitHub repository URL: ").strip()
    
    if not git_url:
        print("Error: No repository URL provided")
        sys.exit(1)
    
    # Analyze repository
    result = analyze_repository(git_url)
    
    # Output the JSON
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
