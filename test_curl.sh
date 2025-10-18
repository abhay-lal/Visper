#!/bin/bash

# Test script for GitHub Repository Content Fetcher API
# This script shows the CORRECT way to call the API

echo "🧪 Testing GitHub Repository Content Fetcher API"
echo "=================================================="
echo ""

# Check if server is running
echo "📡 Checking if server is running..."
if ! curl -s http://localhost:8000/ > /dev/null 2>&1; then
    echo "❌ Server is not running!"
    echo "   Start it with: python main.py"
    echo "   Or: ./start.sh"
    exit 1
fi

echo "✅ Server is running!"
echo ""

# Test 1: Root endpoint (GET request - this should work)
echo "Test 1: GET / (Root endpoint)"
echo "Command: curl http://localhost:8000/"
echo "---"
curl -s http://localhost:8000/ | python3 -m json.tool
echo ""
echo ""

# Test 2: Incorrect method - GET on /fetch-repo (this will fail with 405)
echo "Test 2: ❌ WRONG - GET /fetch-repo (This will fail!)"
echo "Command: curl http://localhost:8000/fetch-repo"
echo "---"
curl -s http://localhost:8000/fetch-repo | python3 -m json.tool
echo ""
echo "⚠️  This fails because /fetch-repo requires POST, not GET!"
echo ""
echo ""

# Test 3: Correct method - POST with data
echo "Test 3: ✅ CORRECT - POST /fetch-repo with JSON data"
echo "Command: curl -X POST http://localhost:8000/fetch-repo \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"repo_url\": \"https://github.com/octocat/Hello-World\"}'"
echo "---"
echo "Sending request..."
echo ""

curl -X POST "http://localhost:8000/fetch-repo" \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/octocat/Hello-World"}' \
  | python3 -m json.tool

echo ""
echo "=================================================="
echo "✨ Test completed!"
echo ""
echo "💡 Key Points:"
echo "   - Use POST method for /fetch-repo (not GET)"
echo "   - Include 'Content-Type: application/json' header"
echo "   - Send JSON body with 'repo_url' field"
echo ""
echo "📚 For more examples, see:"
echo "   - API docs: http://localhost:8000/docs"
echo "   - ReDoc: http://localhost:8000/redoc"
echo "   - Run: python test_api.py"
