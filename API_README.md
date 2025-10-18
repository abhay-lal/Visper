# GitHub Repository Content Fetcher

A FastAPI backend service that fetches and displays all files from any GitHub repository using the official GitHub REST API.

## Features

✨ **Key Capabilities:**

- 🔗 Parse various GitHub URL formats (HTTPS, SSH, with/without .git)
- 🔐 Secure authentication using GitHub Personal Access Token from environment variables
- 📁 Recursive directory traversal to fetch all files
- 🚫 Automatic filtering of binary/image files
- 📝 Detailed console output with file paths, types, and contents
- 🎯 RESTful API with interactive documentation

## Prerequisites

- Python 3.8 or higher
- GitHub Personal Access Token
- pip (Python package installer)

## Installation

1. **Clone or navigate to this repository:**

   ```bash
   cd /Users/kshitij/Personal\ Project/tedai/BlindVerse
   ```

2. **Create and activate a virtual environment (recommended):**

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On macOS/Linux
   # Or on Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up your GitHub Personal Access Token:**

   a. **Generate a token:**

   - Go to GitHub Settings: https://github.com/settings/tokens
   - Click "Generate new token" (classic)
   - Select scopes:
     - `public_repo` (for public repositories)
     - `repo` (for private repositories)
   - Copy the generated token

   b. **Create a `.env` file:**

   ```bash
   cp .env.example .env
   ```

   c. **Edit `.env` and add your token:**

   ```
   GITHUB_TOKEN=your_github_token_here
   ```

   **⚠️ IMPORTANT:** Never commit your `.env` file or hardcode tokens in the code!

## Usage

### Starting the Server

Run the FastAPI server:

```bash
python main.py
```

Or use uvicorn directly:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The server will start at: `http://localhost:8000`

### API Documentation

Once the server is running, access the interactive API documentation:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Making API Requests

#### Using the Interactive Docs (Easiest)

1. Go to http://localhost:8000/docs
2. Click on `POST /fetch-repo`
3. Click "Try it out"
4. Enter a GitHub repository URL
5. Click "Execute"

#### Using curl

```bash
curl -X POST "http://localhost:8000/fetch-repo" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/octocat/Hello-World"
  }'
```

#### Using Python requests

```python
import requests

response = requests.post(
    "http://localhost:8000/fetch-repo",
    json={"repo_url": "https://github.com/octocat/Hello-World"}
)

data = response.json()
print(f"Fetched {data['total_files']} files from {data['owner']}/{data['repo']}")
```

#### Using JavaScript fetch

```javascript
fetch("http://localhost:8000/fetch-repo", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    repo_url: "https://github.com/octocat/Hello-World",
  }),
})
  .then((response) => response.json())
  .then((data) => console.log(data));
```

## Supported GitHub URL Formats

The API accepts various GitHub URL formats:

- ✅ `https://github.com/owner/repo`
- ✅ `https://github.com/owner/repo.git`
- ✅ `http://github.com/owner/repo`
- ✅ `github.com/owner/repo`
- ✅ `git@github.com:owner/repo.git`
- ✅ `git@github.com:owner/repo`

## Console Output

When a repository is fetched, the server prints detailed information to the console:

```
🚀🚀🚀 STARTING REPOSITORY FETCH 🚀🚀🚀
Repository URL: https://github.com/octocat/Hello-World

✅ Parsed URL successfully:
   Owner: octocat
   Repository: Hello-World

📥 Starting recursive file fetch...

📄 Fetching file: README.md
📁 Entering directory: src
📄 Fetching file: src/main.py
⏩ Skipping binary file: logo.png

================================================================================
📄 FILE: README.md
================================================================================
Name: README.md
Type/Extension: .md
Size: 1234 bytes

--------------------------------------------------------------------------------
CONTENT:
--------------------------------------------------------------------------------
# Hello World
This is a sample repository...
================================================================================

📊 SUMMARY 📊
Owner: octocat
Repository: Hello-World
Total files fetched: 5

Files by type:
  .md: 2 file(s)
  .py: 2 file(s)
  .txt: 1 file(s)
```

