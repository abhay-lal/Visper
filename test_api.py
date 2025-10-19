"""
Test script for the GitHub Repository Content Fetcher API.

This script demonstrates how to use the API to fetch repository contents.
"""

import requests
import json
import sys


def test_fetch_repo(repo_url: str):
    """
    Test the /fetch-repo endpoint with a given repository URL.

    Args:
        repo_url: GitHub repository URL to fetch
    """
    api_url = "http://localhost:8000/fetch-repo"

    print(f"🧪 Testing GitHub Repository Content Fetcher")
    print(f"Repository: {repo_url}")
    print(f"API Endpoint: {api_url}")
    print("=" * 80)

    try:
        # Make the API request
        print("\n📡 Sending request to API...")
        response = requests.post(
            api_url,
            json={"repo_url": repo_url},
            timeout=60  # 60 second timeout for large repos
        )

        # Check if request was successful
        response.raise_for_status()

        # Parse response
        data = response.json()

        # Display results
        print("\n✅ Request successful!")
        print(f"\n📊 Summary:")
        print(f"   Owner: {data['owner']}")
        print(f"   Repository: {data['repo']}")
        print(f"   Total Files: {data['total_files']}")

        # Show first few files
        print(f"\n📄 First few files:")
        for i, file_data in enumerate(data['files'][:5], 1):
            print(f"   {i}. {file_data['path']} ({file_data['size']} bytes)")

        if len(data['files']) > 5:
            print(f"   ... and {len(data['files']) - 5} more files")

        # Group by extension
        extensions = {}
        for file_data in data['files']:
            ext = file_data['path'].split('.')[-1] if '.' in file_data['path'] else 'no extension'
            extensions[ext] = extensions.get(ext, 0) + 1

        print(f"\n📁 Files by extension:")
        for ext, count in sorted(extensions.items(), key=lambda x: x[1], reverse=True):
            print(f"   .{ext}: {count} file(s)")

        print("\n" + "=" * 80)
        print("✨ Test completed successfully!")

        return True

    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to the API server.")
        print("   Make sure the FastAPI server is running on http://localhost:8000")
        print("   Run it with: python main.py")
        return False

    except requests.exceptions.Timeout:
        print("\n❌ Error: Request timed out.")
        print("   The repository might be too large. Try a smaller repository.")
        return False

    except requests.exceptions.HTTPError as e:
        print(f"\n❌ HTTP Error: {e}")
        if response.status_code == 400:
            print("   The repository URL might be invalid.")
        elif response.status_code == 404:
            print("   Repository not found. Check the URL.")
        elif response.status_code == 403:
            print("   API rate limit exceeded or insufficient permissions.")
        elif response.status_code == 500:
            print("   Server error. Check if GITHUB_TOKEN is set correctly.")

        try:
            error_detail = response.json()
            print(f"   Details: {error_detail.get('detail', 'No details available')}")
        except:
            pass

        return False

    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        return False


if __name__ == "__main__":
    # Default test repository (small public repo)
    default_repo = "https://github.com/octocat/Hello-World"

    # Use command line argument if provided
    repo_url = sys.argv[1] if len(sys.argv) > 1 else default_repo

    print("\n" + "🧪" * 40)
    print("GitHub Repository Content Fetcher - Test Script")
    print("🧪" * 40 + "\n")

    if repo_url == default_repo:
        print("ℹ️  Using default test repository (octocat/Hello-World)")
        print("   To test with a different repo, run:")
        print("   python test_api.py https://github.com/owner/repo\n")

    success = test_fetch_repo(repo_url)

    if success:
        print("\n💡 Tip: Check the server console for detailed file contents!")
        sys.exit(0)
    else:
        print("\n💡 Troubleshooting:")
        print("   1. Make sure the FastAPI server is running")
        print("   2. Verify your GITHUB_TOKEN is set in .env")
        print("   3. Check that the repository URL is valid")
        print("   4. Try a smaller/public repository first")
        sys.exit(1)
