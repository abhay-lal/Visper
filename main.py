"""FastAPI application for fetching GitHub repository contents."""

import os
import json
import logging
import subprocess
import sys
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from utils import parse_github_url
from github_client import GitHubAPIClient
from vectara_client import VectaraClient


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


class SearchRequest(BaseModel):
    """Request model for searching Vectara corpus."""
    query: str = Field(
        ...,
        description="Natural language search query",
        example="explain me search functionality"
    )
    repo: Optional[str] = Field(
        None,
        description="Filter by specific repository name (e.g., 'sentinelai' or 'owner/repo')",
        example="sentinelai"
    )
    owner: Optional[str] = Field(
        None,
        description="Filter by repository owner",
        example="KshitijD21"
    )
    limit: int = Field(
        5,
        ge=1,
        le=20,
        description="Number of results to return (default: 5, max: 20)",
        example=5
    )


class SearchSource(BaseModel):
    """Model for a single search result source."""
    file_path: str
    file_name: str
    file_type: str
    repo: str
    owner: str
    source_url: str
    relevance_score: float
    snippet: str


class SearchResponse(BaseModel):
    """Response model for search results."""
    query: str = Field(..., description="Original search query from user")
    summary: Optional[str] = Field(None, description="AI-generated summary answer from RAG")
    sources: List[SearchSource] = Field(..., description="List of matching files")
    total_results: int = Field(..., description="Total number of results found")
    query_time_ms: int = Field(..., description="Query execution time in milliseconds")
    filters_applied: Dict[str, Any] = Field(..., description="Filters that were applied to the search")


class RepoResponse(BaseModel):
    """Response model for repository contents."""
    owner: str
    repo: str
    total_files: int
    files: list
    vectara_ingestion: Dict[str, Any] = None


class VideoStatusResponse(BaseModel):
    """Response model for video generation status and URLs."""
    status: str
    gcs_uri: Optional[str] = None
    public_url: Optional[str] = None
    updated_at: Optional[str] = None


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
            "/search": "POST - Search the Vectara corpus with natural language queries",
            "/docs": "GET - Interactive API documentation",
            "/redoc": "GET - Alternative API documentation"
        },
        "example_curl": 'curl -X POST http://localhost:8000/fetch-repo -H "Content-Type: application/json" -d \'{"repo_url": "https://github.com/octocat/Hello-World"}\'',
        "search_example": 'curl -X POST http://localhost:8000/search -H "Content-Type: application/json" -d \'{"query": "explain me search functionality", "limit": 5}\'',
        "note": "⚠️ /fetch-repo requires POST method, not GET"
    }


