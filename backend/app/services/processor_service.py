"""
Processor service with fixed imports and correct method calls
"""
import uuid
from datetime import datetime
from typing import Dict, Optional, List
import threading
from pathlib import Path
import sys
import os
import pandas as pd
import json
import time

# Add the shared directory to path properly
SHARED_PATH = Path(__file__).parent.parent.parent.parent / 'shared'
SRC_PATH = SHARED_PATH / 'src'

# Add both to Python path
if str(SHARED_PATH) not in sys.path:
    sys.path.insert(0, str(SHARED_PATH))
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

# Also set environment variable
os.environ['PYTHONPATH'] = str(SHARED_PATH) + ':' + str(SRC_PATH) + ':' + os.environ.get('PYTHONPATH', '')

print(f"📚 Python paths configured:")
print(f"   SHARED_PATH: {SHARED_PATH}")
print(f"   SRC_PATH: {SRC_PATH}")

class ProcessorService:
    def __init__(self):
        self.jobs: Dict[str, Dict] = {}
        self.processing_lock = threading.Lock()
    
    def create_job(self, request) -> str:
        job_id = str(uuid.uuid4())
        self.jobs[job_id] = {
            "id": job_id,
            "status": "created",
            "request": request.dict() if hasattr(request, 'dict') else request,
            "created_at": datetime.now(),
            "progress": 0,
            "message": "",
            "logs": [],
            "result": None
        }
        return job_id
    
    def add_log(self, job_id: str, message: str, level: str = "info"):
        if job_id in self.jobs:
            log_entry = {
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "message": message,
                "level": level
            }
            self.jobs[job_id]["logs"].append(log_entry)
            if len(self.jobs[job_id]["logs"]) > 200:
                self.jobs[job_id]["logs"] = self.jobs[job_id]["logs"][-200:]
    
    def save_output_files_fast(self, df: pd.DataFrame, output_dir: Path, country_name: str, data_type: str = "Map"):
        """Save output files using optimized methods"""
        start_time = time.time()
        
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            
            self.add_log(None, f"   📊 Preparing {len(df):,} records for export...", "info")
            self.add_log(None, f"   📁 Output type: {data_type}", "info")
            
            # 1. Unit.csv
            unit_columns = ['unitid', 'parentid', 'country_id', 'country', 'country_code',
                           'levelDescription', 'countryLevelId', 'levelKey', 'telioslevelKey', 
                           'countnextLevel', 'unit', 'parentlevelKey', 'teliosparentlevelKey']
            available_unit_cols = [col for col in unit_columns if col in df.columns]
            unit_df = df[available_unit_cols].copy()
            unit_csv = output_dir / "Unit.csv"
            unit_df.to_csv(unit_csv, index=False)
            self.add_log(None, f"   ✅ Unit: {len(unit_df):,} records", "success")
            
            # 2. PSQL_Geo.csv
            psql_columns = ['unitid', 'parentid', 'country_id', 'countryLevelId',
                           'levelKey', 'telioslevelKey', 'countnextLevel', 'unit', 'geometry']
            available_psql_cols = [col for col in psql_columns if col in df.columns]
            psql_df = df[available_psql_cols].copy()
            if not psql_df.empty:
                psql_df.columns = ['unitid', 'parent_id', 'country_id', 'levelid',
                                   'levelkey', 'tellevelkey', 'countnextlevel', 'unit', 'geometry']
                psql_csv = output_dir / "PSQL_Geo.csv"
                psql_df.to_csv(psql_csv, index=False)
                self.add_log(None, f"   ✅ PSQL_Geo: {len(psql_df):,} records", "success")
            
            # 3. teliosgeojson.csv - Database format
            telios_df = pd.DataFrame({
                'unitid': df['unitid'],
                'parent_id': df['parentid'],
                'country_id': df['country_id'],
                'levelid': df['countryLevelId'],
                'levelkey': df.get('levelKey', ''),
                'tellevelkey': df['telioslevelKey'],
                'countnextlevel': df['countnextLevel'],
                'unit': df['unit'],
                'geo_json': df.get('geometry', '{}')
            })
            telios_csv = output_dir / "teliosgeojson.csv"
            telios_df.to_csv(telios_csv, index=False)
            self.add_log(None, f"   ✅ teliosgeojson: {len(telios_df):,} records", "success")
            
            # 4. teliosgeojsondata.csv - Database format
            telios_data_df = pd.DataFrame({
                'teliosgeojson_id': df['unitid'],
                'geojson': df.get('geometry', '{}'),
                'levelkey': df.get('levelKey', '')
            })
            telios_data_csv = output_dir / "teliosgeojsondata.csv"
            telios_data_df.to_csv(telios_data_csv, index=False)
            self.add_log(None, f"   ✅ teliosgeojsondata: {len(telios_data_df):,} records", "success")
            
            # 5. GeoJSON.csv (legacy)
            geojson_df = pd.DataFrame({
                'teliosgeojson_id': df['unitid'],
                'geojson': df.get('geometry', '{}')
            })
            geojson_csv = output_dir / "GeoJSON.csv"
            geojson_df.to_csv(geojson_csv, index=False)
            self.add_log(None, f"   ✅ GeoJSON: {len(geojson_df):,} records", "success")
            
            # Generate report
            self._generate_fast_report(df, output_dir, country_name, data_type)
            
            elapsed = time.time() - start_time
            self.add_log(None, f"   ⚡ All files written in {elapsed:.2f} seconds", "success")
            
        except Exception as e:
            self.add_log(None, f"   ⚠️ Error saving files: {e}", "warning")
            import traceback
            traceback.print_exc()
    
    def _generate_fast_report(self, df: pd.DataFrame, output_dir: Path, country_name: str, data_type: str = "Map"):
        """Generate processing report"""
        report_file = output_dir / "processing_report.txt"
        
        with open(report_file, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write(f"📊 PROCESSING REPORT - {country_name}\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Data Type: {data_type}\n")
            f.write(f"Output Directory: {output_dir.absolute()}\n\n")
            
            f.write("📈 STATISTICS\n")
            f.write("-" * 40 + "\n")
            f.write(f"Total Records: {len(df):,}\n")
            f.write(f"UnitID Range: {df['unitid'].min()} - {df['unitid'].max()}\n\n")
            
            f.write("📋 LEVEL DISTRIBUTION\n")
            f.write("-" * 40 + "\n")
            for level in sorted(df['countryLevelId'].unique()):
                count = len(df[df['countryLevelId'] == level])
                desc = {0:'Country', 1:'State', 2:'District', 3:'Block', 4:'Village'}.get(level, f'Level {level}')
                percentage = (count / len(df)) * 100 if len(df) > 0 else 0
                f.write(f"  {desc:<10} (Level {level}): {count:>10,} records ({percentage:>5.1f}%)\n")
            
            f.write("\n" + "=" * 80 + "\n")
            f.write("✅ Processing completed successfully\n")
            f.write("=" * 80 + "\n")
    
    def _discover_states_from_path(self, country_path: str) -> List[str]:
        """Discover states from country path - returns list of state names"""
        if not country_path:
            return []
        path = Path(country_path)
        if not path.exists():
            return []
        
        states = []
        for item in path.iterdir():
            if item.is_dir() and (item / "Level1.geojson").exists():
                states.append(item.name)
        return sorted(states)
    
    def run_job(self, job_id: str):
        """Run processing job with correct method calls"""
        job = self.jobs[job_id]
        job["status"] = "running"
        job["started_at"] = datetime.now()
        
        try:
            from src.pipeline import GlobalGeoSpatialProcessor
            
            self.add_log(job_id, "🔍 Initializing processing pipeline...", "info")
            job["progress"] = 1
            
            data_root = job["request"].get("data_root")
            countries = job["request"].get("countries", [])
            base_output = Path(job["request"].get("output_base", "/home/linson/workspace/dev/data/processed/Telios"))
            
            self.add_log(job_id, f"📁 Data root: {data_root}", "info")
            self.add_log(job_id, f"🌍 Countries to process: {len(countries)}", "info")
            
            results = []
            total_countries = len(countries)
            
            for idx, country_config in enumerate(countries):
                country_start_time = time.time()
                country_name = country_config.get('name')
                
                # Handle both dict and object
                if hasattr(country_config, 'dict'):
                    country_config = country_config.dict()
                
                # Determine data type
                data_type = country_config.get('data_type', 'Map')
                
                # Build output path
                output_folder = base_output / f"Finale_{data_type}"
                country_output_path = output_folder / country_name.replace(' ', '_')
                
                self.add_log(job_id, f"\n{'='*60}", "info")
                self.add_log(job_id, f"🚀 Processing: {country_name}", "info")
                self.add_log(job_id, f"📋 Data Type: {data_type}", "info")
                self.add_log(job_id, f"💾 Output Path: {country_output_path}", "info")
                
                job["message"] = f"📂 Processing {country_name} ({data_type})..."
                job["progress"] = int((idx / total_countries) * 90) + 5
                
                # Get states - handle both list and integer
                states = country_config.get('states', [])
                
                # If states is an integer, discover them from path
                if isinstance(states, int):
                    if states > 0:
                        # We have a count but need actual names, discover from path
                        states = self._discover_states_from_path(country_config.get('base_path'))
                        self.add_log(job_id, f"🔍 Auto-discovered {len(states)} states from folder structure", "info")
                    else:
                        states = []
                elif isinstance(states, list):
                    # Already a list, use as is
                    pass
                else:
                    # Try to discover from path
                    states = self._discover_states_from_path(country_config.get('base_path'))
                
                # Ensure states is a list
                if not isinstance(states, list):
                    states = []
                
                # Prepare config
                full_config = {
                    'name': country_name,
                    'base_path': country_config.get('base_path'),
                    'states': states,
                    'max_level': country_config.get('max_level', 4),
                    'countryId': country_config.get('countryId', 0),
                    'data_type': data_type
                }
                
                self.add_log(job_id, f"📊 Found {len(full_config['states'])} states", "info")
                
                self.add_log(job_id, "📖 Step 1/3: Extracting GeoJSON data...", "info")
                global_processor = GlobalGeoSpatialProcessor(output_base=str(output_folder))
                result = global_processor.process_country(full_config)
                
                self.add_log(job_id, f"   ✅ Extracted {result.get('record_count', 0):,} records", "success")
                
                self.add_log(job_id, "🔄 Step 2/3: Transforming data...", "info")
                
                # Get the final dataframe from the processor
                # The processed data is stored in global_processor.all_country_data
                if global_processor.all_country_data:
                    final_df = global_processor.all_country_data[-1]  # Get the most recently processed country
                    
                    if final_df is not None and not final_df.empty:
                        self.add_log(job_id, "💾 Step 3/3: Saving output files (optimized)...", "info")
                        self.save_output_files_fast(final_df, country_output_path, country_name, data_type)
                        
                        # Try database storage
                        try:
                            from ..services.db_service import DatabaseService
                            db = DatabaseService()
                            db_result = db.append_processed_data(final_df, country_name)
                            if db_result.get('error'):
                                self.add_log(job_id, f"⚠️ Database error: {db_result['error']}", "warning")
                            else:
                                self.add_log(job_id, f"🗄️ Database: {db_result.get('stored', 0):,} new, {db_result.get('skipped', 0):,} skipped", "success")
                        except Exception as db_error:
                            self.add_log(job_id, f"⚠️ DB not available: {db_error}", "warning")
                    else:
                        self.add_log(job_id, f"⚠️ No data to save for {country_name}", "warning")
                else:
                    self.add_log(job_id, f"⚠️ No data processed for {country_name}", "warning")
                
                country_elapsed = time.time() - country_start_time
                self.add_log(job_id, f"⏱️ Completed in {country_elapsed:.1f}s", "success")
                
                result['data_type'] = data_type
                result['output_path'] = str(country_output_path)
                result['processing_time'] = country_elapsed
                results.append(result)
            
            # Final summary
            self.add_log(job_id, f"\n{'='*60}", "info")
            self.add_log(job_id, "🎉 PROCESSING COMPLETED!", "success")
            total_records = sum(r.get("record_count", 0) for r in results)
            self.add_log(job_id, f"📊 Total records: {total_records:,}", "info")
            
            job["status"] = "completed"
            job["progress"] = 100
            job["completed_at"] = datetime.now()
            job["message"] = "🎉 All processing completed successfully!"
            job["result"] = {
                "countries_processed": len(results),
                "total_records": total_records,
                "output_path": str(base_output),
                "results": results
            }
            
        except Exception as e:
            import traceback
            self.add_log(job_id, f"❌ ERROR: {str(e)}", "error")
            for line in traceback.format_exc().split('\n')[:10]:
                if line.strip():
                    self.add_log(job_id, f"   {line}", "error")
            
            job["status"] = "failed"
            job["error"] = str(e)
            job["completed_at"] = datetime.now()
            job["message"] = f"❌ Processing failed: {str(e)}"
    
    def get_job_status(self, job_id: str) -> Optional[Dict]:
        return self.jobs.get(job_id)
