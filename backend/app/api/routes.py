from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from typing import List, Optional, Dict, Any
import os
import shutil
from pathlib import Path

from ..services.processor_service import ProcessorService
from ..services.db_service import DatabaseService
from ..models.schema import ProcessingRequest, CountryConfig

router = APIRouter()
processor_service = ProcessorService()
db_service = DatabaseService()

def find_countries_in_path(base_path: Path, data_type: str) -> List[Dict]:
    """Recursively find countries by looking for Level0.geojson"""
    countries = []
    
    # Walk through all directories looking for Level0.geojson
    for root, dirs, files in os.walk(base_path):
        root_path = Path(root)
        
        # Check if this directory contains Level0.geojson
        if "Level0.geojson" in files:
            # This is a country directory
            country_name = root_path.name
            
            # Determine continent (parent directory name)
            continent = root_path.parent.name if root_path.parent != base_path else "Unknown"
            
            # Discover states in this country
            states = []
            max_level = 1
            
            for item in root_path.iterdir():
                if item.is_dir() and (item / "Level1.geojson").exists():
                    states.append(item.name)
                    
                    # Check max level for this state
                    for level in range(2, 5):
                        if (item / f"Level{level}").exists():
                            max_level = max(max_level, level)
            
            countries.append({
                "name": country_name,
                "states": len(states),
                "max_level": max_level,
                "base_path": str(root_path),
                "has_geometries": False,  # Will be set based on data_type
                "data_type": data_type,
                "continent": continent,
                "countryId": 0
            })
            
            # Don't descend further into this country directory
            dirs[:] = []
    
    return countries

def detect_data_type(country_path: Path, folder_name: str) -> str:
    """Detect if data is Map or Mapless based on folder name"""
    # First, check folder name
    if folder_name.lower() == 'map':
        return 'Map'
    elif folder_name.lower() == 'mapless':
        return 'Mapless'
    return 'Map'  # Default

@router.post("/process")
async def process_data(
    background_tasks: BackgroundTasks,
    request: Dict[str, Any]
):
    """Start processing job with flexible input format"""
    try:
        if isinstance(request, dict):
            data_root = request.get("data_root")
            output_base = request.get("output_base", "/home/linson/workspace/dev/data/processed/Telios")
            countries_raw = request.get("countries", [])
            
            countries = []
            for c in countries_raw:
                country_config = CountryConfig(
                    name=c.get("name", ""),
                    base_path=c.get("base_path", ""),
                    continent=c.get("continent"),
                    data_type=c.get("data_type", "Map"),
                    states=c.get("states", 0),
                    max_level=c.get("max_level", 4),
                    countryId=c.get("countryId", 0)
                )
                countries.append(country_config)
            
            if not countries:
                print(f"🔍 No countries specified, scanning {data_root}...")
                scan_result = await scan_directory({"path": data_root})
                countries = []
                for data_type in scan_result.get("data_types", []):
                    for continent in data_type.get("continents", []):
                        for country in continent.get("countries", []):
                            country_config = CountryConfig(
                                name=country.get("name"),
                                base_path=country.get("base_path"),
                                continent=continent.get("name"),
                                data_type=data_type.get("type"),
                                states=country.get("states", 0),
                                max_level=country.get("max_level", 4),
                                countryId=country.get("countryId", 0)
                            )
                            countries.append(country_config)
                print(f"✅ Auto-discovered {len(countries)} countries")
            
            proc_request = ProcessingRequest(
                data_root=data_root,
                output_base=output_base,
                countries=countries
            )
        else:
            proc_request = request
        
        job_id = processor_service.create_job(proc_request)
        background_tasks.add_task(processor_service.run_job, job_id)
        return {"job_id": job_id, "status": "started"}
        
    except Exception as e:
        print(f"Error creating processing job: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/process/{job_id}/status")
async def get_job_status(job_id: str):
    """Get processing job status"""
    status = processor_service.get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    return status

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload raw data file"""
    upload_dir = Path("/home/linson/workspace/dev/data/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = upload_dir / file.filename
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return {"filename": file.filename, "path": str(file_path)}

@router.get("/countries")
async def get_countries():
    """Get list of processed countries"""
    countries = db_service.get_countries()
    return countries

@router.get("/export/{country_name}")
async def export_country_data(country_name: str, format: str = "csv"):
    """Export processed data for a country"""
    file_path = db_service.export_country_data(country_name, format)
    return FileResponse(
        file_path,
        media_type='application/octet-stream',
        filename=f"{country_name}_export.{format}"
    )

@router.get("/validate/{country_name}")
async def validate_country_data(country_name: str):
    """Run validation on country data"""
    results = db_service.validate_country_data(country_name)
    return results

@router.post("/scan")
async def scan_directory(data: dict):
    """Scan directory for countries - finds Map and Mapless folders"""
    path = data.get("path")
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=400, detail="Invalid path")
    
    root_path = Path(path)
    result = {
        "data_types": [],
        "total_countries": 0,
        "total_continents": 0
    }
    
    print(f"📁 Scanning path: {path}")
    
    # Look for Map and Mapless folders
    for folder in root_path.iterdir():
        if not folder.is_dir():
            continue
            
        folder_name = folder.name
        data_type = None
        
        # Check if folder is Map or Mapless
        if folder_name.lower() == 'map':
            data_type = 'Map'
        elif folder_name.lower() == 'mapless':
            data_type = 'Mapless'
        else:
            # Skip folders that aren't Map or Mapless
            continue
        
        print(f"   📂 Found {data_type} folder: {folder_name}")
        
        # Scan this data type folder for countries
        data_type_data = {
            "name": folder_name,
            "type": data_type,
            "continents": {},
            "country_count": 0
        }
        
        # Find all countries in this folder
        countries_found = find_countries_in_path(folder, data_type)
        
        # Group countries by continent
        for country in countries_found:
            continent = country["continent"]
            if continent not in data_type_data["continents"]:
                data_type_data["continents"][continent] = {
                    "name": continent,
                    "countries": []
                }
            data_type_data["continents"][continent]["countries"].append(country)
            data_type_data["country_count"] += 1
        
        # Convert continents dict to list
        data_type_data["continents"] = list(data_type_data["continents"].values())
        
        if data_type_data["continents"]:
            result["data_types"].append(data_type_data)
            result["total_countries"] += data_type_data["country_count"]
            result["total_continents"] += len(data_type_data["continents"])
            
            print(f"   ✅ {data_type} folder: {data_type_data['country_count']} countries")
            for continent in data_type_data["continents"]:
                print(f"      🌍 {continent['name']}: {len(continent['countries'])} countries")
    
    print(f"\n✅ Scan complete: {result['total_countries']} total countries")
    
    # Log summary
    for dt in result["data_types"]:
        print(f"   {dt['type']}: {dt['country_count']} countries")
    
    return result
