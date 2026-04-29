# 🗺️ Telios GeoProcessor

Enterprise geospatial data processing system for administrative boundaries (Country → State → District → Block → Village).

## 🚀 Quick Start

### Prerequisites
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.10 python3-pip python3-venv postgresql postgresql-contrib postgis nodejs npm

# Verify installations
python3 --version  # 3.10+
node --version     # 16+
psql --version     # 14+

# ===============================================
# 1. Clone & Setup Backend
cd /home/linson/workspace/projects/web/Robin-Box-Enterprise/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install fastapi uvicorn[standard] sqlalchemy psycopg2-binary pandas geopandas shapely pydantic pydantic-settings python-multipart pyyaml numpy

# Configure environment
cat > .env << 'EOF'
ACTIVE_ENV=staging
DEBUG=true
STAGING_DB_HOST=localhost
STAGING_DB_PORT=5432
STAGING_DB_NAME=telios_geo_staging
STAGING_DB_USER=telios_app
STAGING_DB_PASSWORD=staging_password
DATA_ROOT=/home/linson/workspace/dev/data/raw/Telios
PROCESSED_PATH=/home/linson/workspace/dev/data/processed/Telios
UPLOAD_PATH=/home/linson/workspace/dev/data/uploads
EOF

# ================================================
# 2. Setup Database (Optional)
# Create PostgreSQL database
sudo -u postgres psql << 'EOF'
CREATE DATABASE telios_geo_staging;
CREATE USER telios_app WITH PASSWORD 'staging_password';
GRANT ALL PRIVILEGES ON DATABASE telios_geo_staging TO telios_app;
\c telios_geo_staging
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Create tables
CREATE TABLE teliosgeojson (
    id BIGSERIAL PRIMARY KEY,
    unitid BIGINT UNIQUE NOT NULL,
    parent_id BIGINT,
    country_id INTEGER,
    levelid INTEGER,
    levelkey VARCHAR(100),
    tellevelkey VARCHAR(200),
    countnextlevel INTEGER,
    unit VARCHAR(200),
    geo_json JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE teliosgeojsondata (
    id BIGSERIAL PRIMARY KEY,
    teliosgeojson_id BIGINT UNIQUE NOT NULL,
    geojson JSONB,
    levelkey VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

GRANT ALL ON ALL TABLES IN SCHEMA public TO telios_app;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO telios_app;
\q
EOF
# ===================================================

python3 start.py

npm start