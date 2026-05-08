#!/bin/bash
# Dynamic setup script for Telios GeoProcessor

set -e

echo "🚀 Setting up Telios GeoProcessor..."

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating required directories..."
mkdir -p config
mkdir -p logs
mkdir -p temp

# Copy .env template if .env doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.template .env
    echo "⚠️  Please edit .env file with your configuration"
fi

# Make start script executable
chmod +x backend/start.py

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env file with your configuration"
echo "  2. Run: python backend/start.py"
echo "  3. Or use: ./backend/start.py"
