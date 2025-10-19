#!/bin/bash

# Installation script for BlindVerse with Vectara integration

echo "🚀 Setting up BlindVerse..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "✅ Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "✅ Installation complete!"
echo ""
echo "📝 Next steps:"
echo "1. Copy .env.example to .env: cp .env.example .env"
echo "2. Edit .env and add your credentials"
echo "3. Activate the virtual environment: source venv/bin/activate"
echo "4. Run the server: python main.py"
echo ""
