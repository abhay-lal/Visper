"""FastAPI application for fetching GitHub repository contents."""

import os
import json
import logging
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from utils import parse_github_url
from github_client import GitHubAPIClient


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="GitHub Repository Content Fetcher",
    description="Fetch and display all files from a GitHub repository",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    logger.info(f"📨 Incoming request: {request.method} {request.url.path}")
    logger.info(f"   Client: {request.client.host}")
    logger.info(f"   Headers: {dict(request.headers)}")

    response = await call_next(request)

    logger.info(f"📤 Response status: {response.status_code}")
    return response


class RepoRequest(BaseModel):
    """Request model for repository URL."""
    repo_url: str = Field(
        ...,
        description="GitHub repository URL (e.g., https://github.com/owner/repo)",
        example="https://github.com/octocat/Hello-World"
    )


class RepoResponse(BaseModel):
    """Response model for repository contents."""
    owner: str
    repo: str
    total_files: int
    files: list


def print_file_info(file_data: Dict[str, Any]) -> None:
    """
    Print structured file information to console.

    Args:
        file_data: Dictionary containing file metadata and content
    """
    print("\n" + "="*80)
    print(f"📄 FILE: {file_data.get('path', 'Unknown')}")
    print("="*80)
    print(f"Name: {file_data.get('name', 'Unknown')}")
    print(f"Type/Extension: {os.path.splitext(file_data.get('name', ''))[1] or 'no extension'}")
    print(f"Size: {file_data.get('size', 0)} bytes")
    print(f"\n{'-'*80}")
    print("CONTENT:")
    print(f"{'-'*80}")

    content = file_data.get('content', '')
    if content:
        # Limit console output for very large files
        if len(content) > 5000:
            print(content[:5000])
            print(f"\n... [Content truncated - showing first 5000 characters of {len(content)} total]")
        else:
            print(content)
    else:
        print("[Empty file or no content]")

    print("="*80 + "\n")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    logger.info("📍 Root endpoint accessed")
    return {
        "message": "GitHub Repository Content Fetcher API",
        "status": "running",
        "endpoints": {
            "/fetch-repo": "POST - Fetch all files from a GitHub repository (use POST method!)",
            "/docs": "GET - Interactive API documentation",
            "/redoc": "GET - Alternative API documentation"
        },
        "example_curl": 'curl -X POST http://localhost:8000/fetch-repo -H "Content-Type: application/json" -d \'{"repo_url": "https://github.com/octocat/Hello-World"}\'',
        "note": "⚠️ /fetch-repo requires POST method, not GET"
    }


@app.post("/fetch-repo", response_model=RepoResponse)
async def fetch_repository(request: RepoRequest):
    """
    Fetch all files from a GitHub repository.

    This endpoint:
    1. Parses the GitHub repository URL
    2. Connects to GitHub API using the token from environment variables
    3. Recursively traverses all directories
    4. Fetches all files (excluding binary/image files)
    5. Prints structured output to console
    6. Returns the collected data

    Args:
        request: RepoRequest containing the repository URL

    Returns:
        RepoResponse with owner, repo name, file count, and all file data

    Raises:
        HTTPException: If URL is invalid, token is missing, or API request fails
    """
    logger.info(f"🔍 Received fetch request for: {request.repo_url}")
    print("\n" + "🚀"*40)
    print("STARTING REPOSITORY FETCH")
    print("🚀"*40)
    print(f"Repository URL: {request.repo_url}\n")

    # Parse GitHub URL
    try:
        owner, repo = parse_github_url(request.repo_url)
        logger.info(f"✅ Successfully parsed URL - Owner: {owner}, Repo: {repo}")
        print(f"✅ Parsed URL successfully:")
        print(f"   Owner: {owner}")
        print(f"   Repository: {repo}\n")
    except HTTPException as e:
        logger.error(f"❌ Failed to parse URL: {e.detail}")
        print(f"❌ Failed to parse URL: {e.detail}")
        raise

    # Initialize GitHub client
    try:
        github_client = GitHubAPIClient()
        logger.info("✅ GitHub API client initialized")
        print("✅ GitHub API client initialized\n")
    except HTTPException as e:
        logger.error(f"❌ Failed to initialize GitHub client: {e.detail}")
        print(f"❌ Failed to initialize GitHub client: {e.detail}")
        raise

    # Fetch all files recursively
    logger.info(f"📥 Starting recursive file fetch for {owner}/{repo}")
    print("📥 Starting recursive file fetch...\n")
    try:
        all_files = await github_client.fetch_all_files_recursive(owner, repo)
        logger.info(f"✅ Fetch completed! Retrieved {len(all_files)} files")
        print(f"\n✅ Fetch completed! Total files retrieved: {len(all_files)}\n")
    except Exception as e:
        logger.error(f"❌ Error during fetch: {str(e)}")
        print(f"❌ Error during fetch: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch repository contents: {str(e)}"
        )

    # Print structured output for each file
    print("\n" + "📋"*40)
    print("DETAILED FILE CONTENTS")
    print("📋"*40 + "\n")

    for file_data in all_files:
        print_file_info(file_data)

    # Print summary
    print("\n" + "📊"*40)
    print("SUMMARY")
    print("📊"*40)
    print(f"Owner: {owner}")
    print(f"Repository: {repo}")
    print(f"Total files fetched: {len(all_files)}")

    # Group files by extension
    extensions = {}
    for file_data in all_files:
        ext = os.path.splitext(file_data.get('name', ''))[1] or 'no extension'
        extensions[ext] = extensions.get(ext, 0) + 1

    print("\nFiles by type:")
    for ext, count in sorted(extensions.items(), key=lambda x: x[1], reverse=True):
        print(f"  {ext}: {count} file(s)")

    print("="*80 + "\n")

    # Return response
    return RepoResponse(
        owner=owner,
        repo=repo,
        total_files=len(all_files),
        files=all_files
    )


if __name__ == "__main__":
    import uvicorn

    # Check if GITHUB_TOKEN is set
    if not os.getenv("GITHUB_TOKEN"):
        print("⚠️  WARNING: GITHUB_TOKEN environment variable is not set!")
        print("Please set it before running the application:")
        print("  export GITHUB_TOKEN=your_token_here")
        print("\nOr create a .env file with:")
        print("  GITHUB_TOKEN=your_token_here\n")

    print("Starting FastAPI server...")
    print("API Documentation: http://localhost:8000/docs")
    print("Interactive API: http://localhost:8000/redoc\n")

    uvicorn.run(app, host="0.0.0.0", port=8000)
