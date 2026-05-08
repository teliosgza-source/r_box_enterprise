"""
Dynamic configuration with environment variable support
"""

import os
from pathlib import Path
from typing import Optional

class Settings:
    """Dynamic configuration manager"""
    
    def __init__(self):
        # Project paths - dynamic based on execution context
        self._project_root = Path(__file__).parent.parent.parent.parent
        
        # App settings
        self.APP_NAME: str = os.getenv("TELIOS_APP_NAME", "Telios GeoProcessor")
        self.APP_VERSION: str = os.getenv("TELIOS_VERSION", "2.0.0")
        self.DEBUG: bool = os.getenv("TELIOS_DEBUG", "false").lower() == "true"
        
        # Active environment
        self.ACTIVE_ENV: str = os.getenv("TELIOS_ENV", "staging")
        
        # Database settings - from environment or defaults
        self.STAGING_DB_HOST: str = os.getenv("TELIOS_STAGING_DB_HOST", "localhost")
        self.STAGING_DB_PORT: int = int(os.getenv("TELIOS_STAGING_DB_PORT", "5432"))
        self.STAGING_DB_NAME: str = os.getenv("TELIOS_STAGING_DB_NAME", "telios_geo_staging")
        self.STAGING_DB_USER: str = os.getenv("TELIOS_STAGING_DB_USER", "telios_app")
        self.STAGING_DB_PASSWORD: str = os.getenv("TELIOS_STAGING_DB_PASSWORD", "staging_password")
        
        self.PROD_DB_HOST: str = os.getenv("TELIOS_PROD_DB_HOST", "localhost")
        self.PROD_DB_PORT: int = int(os.getenv("TELIOS_PROD_DB_PORT", "5432"))
        self.PROD_DB_NAME: str = os.getenv("TELIOS_PROD_DB_NAME", "telios_geo_production")
        self.PROD_DB_USER: str = os.getenv("TELIOS_PROD_DB_USER", "telios_app_prod")
        self.PROD_DB_PASSWORD: str = os.getenv("TELIOS_PROD_DB_PASSWORD", "prod_password")
        
        # Dynamic data paths
        default_data_root = os.path.expanduser("~/workspace/dev/data/raw/Telios")
        default_processed = os.path.expanduser("~/workspace/dev/data/processed/Telios")
        default_upload = os.path.expanduser("~/workspace/dev/data/uploads")
        
        self.DATA_ROOT: str = os.getenv("TELIOS_DATA_ROOT", default_data_root)
        self.PROCESSED_PATH: str = os.getenv("TELIOS_PROCESSED_PATH", default_processed)
        self.UPLOAD_PATH: str = os.getenv("TELIOS_UPLOAD_PATH", default_upload)
        
        # Processing settings
        self.MAX_WORKERS: int = int(os.getenv("TELIOS_MAX_WORKERS", "4"))
        self.CHUNK_SIZE: int = int(os.getenv("TELIOS_CHUNK_SIZE", "1000"))
        
        # Country config path
        self.COUNTRY_CONFIG_PATH: str = os.getenv(
            "TELIOS_COUNTRY_CONFIG",
            str(self._project_root / "config" / "country_ids.yaml")
        )
    
    @property
    def DATABASE_URL(self) -> str:
        """Dynamic database URL based on active environment"""
        if self.ACTIVE_ENV == "production":
            return f"postgresql://{self.PROD_DB_USER}:{self.PROD_DB_PASSWORD}@{self.PROD_DB_HOST}:{self.PROD_DB_PORT}/{self.PROD_DB_NAME}"
        else:
            return f"postgresql://{self.STAGING_DB_USER}:{self.STAGING_DB_PASSWORD}@{self.STAGING_DB_HOST}:{self.STAGING_DB_PORT}/{self.STAGING_DB_NAME}"
    
    @property
    def PROJECT_ROOT(self) -> Path:
        """Get project root directory"""
        return self._project_root
    
    @property
    def SHARED_DIR(self) -> Path:
        """Get shared directory path"""
        return self._project_root / "shared" / "src"

settings = Settings()
