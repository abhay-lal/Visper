"""Gemini AI enhancement layer for Vectara search results."""

import os
import logging
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


class SearchSource:
    """Model for a search source/result."""
    def __init__(self, file_path: str, file_name: str, file_type: str,
                 repo: str, owner: str, source_url: str,
                 relevance_score: float, snippet: str):
        self.file_path = file_path
        self.file_name = file_name
        self.file_type = file_type
        self.repo = repo
        self.owner = owner
        self.source_url = source_url
        self.relevance_score = relevance_score
        self.snippet = snippet


def init_gemini_client() -> genai.Client:
    """
    Initialize Gemini client with Vertex AI credentials.

    Returns:
        Configured Gemini client

    Raises:
        ValueError: If credentials are not properly configured
    """
    credentials_path = os.getenv("VERTEX_AI_CREDENTIALS_PATH")
    if credentials_path and not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath(credentials_path)

    project_id = os.getenv("VERTEX_AI_PROJECT_ID")
    location = os.getenv("VERTEX_AI_LOCATION", "us-central1")

    if not project_id:
        raise ValueError("Missing VERTEX_AI_PROJECT_ID in environment/.env")

    logger.info(f"✅ Initializing Gemini client with project: {project_id}, location: {location}")
    return genai.Client(vertexai=True, project=project_id, location=location)


def format_sources_for_gemini(sources: List[Any]) -> str:
    """
    Format Vectara sources into readable text for Gemini.

    Args:
        sources: List of SearchSource objects from Vectara

    Returns:
        Formatted string with source information
    """
    if not sources:
        return "No sources available."

    formatted = []
    # Limit to top 5 sources to avoid token limits
    for idx, source in enumerate(sources[:5], 1):
        # Handle both dict and object formats
        if isinstance(source, dict):
            file_path = source.get('file_path', 'Unknown')
            relevance = source.get('relevance_score', 0.0)
            snippet = source.get('snippet', 'No snippet available')
            repo = source.get('repo', 'Unknown')
            file_type = source.get('file_type', 'Unknown')
        else:
            file_path = getattr(source, 'file_path', 'Unknown')
            relevance = getattr(source, 'relevance_score', 0.0)
            snippet = getattr(source, 'snippet', 'No snippet available')
            repo = getattr(source, 'repo', 'Unknown')
            file_type = getattr(source, 'file_type', 'Unknown')

        formatted.append(f"""
Source {idx}:
File: {file_path}
Repository: {repo}
Type: {file_type}
Relevance Score: {relevance:.2f}
Code Snippet:
```
{snippet}
```
---""")

    return "\n".join(formatted)


async def enhance_with_gemini(
    user_query: str,
    vectara_summary: Optional[str],
    vectara_sources: List[Any]
) -> str:
    """
    Enhance Vectara results using Gemini 2.5 Flash.

    Args:
        user_query: Original user question
        vectara_summary: RAG-generated summary from Vectara
        vectara_sources: List of relevant code files

    Returns:
        Enhanced AI response (5-6 lines + optional code samples)

    Raises:
        Exception: If Gemini API call fails
    """
    try:
        logger.info(f"🤖 Enhancing search results with Gemini for query: '{user_query}'")

        # Initialize Gemini client
        client = init_gemini_client()

        # Format sources for the prompt
        sources_text = format_sources_for_gemini(vectara_sources)

        # Build comprehensive prompt for Gemini
        prompt = f"""You are an AI code assistant analyzing search results from a GitHub codebase.

**User Question:** {user_query}

**Search Results Summary from RAG System:**
{vectara_summary or 'No summary provided'}

**Relevant Code Files and Snippets:**
{sources_text}

**Your Task:**
1. Carefully analyze the user's question and the search results
2. Provide a clear, concise answer in **5-6 lines of text maximum**
3. If the question asks about code implementation or specific files, include relevant code samples with file names
4. Focus on what the user actually wants to know - be direct and helpful
5. If the search results don't fully answer the question, acknowledge this and provide the best answer you can

**Response Format:**
- Start with a brief explanation (5-6 lines)
- If applicable, include code samples with file names in markdown format
- Be conversational but professional

**Important:** Keep your response concise and to the point. Don't repeat the question or add unnecessary verbosity."""

        # Call Gemini API
        logger.info("📡 Calling Gemini 2.5 Flash API...")
        model = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                top_p=0.95,
                max_output_tokens=1024,
            )
        )

        # Extract response text
        enhanced_response = model.text

        logger.info(f"✅ Gemini enhancement completed: {len(enhanced_response)} characters")
        return enhanced_response

    except Exception as e:
        logger.error(f"❌ Gemini enhancement failed: {str(e)}")
        # Fallback to original summary if Gemini fails
        logger.warning("⚠️ Falling back to original Vectara summary")
        return vectara_summary or "Unable to generate enhanced response. Please try again."
