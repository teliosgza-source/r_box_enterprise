#!/bin/bash

echo "🚀 Setting up Telios GeoProcessor..."
echo "================================"

# Check Python version
python3 --version || { echo "Python 3 required"; exit 1; }

# Setup backend
echo "📦 Setting up backend..."
cd backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cd ..

# Setup frontend
echo "📦 Setting up frontend..."
cd frontend/electron
npm install
cd ../..

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data/{raw,processed/Telios,uploads}
mkdir -p logs

# Copy environment file if it doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ Created .env file from template"
fi

# Check PostgreSQL
echo "🛢️  Checking PostgreSQL..."
if command -v psql &> /dev/null; then
    echo "PostgreSQL found. To initialize database run:"
    echo "  sudo -u postgres psql -f scripts/init_db.sql"
else
    echo "PostgreSQL not found. You can use Docker:"
    echo "  docker-compose up -d postgres"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Start PostgreSQL:"
echo "   sudo -u postgres psql -f scripts/init_db.sql"
echo "   OR"
echo "   docker-compose up -d postgres"
echo ""
echo "2. Start backend:"
echo "   cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
echo ""
echo "3. Start frontend:"
echo "   cd frontend/electron && npm run dev"
echo ""
echo "4. Access the application at: http://localhost:3000"
echo ""