## API Response Structure

```json
{
  "owner": "octocat",
  "repo": "Hello-World",
  "total_files": 5,
  "files": [
    {
      "path": "README.md",
      "name": "README.md",
      "type": "file",
      "size": 1234,
      "content": "# Hello World\nThis is a sample repository..."
    },
    {
      "path": "src/main.py",
      "name": "main.py",
      "type": "file",
      "size": 567,
      "content": "def main():\n    print('Hello, World!')"
    }
  ]
}
```

## File Filtering

The following file types are automatically skipped (binary files):

- **Images:** `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.svg`, `.ico`, `.webp`
- **Archives:** `.pdf`, `.zip`, `.tar`, `.gz`, `.rar`, `.7z`
- **Binaries:** `.exe`, `.dll`, `.so`, `.dylib`
- **Media:** `.mp3`, `.mp4`, `.avi`, `.mov`, `.wmv`, `.flv`
- **Fonts:** `.ttf`, `.woff`, `.woff2`, `.eot`
- **Compiled:** `.class`, `.jar`, `.war`, `.pyc`, `.pyo`

## Project Structure

```
BlindVerse/
├── main.py              # FastAPI application and endpoints
├── github_client.py     # GitHub API client with recursive traversal
├── utils.py             # Utility functions (URL parser)
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variable template
├── .gitignore          # Git ignore rules
└── README.md           # This file
```

## Security Notes

🔒 **Important Security Practices:**

1. **Never commit your `.env` file** - It's already in `.gitignore`
2. **Never hardcode tokens** - Always use environment variables
3. **Keep your token secure** - Don't share it or expose it in logs
4. **Use minimal token scopes** - Only request necessary permissions
5. **Rotate tokens regularly** - Generate new tokens periodically

## Error Handling

The API handles various error scenarios:

- ❌ **Invalid URL format** → 400 Bad Request
- ❌ **Missing GitHub token** → 500 Internal Server Error
- ❌ **Repository not found** → 404 Not Found
- ❌ **Rate limit exceeded** → 403 Forbidden
- ❌ **Invalid token/permissions** → 403 Forbidden

## Rate Limits

GitHub API rate limits:

- **Authenticated requests:** 5,000 requests per hour
- **Unauthenticated requests:** 60 requests per hour (not applicable since we use tokens)

## Troubleshooting

### "GitHub token not found" error

Make sure you've:

1. Created a `.env` file in the project root
2. Added `GITHUB_TOKEN=your_token_here` to the file
3. Restarted the server after creating the `.env` file

### "Repository not found" error

Check that:

1. The repository URL is correct
2. Your token has access to the repository (especially for private repos)
3. The repository exists and is not deleted

### Rate limit exceeded

If you hit the rate limit:

1. Wait for the rate limit to reset (check headers in response)
2. Use a different token if available
3. Reduce the frequency of requests

## Development

### Running in development mode with auto-reload:

```bash
uvicorn main:app --reload
```

### Testing with different repositories:

```bash
# Small public repo (good for testing)
curl -X POST "http://localhost:8000/fetch-repo" \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/octocat/Hello-World"}'

# Your own repository
curl -X POST "http://localhost:8000/fetch-repo" \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/yourusername/yourrepo"}'
```

## Future Enhancements

Potential features for future versions:

- ⚙️ Support for specific branch/commit/tag selection
- 💾 Database integration for storing fetched data
- 🔍 Full-text search across repository contents
- 📊 Analytics and statistics on repository contents
- 🎨 Syntax highlighting for code files
- 📦 Export functionality (ZIP, JSON, etc.)
- 🔄 Webhook support for automatic updates
- 📈 Progress tracking for large repositories

## License

This project is open source and available for use and modification.

## Support

For issues, questions, or contributions, please refer to the project repository.

---

**Built with ❤️ using FastAPI and the GitHub REST API**
