# Quick Start Guide

## Setup (First Time Only)

1. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

2. **Set up your GitHub token:**

   ```bash
   cp .env.example .env
   # Edit .env and add your GitHub token
   ```

3. **Get a GitHub token:**
   - Visit: https://github.com/settings/tokens
   - Click "Generate new token (classic)"
   - Select scopes: `public_repo` (or `repo` for private repos)
   - Copy the token and paste it in `.env`

## Running the Server

### Option 1: Using the quick start script

```bash
./start.sh
```

### Option 2: Direct Python execution

```bash
python main.py
```

### Option 3: Using uvicorn with auto-reload (development)

```bash
uvicorn main:app --reload
```

## Testing the API

### Option 1: Using the test script

```bash
# Test with default repo (octocat/Hello-World)
python test_api.py

# Test with a specific repo
python test_api.py https://github.com/owner/repo
```

### Option 2: Using curl

```bash
curl -X POST "http://localhost:8000/fetch-repo" \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/octocat/Hello-World"}'
```

### Option 3: Using the interactive API docs

1. Open browser: http://localhost:8000/docs
2. Click on `POST /fetch-repo`
3. Click "Try it out"
4. Enter repo URL: `https://github.com/octocat/Hello-World`
5. Click "Execute"

## Example Repositories to Test

### Small repositories (good for testing):

- `https://github.com/octocat/Hello-World` - Classic test repo
- `https://github.com/octocat/Spoon-Knife` - Simple repo
- `https://github.com/github/gitignore` - Collection of .gitignore templates

### Medium repositories:

- `https://github.com/pallets/flask` - Flask web framework
- `https://github.com/psf/requests` - Requests library

## What to Expect

When you run the API:

1. **Server starts** and shows:

   ```
   Starting FastAPI server...
   API Documentation: http://localhost:8000/docs
   ```

2. **When you make a request**, the console shows:

   - 🚀 Starting fetch
   - ✅ URL parsed (owner/repo)
   - 📁 Directories being traversed
   - 📄 Files being fetched
   - ⏩ Binary files being skipped
   - 📋 Full file contents
   - 📊 Summary statistics

3. **API returns JSON** with:
   ```json
   {
     "owner": "octocat",
     "repo": "Hello-World",
     "total_files": 5,
     "files": [...]
   }
   ```

## Troubleshooting

### "GitHub token not found"

- Make sure `.env` file exists
- Verify `GITHUB_TOKEN=your_token` is set
- Restart the server

### "Repository not found"

- Check the URL format
- Verify repo exists on GitHub
- For private repos, ensure token has `repo` scope

### "Rate limit exceeded"

- You've made too many requests
- Wait an hour or use a different token
- Rate limit: 5,000 requests/hour with token

### Import errors

- Make sure you've installed dependencies:
  ```bash
  pip install -r requirements.txt
  ```

## Next Steps

After successfully fetching repository data, you can:

- Store the data in a database
- Analyze code patterns
- Generate documentation
- Search across files
- Create backups
- Build a code search engine

---

**Need help?** Check `API_README.md` for detailed documentation.
