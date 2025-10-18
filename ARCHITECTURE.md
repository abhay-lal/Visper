# Architecture & Flow Diagram

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Layer                             │
│  (curl, browser, Python script, test_api.py, examples.py)      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ HTTP POST /fetch-repo
                             │ {"repo_url": "..."}
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                       FastAPI Server                             │
│                         (main.py)                                │
│                                                                   │
│  ┌───────────────────────────────────────────────────────┐     │
│  │  POST /fetch-repo Endpoint                            │     │
│  │  - Validate request                                   │     │
│  │  - Parse GitHub URL                                   │     │
│  │  - Initialize GitHub client                           │     │
│  │  - Fetch all files                                    │     │
│  │  - Print to console                                   │     │
│  │  - Return JSON response                               │     │
│  └───────────────┬───────────────────────────────────────┘     │
│                  │                                               │
│                  │ calls                                         │
│                  ▼                                               │
│  ┌───────────────────────────────────────────────────────┐     │
│  │  URL Parser (utils.py)                                │     │
│  │  - parse_github_url()                                 │     │
│  │  - Extract owner & repo                               │     │
│  └───────────────────────────────────────────────────────┘     │
│                                                                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ uses
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   GitHub API Client                              │
│                   (github_client.py)                             │
│                                                                   │
│  ┌───────────────────────────────────────────────────────┐     │
│  │  GitHubAPIClient Class                                │     │
│  │  - __init__(token from .env)                          │     │
│  │  - get_repo_contents()                                │     │
│  │  - get_file_content()                                 │     │
│  │  - should_ignore_file()                               │     │
│  │  - fetch_all_files_recursive() ◄─────┐               │     │
│  └──────────────┬────────────────────────┼───────────────┘     │
│                 │                         │                      │
│                 │                    recursion                   │
│                 │                         │                      │
└─────────────────┼─────────────────────────┼──────────────────────┘
                  │                         │
                  │ HTTPS with Bearer Token │
                  ▼                         │
┌─────────────────────────────────────────────────────────────────┐
│                    GitHub REST API                               │
│                  (api.github.com)                                │
│                                                                   │
│  GET /repos/{owner}/{repo}/contents/{path}                      │
│  - List directory contents                                       │
│  - Get file metadata                                             │
│  - Return base64 encoded content                                 │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
1. Request Flow
   Client → POST /fetch-repo → FastAPI → parse_github_url()
                                        ↓
                                   GitHubAPIClient()
                                        ↓
                                   GitHub API

2. Response Flow
   GitHub API → base64 content → decode → GitHubAPIClient
                                            ↓
                                       all_files[]
                                            ↓
                                       Console Output
                                            ↓
                                       JSON Response → Client

3. Recursive Traversal
   fetch_all_files_recursive(path="")
        ↓
   get_repo_contents(path)
        ↓
   For each item:
        ├── File? → get_file_content() → decode → append to all_files
        └── Dir?  → fetch_all_files_recursive(item_path) → recurse
```

## Component Interaction

```
┌─────────────┐
│   main.py   │  Entry point, FastAPI app
└──────┬──────┘
       │
       ├─uses─┐
       │      │
       ▼      ▼
┌──────────┐ ┌─────────────────┐
│ utils.py │ │ github_client.py│
│          │ │                 │
│ parse_   │ │ GitHubAPIClient │
│ github_  │ │ - init with env │
│ url()    │ │ - recursive     │
│          │ │   traversal     │
│          │ │ - file fetching │
└──────────┘ └────────┬────────┘
                      │
                      │ reads
                      ▼
              ┌──────────────┐
              │  .env file   │
              │              │
              │ GITHUB_TOKEN │
              └──────────────┘
```

## File Dependencies

```
main.py
├── imports: fastapi, pydantic, dotenv
├── imports: utils (parse_github_url)
├── imports: github_client (GitHubAPIClient)
└── uses: .env (GITHUB_TOKEN)

github_client.py
├── imports: httpx, base64, os
├── uses: GITHUB_TOKEN from env
└── calls: api.github.com

utils.py
├── imports: re, fastapi
└── pure function (no external dependencies)

test_api.py
├── imports: requests
└── calls: http://localhost:8000

examples.py
├── imports: requests, httpx, asyncio
└── calls: http://localhost:8000
```

## Sequence Diagram

```
Client          FastAPI         Parser          GitHub Client      GitHub API
  │                │               │                   │                │
  │─POST /fetch───>│               │                   │                │
  │ repo           │               │                   │                │
  │                │               │                   │                │
  │                │─parse_url()──>│                   │                │
  │                │<──owner,repo──│                   │                │
  │                │               │                   │                │
  │                │──init()───────────────────────────>│                │
  │                │                                    │                │
  │                │──fetch_all_files()────────────────>│                │
  │                │                                    │                │
  │                │                                    │─GET contents──>│
  │                │                                    │<──items list───│
  │                │                                    │                │
  │                │                                    │─GET file1─────>│
  │                │                                    │<──base64───────│
  │                │                                    │                │
  │                │                                    │─GET file2─────>│
  │                │                                    │<──base64───────│
  │                │                                    │                │
  │                │<──all_files[]─────────────────────│                │
  │                │                                                     │
  │                │──print_file_info()                                 │
  │                │  (to console)                                      │
  │                │                                                     │
  │<──JSON─────────│                                                     │
  │  response      │                                                     │
  │                │                                                     │
```

## Security Flow

```
┌──────────────────────┐
│  Developer creates   │
│  GitHub Personal     │
│  Access Token        │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Token stored in     │
│  .env file           │
│  (gitignored!)       │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  python-dotenv loads │
│  into environment    │
│  variables           │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  GitHubAPIClient     │
│  reads from env      │
│  (never hardcoded)   │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Token sent in       │
│  Authorization       │
│  header to GitHub    │
└──────────────────────┘
```

## Error Handling Flow

```
Request
   ↓
Parse URL
   ├─ Invalid URL ────────→ 400 Bad Request
   └─ Valid URL
        ↓
Initialize Client
   ├─ No token ───────────→ 500 Internal Error
   └─ Has token
        ↓
Fetch from GitHub
   ├─ 404 ────────────────→ 404 Not Found
   ├─ 403 ────────────────→ 403 Rate Limit
   ├─ Other error ────────→ 500 Internal Error
   └─ Success
        ↓
Process files
   ├─ Binary file ────────→ Skip (logged)
   ├─ Decode error ───────→ "[Binary content]"
   └─ Success
        ↓
Return 200 OK
```

---

**This architecture ensures:**

- ✅ Clean separation of concerns
- ✅ Secure token handling
- ✅ Comprehensive error handling
- ✅ Recursive directory traversal
- ✅ Structured output
- ✅ No hardcoded secrets
