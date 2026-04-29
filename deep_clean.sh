#!/bin/bash

echo "⚠️  DEEP CLEAN - This will remove:"
echo "   - Virtual environment (backend/venv) - can regenerate"
echo "   - Node modules (frontend/electron/node_modules) - can regenerate"
echo "   - All Python cache files"
echo "   - All backup files"
echo "   - All test files"
echo "   - Empty directories"
echo ""
echo "Estimated space to free: ~500MB+"
echo ""

read -p "Continue? (y/n): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Deep clean cancelled"
    exit 1
fi

cd /home/linson/workspace/projects/web/Robin-Box-Enterprise

# Count before
echo -e "\n📊 BEFORE DEEP CLEAN:"
echo "   Directories: $(find . -type d 2>/dev/null | wc -l)"
echo "   Files: $(find . -type f 2>/dev/null | wc -l)"
echo "   Size: $(du -sh . 2>/dev/null | cut -f1)"

# Remove venv
echo -e "\n🐍 Removing virtual environment..."
rm -rf backend/venv
echo "   ✅ Virtual environment removed"

# Remove node_modules
echo -e "\n📦 Removing node modules..."
rm -rf frontend/electron/node_modules
echo "   ✅ Node modules removed"

# Remove Python cache
echo -e "\n🐍 Removing Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null
echo "   ✅ Python cache removed"

# Remove backup and test files
echo -e "\n🧹 Removing backup and test files..."
find . -type f -name "*.backup" -delete 2>/dev/null
find . -type f -name "*.bak" -delete 2>/dev/null
find . -type f -name "test_*.py" -delete 2>/dev/null
find . -type f -name "*_test.py" -delete 2>/dev/null
find . -type f -name "test_*.js" -delete 2>/dev/null
echo "   ✅ Backup and test files removed"

# Remove temporary files
echo -e "\n🔄 Removing temporary files..."
find . -type f -name "*.tmp" -delete 2>/dev/null
find . -type f -name "*.temp" -delete 2>/dev/null
find . -type f -name "*.log" -delete 2>/dev/null
echo "   ✅ Temporary files removed"

# Remove empty directories
echo -e "\n📂 Removing empty directories..."
find . -type d -empty -delete 2>/dev/null
echo "   ✅ Empty directories removed"

# Remove .DS_Store
find . -type f -name ".DS_Store" -delete 2>/dev/null

# Count after
echo -e "\n📊 AFTER DEEP CLEAN:"
echo "   Directories: $(find . -type d 2>/dev/null | wc -l)"
echo "   Files: $(find . -type f 2>/dev/null | wc -l)"
echo "   Size: $(du -sh . 2>/dev/null | cut -f1)"

echo -e "\n✅ Deep clean complete!"
echo ""
echo "📝 To rebuild the project:"
echo "   1. Backend: cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
echo "   2. Frontend: cd frontend/electron && npm install"
echo "   3. Start: uvicorn app.main:app --reload (backend) && npm start (frontend)"
echo ""
