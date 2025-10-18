#!/bin/bash

# Test the specific repository
echo "🧪 Testing GitHub Repository: KshitijD21/sentinelai"
echo "=" 60

echo ""
echo "📡 Sending POST request..."
echo ""

curl -X POST "http://localhost:8000/fetch-repo" \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/KshitijD21/sentinelai"}' \
  -w "\n\n📊 HTTP Status: %{http_code}\n" \
  | python3 -m json.tool

echo ""
echo "✅ Request completed!"
echo ""
echo "💡 Check the server console for detailed logs showing:"
echo "   - Files being fetched"
echo "   - Directories being traversed"
echo "   - Any errors or issues"
echo ""
echo "🔍 If you see 0 files, check:"
echo "   1. Is the repository private? (Token needs 'repo' scope)"
echo "   2. Does the repository exist?"
echo "   3. Check server logs for error messages"
