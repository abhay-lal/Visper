# Complete Setup & Run Guide - BlindVerse

## 🚀 Complete Setup Instructions

### Step 1: Create Virtual Environment

```bash
cd /Users/kshitij/Personal\ Project/tedai/BlindVerse
python3 -m venv venv
```

### Step 2: Activate Virtual Environment

```bash
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

Or install individually:

```bash
pip install fastapi==0.104.1
pip install uvicorn==0.24.0
pip install httpx==0.25.1
pip install python-dotenv==1.0.0
pip install requests==2.31.0
pip install vectara==0.1.10
```

### Step 4: Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit the .env file with your credentials
nano .env
```

Required environment variables in `.env`:

```env
# GitHub Token (required)
GITHUB_TOKEN=your_github_token_here

# Vectara Credentials (required for ingestion)
VECTARA_CUSTOMER_ID=your_vectara_customer_id
VECTARA_CORPUS_ID=your_vectara_corpus_id
VECTARA_API_KEY=your_vectara_api_key
```

**Get Credentials:**

- GitHub Token: https://github.com/settings/tokens
- Vectara: https://console.vectara.com/

### Step 5: Start the Server

```bash
python3 main.py
```

Or use uvicorn directly:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🧪 Testing the API

### Test 1: Root Endpoint (GET)

```bash
curl http://localhost:8000/
```

Expected response:

```json
{
  "message": "GitHub Repository Content Fetcher API",
  "status": "running",
  "endpoints": {...}
}
```

### Test 2: Fetch Repository (POST) - SentinelAI Project

```bash
curl -X POST http://localhost:8000/fetch-repo \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/KshitijD21/sentinelai"}'
```

**✅ Successfully Tested!** This command fetched 73 files from the SentinelAI repository.

### Test 3: Another Repository Example

```bash
curl -X POST http://localhost:8000/fetch-repo \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/octocat/Hello-World"}'
```

### Test 4: Pretty Print Response (with jq)

```bash
curl -X POST http://localhost:8000/fetch-repo \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/KshitijD21/sentinelai"}' | jq '.'
```

### Test 5: Save Response to File

```bash
curl -X POST http://localhost:8000/fetch-repo \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/KshitijD21/sentinelai"}' \
  -o response.json
```

---

## 📊 Interactive API Documentation

Once the server is running, access these URLs in your browser:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 🛠️ Troubleshooting Commands

### Check Python Version

```bash
python3 --version
```

### Check Installed Packages

```bash
pip list | grep -E "(fastapi|uvicorn|httpx|vectara)"
```

### Verify Virtual Environment is Active

```bash
which python
# Should show: /Users/kshitij/Personal Project/tedai/BlindVerse/venv/bin/python
```

### Check Server is Running

```bash
lsof -i :8000
```

### Kill Server if Needed

```bash
lsof -ti :8000 | xargs kill -9
```

### View Server Logs

The server outputs logs directly to the console. For background running:

```bash
python3 main.py > server.log 2>&1 &
tail -f server.log
```

---

## 📝 Quick Reference Commands

### Full Setup (One-Time)

```bash
# Navigate to project
cd /Users/kshitij/Personal\ Project/tedai/BlindVerse

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials
```

### Daily Use

```bash
# Navigate to project
cd /Users/kshitij/Personal\ Project/tedai/BlindVerse

# Activate virtual environment
source venv/bin/activate

# Start server
python3 main.py

# In another terminal, test with:
curl -X POST http://localhost:8000/fetch-repo \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/KshitijD21/sentinelai"}'
```

---

## 🔧 Alternative Installation (Using Script)

If you have the `install.sh` script:

```bash
chmod +x install.sh
./install.sh
source venv/bin/activate
```

---

## 📤 Expected API Response Structure

```json
{
  "owner": "KshitijD21",
  "repo": "sentinelai",
  "total_files": 25,
  "files": [
    {
      "path": "README.md",
      "name": "README.md",
      "type": "file",
      "size": 1234,
      "content": "# SentinelAI\n..."
    },
    ...
  ],
  "vectara_ingestion": {
    "total_files": 25,
    "ingested": 20,
    "skipped": 3,
    "failed": 2
  }
}
```

---

## 🔐 Security Notes

- Never commit `.env` file to Git
- Keep your GitHub token secure
- Rotate credentials regularly
- Use read-only tokens when possible

---

## 📦 Project Files Checklist

Required files:

- ✅ `main.py` - FastAPI application
- ✅ `github_client.py` - GitHub API client
- ✅ `vectara_client.py` - Vectara integration
- ✅ `utils.py` - Helper functions
- ✅ `requirements.txt` - Python dependencies
- ✅ `.env.example` - Environment template
- ✅ `Readme.md` - Documentation

Optional files:

- ✅ `install.sh` - Setup script
- ✅ `start.sh` - Run script
- ✅ `VECTARA_INTEGRATION.md` - Implementation details

---

## 🐛 Common Issues & Solutions

### Issue: `ModuleNotFoundError: No module named 'fastapi'`

**Solution:**

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Issue: `GITHUB_TOKEN not found`

**Solution:**

```bash
# Make sure .env file exists and contains GITHUB_TOKEN
cat .env | grep GITHUB_TOKEN
```

### Issue: Port 8000 already in use

**Solution:**

```bash
# Kill existing process
lsof -ti :8000 | xargs kill -9

# Or use different port
uvicorn main:app --port 8001
```

### Issue: Vectara ingestion fails

**Solution:**

- Check Vectara credentials in `.env`
- Verify corpus exists and is accessible
- Check API key permissions

---

## 📚 Additional Resources

- FastAPI Documentation: https://fastapi.tiangolo.com/
- GitHub API: https://docs.github.com/en/rest
- Vectara Documentation: https://docs.vectara.com/
- Python dotenv: https://pypi.org/project/python-dotenv/

---

## 💡 Tips

1. **Use virtual environment**: Always activate venv before running
2. **Check logs**: Server prints detailed logs for debugging
3. **Test incrementally**: Test with small repos first
4. **Rate limits**: GitHub API has rate limits (5000/hour with token)
5. **File size**: Very large repos may take time to process

---

## 🎯 Quick Test Script

Save as `test_api.sh`:

```bash
#!/bin/bash

echo "Testing BlindVerse API..."
echo ""

# Test root endpoint
echo "1. Testing root endpoint..."
curl -s http://localhost:8000/ | jq '.status'
echo ""

# Test fetch-repo
echo "2. Fetching SentinelAI repository..."
curl -X POST http://localhost:8000/fetch-repo \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/KshitijD21/sentinelai"}' \
  -s | jq '.total_files, .vectara_ingestion'

echo ""
echo "Test complete!"
```

Make it executable:

```bash
chmod +x test_api.sh
./test_api.sh
```
