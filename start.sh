#!/bin/bash

# Quick start script for the GitHub Repository Content Fetcher

echo "🚀 GitHub Repository Content Fetcher - Quick Start"
echo "=================================================="
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo ""
    echo "✅ .env file created!"
    echo "⚠️  IMPORTANT: Edit .env and add your GitHub token before continuing!"
    echo ""
    echo "To get a GitHub token:"
    echo "1. Go to https://github.com/settings/tokens"
    echo "2. Click 'Generate new token (classic)'"
    echo "3. Select 'public_repo' or 'repo' scope"
    echo "4. Copy the token and paste it in .env"
    echo ""
    read -p "Press Enter after you've added your token to .env..."
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created!"
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q -r requirements.txt
echo "✅ Dependencies installed!"

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Starting FastAPI server..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📚 API Documentation: http://localhost:8000/docs"
echo "📖 ReDoc: http://localhost:8000/redoc"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Run the application
python main.py
