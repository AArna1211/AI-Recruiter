#!/bin/bash
# Talent Quest Installation Script

set -e

echo "🏰 Talent Quest - Installation Script"
echo "====================================="

# Check Python version
echo "🔍 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r backend/requirements.txt

# Create data directories
echo "📁 Creating data directories..."
mkdir -p data/raw data/processed data/embeddings data/outputs data/qdrant_storage
mkdir -p logs models

# Start Docker services
echo "🐳 Starting Docker services..."
docker-compose up -d

echo "✅ Installation complete!"
echo ""
echo "To start the backend:"
echo "  source venv/bin/activate"
echo "  cd backend"
echo "  uvicorn app.main:app --reload"
echo ""
echo "To access the API docs:"
echo "  http://localhost:8000/docs"
