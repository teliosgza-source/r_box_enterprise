from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # App
    APP_NAME: str = "Telios GeoProcessor"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Active environment
    ACTIVE_ENV: str = "staging"
    
    # Database settings
    STAGING_DB_HOST: str = "localhost"
    STAGING_DB_PORT: int = 5432
    STAGING_DB_NAME: str = "telios_geo_staging"
    STAGING_DB_USER: str = "telios_app"
    STAGING_DB_PASSWORD: str = "staging_password"
    
    PROD_DB_HOST: str = "localhost"
    PROD_DB_PORT: int = 5432
    PROD_DB_NAME: str = "telios_geo_production"
    PROD_DB_USER: str = "telios_app_prod"
    PROD_DB_PASSWORD: str = "prod_password"
    
    # Paths
    DATA_ROOT: str = "/home/linson/workspace/dev/data/raw/Telios"
    PROCESSED_PATH: str = "/home/linson/workspace/dev/data/processed/Telios"
    UPLOAD_PATH: str = "/home/linson/workspace/dev/data/uploads"
    
    # Processing
    MAX_WORKERS: int = 4
    CHUNK_SIZE: int = 1000
    
    @property
    def DATABASE_URL(self) -> str:
        if self.ACTIVE_ENV == "production":
            return f"postgresql://{self.PROD_DB_USER}:{self.PROD_DB_PASSWORD}@{self.PROD_DB_HOST}:{self.PROD_DB_PORT}/{self.PROD_DB_NAME}"
        else:
            return f"postgresql://{self.STAGING_DB_USER}:{self.STAGING_DB_PASSWORD}@{self.STAGING_DB_HOST}:{self.STAGING_DB_PORT}/{self.STAGING_DB_NAME}"
    
    class Config:
        env_file = ".env"

settings = Settings()
