from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class CountryConfig(BaseModel):
    name: str
    base_path: Optional[str] = None
    continent: Optional[str] = None
    data_type: Optional[str] = None  # "Map" or "Mapless"
    states: int = 0
    max_level: int = 4
    countryId: Optional[int] = None

class ProcessingRequest(BaseModel):
    data_root: str
    output_base: str = "/home/linson/workspace/dev/data/processed/Telios"
    countries: List[CountryConfig]

class ProcessingStatus(BaseModel):
    id: str
    status: str
    progress: int
    message: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

class CountryInfo(BaseModel):
    country: str
    country_code: str
    record_count: int
    min_id: int
    max_id: int

class ValidationResult(BaseModel):
    country: str
    orphaned_records: int
    hierarchy_issues: int
    duplicate_keys: int
    valid: bool
    error: Optional[str] = None

class ScanResult(BaseModel):
    countries: List[CountryConfig]
    summary: Dict[str, Any]
