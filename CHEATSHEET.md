# 🚀 GitHub Repository Content Fetcher - Quick Reference

## Installation

```bash
pip install -r requirements.txt
cp .env.example .env
# Add your GITHUB_TOKEN to .env
```

## Start Server

```bash
./start.sh                    # Quick start
python main.py                # Direct
uvicorn main:app --reload     # Dev mode
```

## API Endpoint

```
POST http://localhost:8000/fetch-repo
Content-Type: application/json

{
  "repo_url": "https://github.com/owner/repo"
}
```

## Test Commands

### Using test script

```bash
python test_api.py
python test_api.py https://github.com/owner/repo
```

### Using curl

```bash
curl -X POST http://localhost:8000/fetch-repo \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/octocat/Hello-World"}'
```

### Using Python

```python
import requests
r = requests.post("http://localhost:8000/fetch-repo",
                  json={"repo_url": "https://github.com/octocat/Hello-World"})
print(r.json())
```

## URLs & Docs

- **API Docs:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **GitHub Token:** https://github.com/settings/tokens

## Response Format

```json
{
  "owner": "string",
  "repo": "string",
  "total_files": 0,
  "files": [
    {
      "path": "string",
      "name": "string",
      "type": "file",
      "size": 0,
      "content": "string"
    }
  ]
}
```

## Common Errors

| Error                | Cause              | Solution                             |
| -------------------- | ------------------ | ------------------------------------ |
| 500: Token not found | `.env` missing     | Create `.env` with `GITHUB_TOKEN`    |
| 400: Invalid URL     | Bad repo URL       | Use: `https://github.com/owner/repo` |
| 404: Not found       | Repo doesn't exist | Check repo URL                       |
| 403: Rate limit      | Too many requests  | Wait 1 hour                          |

## File Structure

```
main.py             # FastAPI app
github_client.py    # GitHub API client
utils.py            # URL parser
test_api.py         # Testing script
examples.py         # Usage examples
```

## Environment Variables

```bash
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## Supported URL Formats

- ✅ `https://github.com/owner/repo`
- ✅ `https://github.com/owner/repo.git`
- ✅ `github.com/owner/repo`
- ✅ `git@github.com:owner/repo.git`

## Binary Files (Auto-skipped)

Images: `.jpg`, `.png`, `.gif`, `.svg`
Archives: `.zip`, `.tar`, `.gz`
Binaries: `.exe`, `.dll`, `.so`
Media: `.mp4`, `.mp3`, `.avi`

## Example Test Repos

- `https://github.com/octocat/Hello-World` (small)
- `https://github.com/octocat/Spoon-Knife` (small)
- `https://github.com/pallets/flask` (medium)

---

**Docs:** See `API_README.md` for full documentation
