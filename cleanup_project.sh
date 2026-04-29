#!/bin/bash

echo "========================================="
echo "🧹 PROJECT CLEANUP - Telios GeoProcessor"
echo "========================================="
echo ""
echo "⚠️  This script will remove:"
echo "   - Python cache files (__pycache__, *.pyc)"
echo "   - Backup files (*.backup)"
echo "   - Temporary files (*.tmp, *.temp, *.log)"
echo "   - Empty directories"
echo "   - Virtual environment (if you want to recreate it)"
echo "   - node_modules (optional, will be recreated with npm install)"
echo ""

read -p "Continue? (y/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Cleanup cancelled"
    exit 1
fi

cd /home/linson/workspace/projects/web/Robin-Box-Enterprise

echo -e "\n📊 BEFORE CLEANUP:"
echo "   Directories: $(find . -type d 2>/dev/null | wc -l)"
echo "   Files: $(find . -type f 2>/dev/null | wc -l)"

# 1. Remove Python cache files
echo -e "\n🐍 Removing Python cache files..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null
find . -type f -name "*.pyo" -delete 2>/dev/null
echo "   ✅ Python cache removed"

# 2. Remove backup files
echo -e "\n💾 Removing backup files..."
find . -type f -name "*.backup" -delete 2>/dev/null
find . -type f -name "*.bak" -delete 2>/dev/null
find . -type f -name "*~" -delete 2>/dev/null
echo "   ✅ Backup files removed"

# 3. Remove temporary files
echo -e "\n🔄 Removing temporary files..."
find . -type f -name "*.tmp" -delete 2>/dev/null
find . -type f -name "*.temp" -delete 2>/dev/null
find . -type f -name "*.log" -delete 2>/dev/null
find . -type f -name "*.pid" -delete 2>/dev/null
echo "   ✅ Temporary files removed"

# 4. Remove empty directories
echo -e "\n📂 Removing empty directories..."
find . -type d -empty -delete 2>/dev/null
echo "   ✅ Empty directories removed"

# 5. Optional: Remove node_modules (comment out if you want to keep)
echo -e "\n📦 Node modules (optional):"
read -p "Remove node_modules? (y/n) - will be reinstalled with npm install: " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -d "frontend/electron/node_modules" ]; then
        rm -rf frontend/electron/node_modules
        echo "   ✅ node_modules removed"
    fi
fi

# 6. Optional: Remove virtual environment
echo -e "\n🐍 Virtual environment (optional):"
read -p "Remove backend/venv? (y/n) - will be recreated: " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -d "backend/venv" ]; then
        rm -rf backend/venv
        echo "   ✅ Virtual environment removed"
    fi
fi

# 7. Remove test files (optional)
echo -e "\n🧪 Test files (optional):"
read -p "Remove test files? (y/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    find . -type f -name "test_*.py" -delete 2>/dev/null
    find . -type f -name "*_test.py" -delete 2>/dev/null
    echo "   ✅ Test files removed"
fi

# 8. Remove IDE files (optional)
echo -e "\n💻 IDE files (optional):"
read -p "Remove IDE files (.vscode, .idea)? (y/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf .vscode 2>/dev/null
    rm -rf .idea 2>/dev/null
    find . -type f -name ".DS_Store" -delete 2>/dev/null
    echo "   ✅ IDE files removed"
fi

echo -e "\n📊 AFTER CLEANUP:"
echo "   Directories: $(find . -type d 2>/dev/null | wc -l)"
echo "   Files: $(find . -type f 2>/dev/null | wc -l)"

echo -e "\n✅ Cleanup completed!"
echo ""
echo "📝 Next steps:"
echo "   1. Recreate virtual environment: cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
echo "   2. Reinstall node modules: cd frontend/electron && npm install"
echo "   3. Start backend: cd backend && uvicorn app.main:app --reload"
echo "   4. Start frontend: cd frontend/electron && npm start"
echo ""
