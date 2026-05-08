#!/usr/bin/env python3
"""
Dynamic entry point for the backend server
Supports environment variable configuration
"""

import sys
import os
from pathlib import Path

def setup_environment():
    """Dynamically setup Python environment"""
    backend_dir = Path(__file__).parent
    project_root = backend_dir.parent
    shared_dir = project_root / 'shared' / 'src'
    
    # Add paths
    paths_to_add = [str(shared_dir), str(project_root), str(backend_dir)]
    for path in paths_to_add:
        if path not in sys.path:
            sys.path.insert(0, path)
    
    # Set environment variable
    os.environ['PYTHONPATH'] = ':'.join(paths_to_add) + ':' + os.environ.get('PYTHONPATH', '')
    
    # Load .env file if exists
    env_file = project_root / '.env'
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    os.environ[key] = value
    
    return project_root, shared_dir

if __name__ == "__main__":
    project_root, shared_dir = setup_environment()
    
    print(f"🚀 Starting Telios GeoProcessor Backend...")
    print(f"📁 Project root: {project_root}")
    print(f"📁 Shared directory: {shared_dir}")
    print(f"🌍 Environment: {os.getenv('TELIOS_ENV', 'staging')}")
    
    try:
        from app.main import app
        import uvicorn
    except Exception as e:
        print(f"❌ Error importing app: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    port = int(os.getenv('TELIOS_PORT', '8000'))
    host = os.getenv('TELIOS_HOST', '0.0.0.0')
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=os.getenv('TELIOS_LOG_LEVEL', 'info')
    )
