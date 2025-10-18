"""
Example usage scripts for the GitHub Repository Content Fetcher API.

These examples demonstrate different ways to interact with the API.
"""

import asyncio
import httpx
import json


# Example 1: Simple synchronous request
def example_sync_request():
    """Simple synchronous request using requests library."""
    import requests

    print("Example 1: Simple Synchronous Request")
    print("=" * 60)

    response = requests.post(
        "http://localhost:8000/fetch-repo",
        json={"repo_url": "https://github.com/octocat/Hello-World"}
    )

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success! Fetched {data['total_files']} files from {data['owner']}/{data['repo']}")
        print(f"\nFirst file: {data['files'][0]['path']}")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)


# Example 2: Async request with httpx
async def example_async_request():
    """Asynchronous request using httpx."""
    print("\nExample 2: Asynchronous Request")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/fetch-repo",
            json={"repo_url": "https://github.com/octocat/Hello-World"},
            timeout=60.0
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success! Fetched {data['total_files']} files")

            # Group files by extension
            extensions = {}
            for file in data['files']:
                ext = file['path'].split('.')[-1] if '.' in file['path'] else 'no-ext'
                extensions[ext] = extensions.get(ext, 0) + 1

            print("\nFiles by extension:")
            for ext, count in extensions.items():
                print(f"  .{ext}: {count}")
        else:
            print(f"❌ Error: {response.status_code}")


# Example 3: Multiple repositories
async def example_multiple_repos():
    """Fetch multiple repositories in parallel."""
    print("\nExample 3: Multiple Repositories (Parallel)")
    print("=" * 60)

    repos = [
        "https://github.com/octocat/Hello-World",
        "https://github.com/octocat/Spoon-Knife",
    ]

    async with httpx.AsyncClient() as client:
        tasks = [
            client.post(
                "http://localhost:8000/fetch-repo",
                json={"repo_url": repo},
                timeout=60.0
            )
            for repo in repos
        ]

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        for repo, response in zip(repos, responses):
            if isinstance(response, Exception):
                print(f"❌ {repo}: {response}")
            elif response.status_code == 200:
                data = response.json()
                print(f"✅ {data['owner']}/{data['repo']}: {data['total_files']} files")
            else:
                print(f"❌ {repo}: HTTP {response.status_code}")


# Example 4: Search for specific files
def example_search_files():
    """Search for specific file types in the response."""
    import requests

    print("\nExample 4: Search for Specific Files")
    print("=" * 60)

    response = requests.post(
        "http://localhost:8000/fetch-repo",
        json={"repo_url": "https://github.com/octocat/Hello-World"}
    )

    if response.status_code == 200:
        data = response.json()

        # Find all Python files
        python_files = [f for f in data['files'] if f['path'].endswith('.py')]
        print(f"Found {len(python_files)} Python files:")
        for f in python_files:
            print(f"  - {f['path']}")

        # Find all markdown files
        md_files = [f for f in data['files'] if f['path'].endswith('.md')]
        print(f"\nFound {len(md_files)} Markdown files:")
        for f in md_files:
            print(f"  - {f['path']}")

        # Find files containing specific text
        print("\nSearching for files containing 'hello':")
        for f in data['files']:
            if 'hello' in f.get('content', '').lower():
                print(f"  - {f['path']}")


# Example 5: Save to files
def example_save_to_files():
    """Save repository contents to local files."""
    import requests
    import os
    from pathlib import Path

    print("\nExample 5: Save Repository to Local Files")
    print("=" * 60)

    response = requests.post(
        "http://localhost:8000/fetch-repo",
        json={"repo_url": "https://github.com/octocat/Hello-World"}
    )

    if response.status_code == 200:
        data = response.json()

        # Create output directory
        output_dir = Path(f"downloaded_{data['owner']}_{data['repo']}")
        output_dir.mkdir(exist_ok=True)

        print(f"Saving files to: {output_dir}/")

        for file in data['files']:
            # Create subdirectories if needed
            file_path = output_dir / file['path']
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(file.get('content', ''))

            print(f"  ✅ Saved: {file['path']}")

        print(f"\n✅ Saved {len(data['files'])} files to {output_dir}/")


# Example 6: Analyze code statistics
def example_code_statistics():
    """Calculate statistics about the repository code."""
    import requests

    print("\nExample 6: Code Statistics")
    print("=" * 60)

    response = requests.post(
        "http://localhost:8000/fetch-repo",
        json={"repo_url": "https://github.com/octocat/Hello-World"}
    )

    if response.status_code == 200:
        data = response.json()

        # Calculate statistics
        total_size = sum(f.get('size', 0) for f in data['files'])
        total_lines = sum(len(f.get('content', '').splitlines()) for f in data['files'])

        print(f"Repository: {data['owner']}/{data['repo']}")
        print(f"Total Files: {data['total_files']}")
        print(f"Total Size: {total_size:,} bytes ({total_size / 1024:.2f} KB)")
        print(f"Total Lines: {total_lines:,}")

        # Find largest files
        print("\nLargest files:")
        sorted_files = sorted(data['files'], key=lambda x: x.get('size', 0), reverse=True)
        for f in sorted_files[:5]:
            print(f"  {f['size']:>6} bytes - {f['path']}")


# Example 7: Error handling
def example_error_handling():
    """Demonstrate proper error handling."""
    import requests

    print("\nExample 7: Error Handling")
    print("=" * 60)

    test_cases = [
        ("Invalid URL", "not-a-valid-url"),
        ("Non-existent repo", "https://github.com/this-repo/does-not-exist-123456"),
        ("Valid repo", "https://github.com/octocat/Hello-World"),
    ]

    for name, url in test_cases:
        print(f"\nTesting: {name}")
        try:
            response = requests.post(
                "http://localhost:8000/fetch-repo",
                json={"repo_url": url},
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                print(f"  ✅ Success: {data['total_files']} files")
            else:
                error = response.json()
                print(f"  ❌ Error {response.status_code}: {error.get('detail', 'Unknown error')}")

        except requests.exceptions.RequestException as e:
            print(f"  ❌ Request failed: {e}")


# Main execution
if __name__ == "__main__":
    print("GitHub Repository Content Fetcher - Usage Examples")
    print("=" * 60)
    print("\n⚠️  Make sure the FastAPI server is running on http://localhost:8000")
    print("   Start it with: python main.py\n")

    try:
        # Run examples
        example_sync_request()
        asyncio.run(example_async_request())
        asyncio.run(example_multiple_repos())
        example_search_files()
        example_save_to_files()
        example_code_statistics()
        example_error_handling()

        print("\n" + "=" * 60)
        print("✨ All examples completed!")

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        print("\nMake sure:")
        print("  1. FastAPI server is running (python main.py)")
        print("  2. GITHUB_TOKEN is set in .env")
        print("  3. Dependencies are installed (pip install -r requirements.txt)")
