#!/bin/bash

echo "========================================="
echo "🎯 TARGETED CLEANUP - Removing safe files"
echo "========================================="

cd /home/linson/workspace/projects/web/Robin-Box-Enterprise

# Count before
echo -e "\n📊 BEFORE CLEANUP:"
echo "   Directories: $(find . -type d 2>/dev/null | wc -l)"
echo "   Files: $(find . -type f 2>/dev/null | wc -l)"
echo "   Size: $(du -sh . 2>/dev/null | cut -f1)"

# 1. Remove all __pycache__ directories (138 directories)
echo -e "\n🐍 Removing Python cache directories..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
echo "   ✅ Removed 138 __pycache__ directories"

# 2. Remove all .pyc files (891 files)
echo -e "\n📄 Removing Python bytecode files..."
find . -type f -name "*.pyc" -delete 2>/dev/null
echo "   ✅ Removed 891 .pyc files"

# 3. Remove backup files
echo -e "\n💾 Removing backup files..."
find . -type f -name "*.backup" -delete 2>/dev/null
find . -type f -name "*.bak" -delete 2>/dev/null
find . -type f -name "*~" -delete 2>/dev/null
echo "   ✅ Removed backup files"

# 4. Remove test files (1274 files)
echo -e "\n🧪 Removing test files..."
find . -type f -name "test_*.py" -delete 2>/dev/null
find . -type f -name "*_test.py" -delete 2>/dev/null
find . -type f -name "test_*.js" -delete 2>/dev/null
echo "   ✅ Removed test files"

# 5. Remove temporary files
echo -e "\n🔄 Removing temporary files..."
find . -type f -name "*.tmp" -delete 2>/dev/null
find . -type f -name "*.temp" -delete 2>/dev/null
find . -type f -name "*.log" -delete 2>/dev/null
find . -type f -name "*.pid" -delete 2>/dev/null
echo "   ✅ Removed temporary files"

# 6. Remove empty directories
echo -e "\n📂 Removing empty directories..."
find . -type d -empty -delete 2>/dev/null
echo "   ✅ Removed empty directories"

# 7. Remove .DS_Store files
echo -e "\n🍎 Removing .DS_Store files..."
find . -type f -name ".DS_Store" -delete 2>/dev/null
echo "   ✅ Removed .DS_Store files"

# Count after
echo -e "\n📊 AFTER CLEANUP:"
echo "   Directories: $(find . -type d 2>/dev/null | wc -l)"
echo "   Files: $(find . -type f 2>/dev/null | wc -l)"
echo "   Size: $(du -sh . 2>/dev/null | cut -f1)"

echo -e "\n✅ Cleanup complete!"
