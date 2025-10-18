"""Utility functions for parsing GitHub repository URLs."""

import re
from typing import Tuple
from fastapi import HTTPException


def parse_github_url(url: str) -> Tuple[str, str]:
    """
    Parse a GitHub repository URL and extract owner and repository name.

    Supports various GitHub URL formats:
    - https://github.com/owner/repo
    - https://github.com/owner/repo.git
    - git@github.com:owner/repo.git
    - github.com/owner/repo

    Args:
        url: GitHub repository URL

    Returns:
        Tuple of (owner, repo_name)

    Raises:
        HTTPException: If the URL format is invalid
    """
    # Remove trailing slashes
    url = url.rstrip('/')

    # Remove .git extension if present (but don't strip individual characters!)
    if url.endswith('.git'):
        url = url[:-4]

    # Pattern for HTTPS URLs
    https_pattern = r'(?:https?://)?(?:www\.)?github\.com/([^/]+)/([^/]+)'
    # Pattern for SSH URLs
    ssh_pattern = r'git@github\.com:([^/]+)/([^/]+)'

    # Try HTTPS pattern first
    match = re.match(https_pattern, url)
    if match:
        owner, repo = match.groups()
        # Clean up any remaining special characters
        repo = repo.rstrip('/')
        return owner, repo

    # Try SSH pattern
    match = re.match(ssh_pattern, url)
    if match:
        owner, repo = match.groups()
        # Clean up any remaining special characters
        repo = repo.rstrip('/')
        return owner, repo

    # If no pattern matched, raise an error
    raise HTTPException(
        status_code=400,
        detail=f"Invalid GitHub URL format: {url}. Expected format: https://github.com/owner/repo"
    )
