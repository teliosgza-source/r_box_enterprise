#!/bin/bash
# Cleanup script for Telios GeoProcessor

set -e

echo "🧹 Cleaning up Telios GeoProcessor..."

# Remove Python cache files
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true

# Remove temporary directories
rm -rf temp/
rm -rf logs/

# Remove virtual environment (optional)
read -p "Remove virtual environment? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf venv/
    echo "✅ Virtual environment removed"
fi

# Remove output directories (optional)
read -p "Remove processed data? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    DATA_ROOT=$(grep TELIOS_DATA_ROOT .env 2>/dev/null | cut -d '=' -f2 || echo "~/workspace/dev/data/processed/Telios")
    rm -rf $(eval echo $DATA_ROOT) 2>/dev/null || true
    echo "✅ Processed data removed"
fi

echo "✅ Cleanup complete!"