@app.post("/search", response_model=SearchResponse)
async def search_corpus(request: SearchRequest):
    """
    Search the Vectara corpus with natural language queries.

    This endpoint:
    1. Accepts a natural language query from the user
    2. Searches the Vectara corpus using semantic search
    3. Optionally filters by repository and/or owner
    4. Returns an AI-generated summary (RAG) and top matching sources
    5. Includes relevance scores and snippets for each result

    Args:
        request: SearchRequest containing query and optional filters

    Returns:
        SearchResponse with summary, sources, and metadata

    Raises:
        HTTPException: If Vectara credentials are missing or search fails
    """
    logger.info(f"🔍 Search request received: '{request.query}'")
    logger.info(f"   Filters: repo={request.repo}, owner={request.owner}, limit={request.limit}")

    print("\n" + "🔍"*40)
    print("SEARCH REQUEST")
    print("🔍"*40)
    print(f"Query: {request.query}")
    print(f"Repo filter: {request.repo or 'None'}")
    print(f"Owner filter: {request.owner or 'None'}")
    print(f"Limit: {request.limit}")
    print("="*80 + "\n")

    # Initialize Vectara client
    try:
        vectara_client = VectaraClient()
        logger.info("✅ Vectara client initialized for search")
    except HTTPException as e:
        logger.error(f"❌ Failed to initialize Vectara client: {e.detail}")
        print(f"❌ Vectara initialization failed: {e.detail}\n")
        raise HTTPException(
            status_code=500,
            detail=f"Vectara service unavailable: {e.detail}"
        )

    # Perform search
    try:
        search_results = await vectara_client.search_corpus(
            query=request.query,
            limit=request.limit,
            repo_filter=request.repo,
            owner_filter=request.owner,
            enable_rag=True
        )

        logger.info(f"✅ Search completed successfully")
        print(f"✅ Search completed: {search_results['total_results']} results in {search_results['query_time_ms']}ms\n")

        # Build response with original query included
        filters_applied = {}
        if request.repo:
            filters_applied["repo"] = request.repo
        if request.owner:
            filters_applied["owner"] = request.owner
        filters_applied["limit"] = request.limit

        response = SearchResponse(
            query=request.query,  # Include original query in response
            summary=search_results.get("summary"),
            sources=[SearchSource(**source) for source in search_results.get("sources", [])],
            total_results=search_results.get("total_results", 0),
            query_time_ms=search_results.get("query_time_ms", 0),
            filters_applied=filters_applied
        )

        # Pretty print response for debugging
        print("📊 SEARCH RESPONSE:")
        print("="*80)
        print(f"Original Query: {response.query}")
        print(f"Summary: {response.summary[:200] if response.summary else 'No summary generated'}...")
        print(f"Total Results: {response.total_results}")
        print(f"Sources Returned: {len(response.sources)}")
        print(f"Query Time: {response.query_time_ms}ms")
        print(f"Filters Applied: {response.filters_applied}")
        print("="*80 + "\n")

        return response

    except HTTPException as e:
        logger.error(f"❌ Search failed: {e.detail}")
        print(f"❌ Search error: {e.detail}\n")
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected search error: {str(e)}")
        print(f"❌ Unexpected error: {str(e)}\n")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


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

    # Ingest files into Vectara
    vectara_stats = None
    try:
        logger.info("🔄 Starting Vectara ingestion...")
        vectara_client = VectaraClient()
        vectara_stats = await vectara_client.ingest_files(all_files, owner, repo)
        logger.info(f"✅ Vectara ingestion completed: {vectara_stats}")
    except HTTPException as e:
        logger.warning(f"⚠️  Vectara ingestion skipped: {e.detail}")
        print(f"⚠️  Vectara ingestion skipped: {e.detail}\n")
        vectara_stats = {
            "status": "skipped",
            "reason": e.detail
        }
    except Exception as e:
        logger.error(f"❌ Vectara ingestion error: {str(e)}")
        print(f"❌ Vectara ingestion error: {str(e)}\n")
        vectara_stats = {
            "status": "error",
            "error": str(e)
        }

    # Always trigger agent launch after Vectara ingestion attempt (no success check)
    try:
        logger.info("▶️ Launching agent_router.py in background (no Vectara success check)…")
        env = os.environ.copy()
        env["GITHUB_URL"] = request.repo_url
        env.setdefault("AUTO_RUN_PIPELINE", "true")
        # uAgents expects PORT; keep AGENT_PORT for our logs
        env.setdefault("AGENT_PORT", "8100")
        env.setdefault("PORT", env.get("AGENT_PORT", "8100"))
        out_dir = env.get("OUT_DIR", "media")
        os.makedirs(out_dir, exist_ok=True)
        agent_log = os.path.join(out_dir, "agent_router.log")
        agent_pid_file = os.path.join(out_dir, "agent_router.pid")
        agent_status_file = os.path.join(out_dir, "agent_status.json")
        agent_path = os.path.join(os.path.dirname(__file__), "agent_router.py")

        if not os.path.exists(agent_path):
            logger.error(f"❌ agent_router.py not found at {agent_path}")
        else:
            # Write a header line to the log and launch
            try:
                with open(agent_log, "a", encoding="utf-8") as lf:
                    lf.write("\n" + "="*80 + "\n")
                    lf.write("Starting agent_router.py\n")
                    lf.write(f"Repo: {request.repo_url}\n")
                    lf.write(f"Time: {__import__('datetime').datetime.utcnow().isoformat()}Z\n")
                    lf.write("="*80 + "\n")
                proc = subprocess.Popen(
                    [sys.executable or "python", agent_path],
                    env=env,
                    stdout=open(agent_log, "a"),
                    stderr=open(agent_log, "a")
                )
                # Persist PID and status for visibility
                try:
                    with open(agent_pid_file, "w", encoding="utf-8") as pf:
                        pf.write(str(proc.pid))
                    with open(agent_status_file, "w", encoding="utf-8") as sf:
                        json.dump({
                            "status": "launched",
                            "pid": proc.pid,
                            "repo_url": request.repo_url,
                            "log_file": agent_log,
                            "started_at": __import__('datetime').datetime.utcnow().isoformat() + "Z"
                        }, sf, indent=2)
                except Exception as persist_err:
                    logger.warning(f"⚠️ Failed to write agent PID/status files: {persist_err}")
                logger.info(f"🚀 agent_router.py started with PID {proc.pid}. Logs: {agent_log}")
            except Exception as launch_err:
                logger.error(f"❌ Failed launching agent_router.py: {launch_err}")
    except Exception as e:
        logger.warning(f"⚠️ Failed to start agent_router.py: {e}")

    # Return response
    return RepoResponse(
        owner=owner,
        repo=repo,
        total_files=len(all_files),
        files=all_files,
        vectara_ingestion=vectara_stats
    )


