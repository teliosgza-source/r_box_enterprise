#!/bin/bash

echo "========================================="
echo "📊 PROJECT CLEANUP ANALYSIS"
echo "========================================="

# Count files and directories
echo -e "\n📁 Current structure:"
echo "   Total directories: $(find . -type d 2>/dev/null | wc -l)"
echo "   Total files: $(find . -type f 2>/dev/null | wc -l)"

# Identify __pycache__ directories
echo -e "\n🐍 Python cache files (safe to remove):"
find . -type d -name "__pycache__" 2>/dev/null | wc -l
echo "   __pycache__ directories found"

# Identify .pyc files
echo -e "\n📄 Python bytecode files (safe to remove):"
find . -type f -name "*.pyc" 2>/dev/null | wc -l
echo "   .pyc files found"

# Identify node_modules (large but needed)
echo -e "\n📦 Node modules (can be regenerated with npm install):"
if [ -d "frontend/electron/node_modules" ]; then
    echo "   node_modules size: $(du -sh frontend/electron/node_modules 2>/dev/null | cut -f1)"
fi

# Identify backup files
echo -e "\n💾 Backup files (safe to remove):"
find . -type f -name "*.backup" 2>/dev/null | wc -l
echo "   .backup files found"

# Identify temporary files
echo -e "\n🔄 Temporary files (safe to remove):"
find . -type f -name "*.tmp" -o -name "*.temp" -o -name "*.log" 2>/dev/null | wc -l
echo "   temp files found"

# Identify empty directories
echo -e "\n📂 Empty directories (safe to remove):"
find . -type d -empty 2>/dev/null | wc -l
echo "   empty directories found"

# Identify test files
echo -e "\n🧪 Test files (optional to keep):"
find . -type f -name "test_*.py" -o -name "*_test.py" 2>/dev/null | wc -l
echo "   test files found"

echo -e "\n========================================="
