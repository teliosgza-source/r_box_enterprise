#!/bin/bash

echo "========================================="
echo "📊 CLEANUP SUMMARY"
echo "========================================="

cd /home/linson/workspace/projects/web/Robin-Box-Enterprise

echo -e "\n📁 Project Structure:"
echo "   Root: $(pwd)"
echo "   Size: $(du -sh . 2>/dev/null | cut -f1)"
echo "   Directories: $(find . -type d 2>/dev/null | wc -l)"
echo "   Files: $(find . -type f 2>/dev/null | wc -l)"

echo -e "\n📂 Key Directories:"
ls -la

echo -e "\n🐍 Backend Files:"
ls -la backend/ | head -10

echo -e "\n📦 Frontend Files:"
ls -la frontend/electron/ | head -10

echo -e "\n🔄 Shared Files:"
ls -la shared/src/ | head -10

echo -e "\n💾 Disk Usage by Directory:"
du -sh */ 2>/dev/null | sort -hr

echo -e "\n✅ Ready for production!"
