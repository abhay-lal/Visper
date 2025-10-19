# Search API Documentation

## Overview

The `/search` endpoint allows you to search the Vectara corpus using natural language queries. It returns AI-generated summaries (RAG) and relevant source files with snippets.

## Endpoint Details

**URL:** `POST /search`

**Content-Type:** `application/json`

## Request Schema

```json
{
  "query": "string (required)",
  "repo": "string (optional)",
  "owner": "string (optional)",
  "limit": "integer (optional, default: 5, max: 20)"
}
```

### Parameters

| Parameter | Type    | Required | Description                             | Example                           |
| --------- | ------- | -------- | --------------------------------------- | --------------------------------- |
| `query`   | string  | Yes      | Natural language search query           | "explain me search functionality" |
| `repo`    | string  | No       | Filter by specific repository name      | "sentinelai"                      |
| `owner`   | string  | No       | Filter by repository owner              | "KshitijD21"                      |
| `limit`   | integer | No       | Number of results (default: 5, max: 20) | 5                                 |

**Note:** Metadata filtering (repo/owner) is currently not active as the corpus needs filterable attributes configured. Filters are accepted but not applied.

## Response Schema

```json
{
  "query": "string - Your original search query",
  "summary": "string - AI-generated summary answer from RAG",
  "sources": [
    {
      "file_path": "string - Full path of the file",
      "file_name": "string - Name of the file",
      "file_type": "string - File extension",
      "repo": "string - Repository (owner/repo format)",
      "owner": "string - Repository owner",
      "source_url": "string - GitHub URL to the file",
      "relevance_score": "float - Relevance score (0-1)",
      "snippet": "string - First 200 characters of content"
    }
  ],
  "total_results": "integer - Total number of results found",
  "query_time_ms": "integer - Query execution time in milliseconds",
  "filters_applied": {
    "repo": "string (if provided)",
    "owner": "string (if provided)",
    "limit": "integer"
  }
}
```

## Example Requests

### 1. Basic Search

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "explain me search functionality"
  }'
```

### 2. Search with Limit

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "authentication and authorization code",
    "limit": 10
  }'
```

### 3. Search with Filters (Currently not applied)

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "API endpoints",
    "owner": "KshitijD21",
    "repo": "sentinelai",
    "limit": 5
  }'
