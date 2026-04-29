#!/usr/bin/env python3
"""
Entry point for the backend server
"""
import sys
import os
from pathlib import Path

# Add paths for imports
backend_dir = Path(__file__).parent
shared_dir = backend_dir.parent / 'shared'

# Add to Python path
sys.path.insert(0, str(shared_dir))
sys.path.insert(0, str(backend_dir))

# Also set environment variable
os.environ['PYTHONPATH'] = str(shared_dir) + ':' + os.environ.get('PYTHONPATH', '')

print(f"Starting Telios GeoProcessor Backend...")
print(f"Working directory: {backend_dir}")
print(f"Shared directory: {shared_dir}")
print(f"Python path includes: {shared_dir}")

# Import and run the app
try:
    from app.main import app
    import uvicorn
except Exception as e:
    print(f"Error importing app: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