@app.get("/video-status", response_model=VideoStatusResponse)
async def video_status():
    """Expose the latest video generation status and URL to the frontend."""
    status_file = os.getenv("VIDEO_STATUS_FILE", os.path.join(os.getenv("OUT_DIR", "media"), "video_status.json"))
    try:
        if os.path.exists(status_file):
            with open(status_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Basic validation
            status = data.get("status", "unknown")
            return VideoStatusResponse(
                status=status,
                gcs_uri=data.get("gcs_uri"),
                public_url=data.get("public_url"),
                updated_at=data.get("updated_at")
            )
        else:
            return VideoStatusResponse(status="pending")
    except Exception as e:
        logger.error(f"❌ Failed reading video status: {e}")
        raise HTTPException(status_code=500, detail="Failed to read video status")


class AgentStatusResponse(BaseModel):
    """Response model for agent process status."""
    running: bool
    pid: Optional[int] = None
    repo_url: Optional[str] = None
    log_file: Optional[str] = None
    started_at: Optional[str] = None


@app.get("/agent-status", response_model=AgentStatusResponse)
async def agent_status():
    """Report whether agent_router.py is currently running and where logs are written."""
    out_dir = os.getenv("OUT_DIR", "media")
    pid_path = os.path.join(out_dir, "agent_router.pid")
    status_path = os.path.join(out_dir, "agent_status.json")
    log_path = os.path.join(out_dir, "agent_router.log")
    pid = None
    try:
        if os.path.exists(pid_path):
            with open(pid_path, "r", encoding="utf-8") as f:
                pid = int((f.read() or "0").strip() or "0")
        running = False
        if pid:
            try:
                # On Unix, signal 0 checks existence without sending a signal
                os.kill(pid, 0)
                running = True
            except Exception:
                running = False
        meta = {}
        if os.path.exists(status_path):
            with open(status_path, "r", encoding="utf-8") as sf:
                meta = json.load(sf)
        return AgentStatusResponse(
            running=running,
            pid=pid if pid else None,
            repo_url=meta.get("repo_url"),
            log_file=log_path if os.path.exists(log_path) else None,
            started_at=meta.get("started_at")
        )
    except Exception as e:
        logger.error(f"❌ Failed to read agent status: {e}")
        raise HTTPException(status_code=500, detail="Failed to read agent status")


if __name__ == "__main__":
    import uvicorn

    # Check if GITHUB_TOKEN is set
    if not os.getenv("GITHUB_TOKEN"):
        print("⚠️  WARNING: GITHUB_TOKEN environment variable is not set!")
        print("Please set it before running the application:")
        print("  export GITHUB_TOKEN=your_token_here")
        print("\nOr create a .env file with:")
        print("  GITHUB_TOKEN=your_token_here\n")

    # Check if Vectara credentials are set
    vectara_vars = ["VECTARA_CORPUS_KEY", "VECTARA_API_KEY"]
    missing_vectara = [var for var in vectara_vars if not os.getenv(var)]

    if missing_vectara:
        print("⚠️  WARNING: Some Vectara environment variables are not set:")
        for var in missing_vectara:
            print(f"  - {var}")
        print("\nVectara ingestion will be skipped if these are not configured.")
        print("Add them to your .env file or set them as environment variables.\n")

    print("Starting FastAPI server...")
    print("API Documentation: http://localhost:8000/docs")
    print("Interactive API: http://localhost:8000/redoc\n")

    uvicorn.run(app, host="0.0.0.0", port=8200)
