# Quick Reference: Search Endpoint

## 🚀 Quick Start

```bash
# Start server
source venv/bin/activate
python main.py

# Simple search
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "your search query here"}'
```

## 📋 Request Format

```json
{
  "query": "explain me search functionality", // Required
  "limit": 5 // Optional (default: 5, max: 20)
}
```

## 📤 Response Format

```json
{
  "query": "explain me search functionality", // ← YOUR INPUT
  "summary": "AI-generated answer with citations...", // ← AI SUMMARY
  "sources": [
    // ← RELEVANT FILES
    {
      "file_path": "src/components/SearchBar.tsx",
      "file_name": "SearchBar.tsx",
      "file_type": "tsx",
      "repo": "KshitijD21/job-portal-ui",
      "owner": "KshitijD21",
      "source_url": "https://github.com/...",
      "relevance_score": 0.0791,
      "snippet": "First 200 chars of content..."
    }
  ],
  "total_results": 5, // ← COUNT
  "query_time_ms": 1845, // ← SPEED
  "filters_applied": { "limit": 5 } // ← FILTERS
}
```

## 🎯 What You Get

### 1. Your Original Query

```json
"query": "explain me search functionality"
```

→ Always echoed back so you know what was searched

### 2. AI Summary

```json
"summary": "The search functionality includes..."
```

→ RAG-powered answer with citations [1], [2], etc.

### 3. Source Files

```json
"sources": [...]
```

→ Each source has:

- Full file path
- File name and type
- Repository (owner/repo)
- GitHub URL
- Relevance score (0-1)
- Content snippet (200 chars)

### 4. Metadata

```json
"total_results": 5,
"query_time_ms": 1845,
"filters_applied": {...}
```

→ Result count, timing, and applied filters

## 💡 Examples

### Example 1: Code Search

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "authentication code", "limit": 5}'
```

### Example 2: Component Search

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "React search components", "limit": 3}'
```

### Example 3: Documentation Search

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "how to use the API", "limit": 10}'
```

## 🔑 Key Points

✅ **Query is included**: Response contains your original query
✅ **AI summaries**: Get direct answers via RAG
✅ **Clean JSON**: Easy to parse and use
✅ **Rich metadata**: Complete file information
✅ **Fast**: ~2-6 seconds including AI generation
✅ **Relevance scores**: Know which results are most relevant

## 📖 Full Documentation

- **SEARCH_API_DOCS.md** - Complete API reference
- **SEARCH_IMPLEMENTATION_SUMMARY.md** - Implementation details
- **http://localhost:8000/docs** - Interactive Swagger UI
- **http://localhost:8000/redoc** - Alternative API docs

## 🐛 Troubleshooting

**Server not starting?**

```bash
# Check if port 8000 is in use
lsof -ti:8000

# Kill existing process
lsof -ti:8000 | xargs kill -9

# Restart server
source venv/bin/activate
python main.py
```

**Search not working?**

1. Check VECTARA_API_KEY is set in .env
2. Check server logs for errors
3. Verify corpus "blindverse" exists
4. Try a simpler query

**No results?**

- Try different search terms
- Check if data is ingested (use /fetch-repo first)
- Increase limit parameter

## 🎓 Integration

### Python

```python
import requests

def search_code(query, limit=5):
    response = requests.post(
        "http://localhost:8000/search",
        json={"query": query, "limit": limit}
    )
    return response.json()

# Use it
results = search_code("authentication code")
print(f"Query: {results['query']}")
print(f"Summary: {results['summary']}")
for source in results['sources']:
    print(f"- {source['file_path']} (score: {source['relevance_score']})")
```

### JavaScript

```javascript
async function searchCode(query, limit = 5) {
  const response = await fetch("http://localhost:8000/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, limit }),
  });
  return await response.json();
}

// Use it
const results = await searchCode("authentication code");
console.log("Query:", results.query);
console.log("Summary:", results.summary);
results.sources.forEach((s) =>
  console.log(`- ${s.file_path} (score: ${s.relevance_score})`)
);
```

## 📊 Response Analysis

### Understanding Relevance Scores

- **> 0.1**: Highly relevant
- **0.01 - 0.1**: Moderately relevant
- **< 0.01**: Tangentially related

### Understanding Citations

The AI summary includes citations like [1], [2]:

- [1] = First source in the sources array
- [2] = Second source in the sources array
- And so on...

### Query Time

- Typical: 1.8 - 6.5 seconds
- Includes: Network + Search + AI generation
- Larger limits may be slower

---

**That's it! You're ready to search! 🎉**