```

## Example Response

```json
{
  "query": "explain me search functionality",
  "summary": "The search functionality provided includes a search bar component that allows users to search by company, skill, or tag[1]. There is also a recruiter list component that filters candidates based on various criteria such as name, gender, experience, skills, field, and location. The list is sorted by total score and notice period[2].",
  "sources": [
    {
      "file_path": "src/components/dashboard/SearchBar.tsx",
      "file_name": "SearchBar.tsx",
      "file_type": "tsx",
      "repo": "KshitijD21/job-portal-ui",
      "owner": "KshitijD21",
      "source_url": "https://github.com/KshitijD21/job-portal-ui/blob/main/src/components/dashboard/SearchBar.tsx",
      "relevance_score": 0.0791,
      "snippet": "\"use client\";\nimport { Search } from \"lucide-react\";\nimport FilterButton from \"./FilterButton\";\n\nexport default function SearchBar({\n  onSearch,\n}: {\n  onSearch?: (q: string) => void;\n}) {\n  return (\n..."
    },
    {
      "file_path": "src/components/dashboard/RecruiterList.tsx",
      "file_name": "RecruiterList.tsx",
      "file_type": "tsx",
      "repo": "KshitijD21/job-portal-ui",
      "owner": "KshitijD21",
      "source_url": "https://github.com/KshitijD21/job-portal-ui/blob/main/src/components/dashboard/RecruiterList.tsx",
      "relevance_score": 0.0109,
      "snippet": "// components/RecruiterList.tsx\n\"use client\";\n\nimport { useEffect, useState } from \"react\";\nimport { Clock, MapPin } from \"lucide-react\";\n\ninterface Recruiter {\n  \"User Name\": string;\n  \"LinkedIn URL\"..."
    }
  ],
  "total_results": 2,
  "query_time_ms": 1845,
  "filters_applied": {
    "limit": 5
  }
}
```

## Response Fields Explained

### `query` (string)

The original search query you sent. This is echoed back so you can track what was searched.

### `summary` (string, nullable)

An AI-generated summary answer using Retrieval Augmented Generation (RAG). This provides a concise answer to your query based on the retrieved documents. It includes citations like [1], [2] that reference the sources array.

### `sources` (array)

An array of the most relevant files/documents found. Each source contains:

- **file_path**: Full path within the repository
- **file_name**: Just the filename
- **file_type**: File extension (e.g., tsx, ts, py, md)
- **repo**: Repository in "owner/repo" format
- **owner**: Repository owner username
- **source_url**: Direct GitHub URL to view the file
- **relevance_score**: Semantic relevance score (0.0 to 1.0, higher is more relevant)
- **snippet**: First 200 characters of the file content for quick preview

### `total_results` (integer)

Total number of matching results found.

### `query_time_ms` (integer)

Time taken to execute the query in milliseconds.

### `filters_applied` (object)

Shows which filters were applied to your search. Currently only `limit` is actively used.

## Error Responses

### 400 Bad Request

```json
{
  "detail": "Validation error message"
}
```

### 500 Internal Server Error

```json
{
  "detail": "Search failed: [error details]"
}
```

Common errors:

- Missing Vectara credentials (VECTARA_API_KEY not set)
- Vectara service unavailable
- Invalid corpus key

## Features

### ✅ Implemented

- Natural language semantic search
- AI-generated summary answers (RAG)
- Relevance scoring
- Configurable result limits (1-20)
- Response includes original query
- File metadata (path, name, type, repo, owner)
- Content snippets (200 chars)
- Query performance metrics
- Direct GitHub source URLs
- Comprehensive error handling
- Request/response logging

### ⚠️ Partially Implemented

- Metadata filtering (repo/owner): Accepted in request but not applied
  - Requires Vectara corpus filterable attributes configuration
  - See logs for filter warnings

### 📝 To Enable Filtering

1. Access your Vectara Console
2. Navigate to the "blindverse" corpus
3. Configure filterable attributes for:
   - `repo` (document-level metadata)
   - `owner` (document-level metadata)
4. Update `vectara_client.py` to uncomment filter logic (lines marked with TODO)

## Use Cases

1. **Code Search**: Find specific implementations or patterns

   ```
   "how to implement authentication with JWT"
   ```

2. **Documentation Search**: Find explanations or guides

   ```
   "explain me search functionality"
   ```

3. **API Discovery**: Find endpoints and usage

   ```
   "API endpoints for user management"
   ```

4. **Component Search**: Find UI components

   ```
   "React components for forms"
   ```

5. **Configuration Search**: Find config files
   ```
   "Docker configuration"
   ```

## Performance

- Typical query time: 1-6 seconds
- Includes network latency + Vectara processing + RAG generation
- Larger result limits may take slightly longer

## Best Practices

1. **Use natural language**: The search uses semantic understanding

   - Good: "how to authenticate users"
   - Also good: "authentication code"

2. **Be specific**: More specific queries yield better results

   - Better: "React search bar component"
   - Less specific: "search"

3. **Adjust limit**: Start with 5 results, increase if needed

   - More results = more context for RAG summary
   - But also slower response time

4. **Use the summary**: The RAG summary often answers your question directly

   - Sources provide supporting evidence
   - Citations [1], [2] link summary to sources

5. **Check relevance_score**: Higher scores indicate better matches
   - Scores > 0.1 are typically very relevant
   - Scores < 0.01 may be tangentially related

## Integration Example

### Python

```python
import requests

response = requests.post(
    "http://localhost:8000/search",
    json={
        "query": "explain authentication",
        "limit": 5
    }
)

data = response.json()
print(f"Query: {data['query']}")
print(f"Summary: {data['summary']}")
print(f"\nTop {len(data['sources'])} sources:")
for i, source in enumerate(data['sources'], 1):
    print(f"{i}. {source['file_path']} (score: {source['relevance_score']})")
```

### JavaScript

```javascript
const response = await fetch("http://localhost:8000/search", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    query: "explain authentication",
    limit: 5,
  }),
});

const data = await response.json();
console.log("Query:", data.query);
console.log("Summary:", data.summary);
console.log("Sources:", data.sources.length);
```

## API Documentation UI

Interactive API documentation is available at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Environment Variables

Required:

- `VECTARA_API_KEY`: Your Vectara API key
- `VECTARA_CORPUS_KEY`: Corpus key (default: "blindverse")

## Logging

All search requests are logged with:

- Query text
- Filters applied (if any)
- Results count
- Query execution time
- Any errors encountered

Check server logs for debugging and monitoring.
