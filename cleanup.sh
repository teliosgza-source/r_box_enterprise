#!/bin/bash

echo "🧹 Cleaning up Robin-Box-Enterprise project..."
echo "=============================================="
echo ""

# Change to project directory
cd ~/workspace/projects/web/Robin-Box-Enterprise

# 1. Remove backup files
echo "1. Removing backup files..."
find . -name "*.backup" -type f -delete
find . -name "*.pyc" -type f -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null

# 2. Remove duplicate electron folder at root (if it exists)
if [ -d "electron" ] && [ ! -L "electron" ]; then
    echo "2. Removing duplicate electron folder..."
    rm -rf electron
fi

# 3. Remove duplicate src folder at root (if it exists)
if [ -d "src" ] && [ ! -L "src" ]; then
    echo "3. Removing duplicate src folder..."
    rm -rf src
fi

# 4. Remove nested Telios_Yx folders
echo "4. Removing nested Telios_Yx folders..."
find . -type d -name "Telios_Yx" -exec rm -rf {} + 2>/dev/null

# 5. Remove test data if present
echo "5. Cleaning test data..."
rm -rf dumps/ 2>/dev/null
rm -rf backups/ 2>/dev/null

# 6. Remove any .tmp files
echo "6. Removing temporary files..."
find . -name "*.tmp" -type f -delete
find . -name "*.log" -type f -delete

# 7. Remove empty directories
echo "7. Removing empty directories..."
find . -type d -empty -delete 2>/dev/null

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "📁 Current project structure:"
ls -la

echo ""
echo "✨ Keep these essential directories:"
echo "   backend/    - FastAPI backend"
echo "   frontend/   - Electron frontend"
echo "   shared/     - Shared processing code"
echo "   config/     - Configuration files"
echo "   scripts/    - Utility scripts"
echo "   data/       - Data directories"
echo "   logs/       - Log files"
echo "   .env        - Environment variables"
