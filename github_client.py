"""GitHub API client for fetching repository contents."""

import os
import base64
import logging
from typing import List, Dict, Any, Optional
import httpx
from fastapi import HTTPException

# Configure logger
logger = logging.getLogger(__name__)


# Binary file extensions to ignore
BINARY_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.ico', '.webp',  # Images
    '.pdf', '.zip', '.tar', '.gz', '.rar', '.7z',  # Archives
    '.exe', '.dll', '.so', '.dylib',  # Binaries
    '.mp3', '.mp4', '.avi', '.mov', '.wmv', '.flv',  # Media
    '.ttf', '.woff', '.woff2', '.eot',  # Fonts
    '.class', '.jar', '.war',  # Compiled Java
    '.pyc', '.pyo',  # Compiled Python
}


class GitHubAPIClient:
    """Client for interacting with the GitHub REST API."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: Optional[str] = None):
        """
        Initialize the GitHub API client.

        Args:
            token: GitHub personal access token. If not provided, will try to read from GITHUB_TOKEN env var.

        Raises:
            HTTPException: If no token is provided or found in environment
        """
        self.token = token or os.getenv("GITHUB_TOKEN")

        if not self.token:
            raise HTTPException(
                status_code=500,
                detail="GitHub token not found. Please set the GITHUB_TOKEN environment variable."
            )

        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }

    async def get_repo_contents(self, owner: str, repo: str, path: str = "") -> List[Dict[str, Any]]:
        """
        Get the contents of a repository at a specific path.

        Args:
            owner: Repository owner
            repo: Repository name
            path: Path within the repository (empty string for root)

        Returns:
            List of content items (files and directories)

        Raises:
            HTTPException: If the API request fails
        """
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/contents/{path}"
        logger.info(f"🌐 Fetching contents from: {url}")

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, timeout=30.0)

            logger.info(f"📡 Response status: {response.status_code}")

            if response.status_code == 404:
                logger.error(f"❌ 404 Not Found: {owner}/{repo}/{path}")
                logger.error(f"Response: {response.text}")
                raise HTTPException(
                    status_code=404,
                    detail=f"Repository not found or path does not exist: {owner}/{repo}/{path}"
                )
            elif response.status_code == 403:
                logger.error(f"❌ 403 Forbidden - Rate limit or permissions issue")
                logger.error(f"Response: {response.text}")
                raise HTTPException(
                    status_code=403,
                    detail="API rate limit exceeded or insufficient permissions. Check your GitHub token."
                )
            elif response.status_code != 200:
                logger.error(f"❌ GitHub API error {response.status_code}: {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"GitHub API error: {response.text}"
                )

            data = response.json()
            logger.info(f"✅ Retrieved {len(data)} items from {path or 'root'}")
            return data

    async def get_file_content(self, owner: str, repo: str, path: str) -> Dict[str, Any]:
        """
        Get the content of a specific file.

        Args:
            owner: Repository owner
            repo: Repository name
            path: Path to the file

        Returns:
            Dictionary containing file metadata and decoded content
        """
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/contents/{path}"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, timeout=30.0)

            if response.status_code != 200:
                return {
                    "path": path,
                    "type": "error",
                    "content": f"Failed to fetch file: {response.status_code}"
                }

            data = response.json()

            # Decode base64 content
            if "content" in data and data.get("encoding") == "base64":
                try:
                    content = base64.b64decode(data["content"]).decode('utf-8')
                except UnicodeDecodeError:
                    # Handle binary files that can't be decoded as UTF-8
                    content = "[Binary content - cannot display as text]"
            else:
                content = data.get("content", "")

            return {
                "path": data.get("path", path),
                "name": data.get("name", ""),
                "type": data.get("type", "file"),
                "size": data.get("size", 0),
                "content": content
            }

    def should_ignore_file(self, filename: str) -> bool:
        """
        Check if a file should be ignored based on its extension.

        Args:
            filename: Name of the file

        Returns:
            True if the file should be ignored, False otherwise
        """
        extension = os.path.splitext(filename)[1].lower()
        return extension in BINARY_EXTENSIONS

    async def fetch_all_files_recursive(
        self,
        owner: str,
        repo: str,
        path: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Recursively fetch all files from a repository, ignoring binary files.

        Args:
            owner: Repository owner
            repo: Repository name
            path: Current path in the repository

        Returns:
            List of all file contents with metadata
        """
        all_files = []

        try:
            logger.info(f"📂 Fetching contents of: {path or 'root'}")
            contents = await self.get_repo_contents(owner, repo, path)

            logger.info(f"📋 Found {len(contents)} items in {path or 'root'}")

            for item in contents:
                item_path = item.get("path", "")
                item_type = item.get("type", "")
                item_name = item.get("name", "")

                logger.info(f"  Processing: {item_name} (type: {item_type})")

                if item_type == "file":
                    # Check if we should ignore this file
                    if self.should_ignore_file(item_name):
                        logger.info(f"⏩ Skipping binary file: {item_path}")
                        print(f"⏩ Skipping binary file: {item_path}")
                        continue

                    # Fetch file content
                    logger.info(f"📄 Fetching file: {item_path}")
                    print(f"📄 Fetching file: {item_path}")
                    file_data = await self.get_file_content(owner, repo, item_path)
                    all_files.append(file_data)

                elif item_type == "dir":
                    # Recursively fetch directory contents
                    logger.info(f"📁 Entering directory: {item_path}")
                    print(f"📁 Entering directory: {item_path}")
                    subdir_files = await self.fetch_all_files_recursive(owner, repo, item_path)
                    all_files.extend(subdir_files)
                else:
                    logger.warning(f"⚠️  Unknown item type '{item_type}' for: {item_path}")

        except HTTPException as e:
            logger.error(f"❌ HTTPException while fetching {path}: {e.detail}")
            print(f"❌ Error fetching {path}: {e.detail}")
            raise
        except Exception as e:
            logger.error(f"❌ Exception while fetching {path}: {str(e)}")
            print(f"❌ Error fetching {path}: {str(e)}")

        return all_files
