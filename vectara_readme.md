# BlindVerse - GitHub Repository to Vectara Ingestion

FastAPI service that fetches GitHub repository contents and automatically ingests them into Vectara for semantic search.

## Features

- 📥 Fetch all files from any GitHub repository
- 🔍 Automatic ingestion into Vectara corpus for semantic search
- 🎯 Smart filtering (text/code files only, single README)
- 🔄 Retry logic with exponential backoff
- 📊 Detailed logging and progress tracking

## Quick Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Required variables:

```env
# GitHub Token (required)
GITHUB_TOKEN=your_github_token_here

# Vectara Credentials (required for ingestion)
VECTARA_CUSTOMER_ID=your_vectara_customer_id
VECTARA_CORPUS_ID=your_vectara_corpus_id
VECTARA_API_KEY=your_vectara_api_key
```

**Get GitHub Token:** https://github.com/settings/tokens
**Get Vectara Credentials:** https://console.vectara.com/

### 3. Run the Server

```bash
python main.py
```

Or use the start script:

```bash
./start.sh
```

## API Usage

### Endpoint: `POST /fetch-repo`

Fetches repository files and ingests them into Vectara.

**Request:**

```bash
curl -X POST http://localhost:8000/fetch-repo \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/owner/repo"}'
```

**Response:**

```json
{
  "owner": "owner",
  "repo": "repo",
  "total_files": 42,
  "files": [...],
  "vectara_ingestion": {
    "total_files": 42,
    "ingested": 35,
    "skipped": 5,
    "failed": 2
  }
}
```

### Interactive Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## How It Works

1. **Fetch:** Retrieves all files from the GitHub repository via GitHub API
2. **Filter:** Keeps only text/code files, excludes binaries/images
3. **Deduplicate:** Keeps only one README file (preferably root README.md)
4. **Ingest:** Uploads each file to Vectara with metadata:
   - Repository info (owner, repo)
   - File details (path, name, type, size)
   - Source URL (GitHub link)

## Supported File Types

Code, web, config, documentation, and query files:

- `.py`, `.js`, `.ts`, `.java`, `.cpp`, `.go`, `.rs`, etc.
- `.html`, `.css`, `.json`, `.yaml`, `.xml`
- `.md`, `.txt`, `.rst`
- `.sql`, `.graphql`

## Project Structure

```
├── main.py              # FastAPI application
├── github_client.py     # GitHub API client
├── vectara_client.py    # Vectara ingestion client
├── utils.py             # Helper functions
├── requirements.txt     # Python dependencies
└── .env.example         # Environment template
```

## Notes

- GitHub token only needs `public_repo` scope for public repositories
- Vectara ingestion is optional—service works without credentials (fetch only)
- Binary files, images, and archives are automatically skipped
- Failed ingestions are retried up to 3 times with exponential backoff
