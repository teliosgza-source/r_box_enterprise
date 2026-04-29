"""
Database service with proper handling for Map and Mapless data
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError, OperationalError
import pandas as pd
from pathlib import Path
import json
from typing import List, Dict, Any
from datetime import datetime
import time

from ..core.config import settings

class DatabaseService:
    def __init__(self):
        try:
            self.sync_engine = create_engine(
                settings.DATABASE_URL, 
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                echo=False
            )
            self.SessionLocal = sessionmaker(bind=self.sync_engine)
            print("✅ Database service initialized")
        except Exception as e:
            print(f"⚠️ Database init error: {e}")
            self.sync_engine = None
            self.SessionLocal = None
    
    def append_processed_data(self, final_df: pd.DataFrame, country_name: str):
        """Append processed data with proper Map/Mapless handling"""
        if self.SessionLocal is None:
            print("   ⚠️ Database not available, skipping storage")
            return {"stored": 0, "skipped": 0, "data_stored": 0, "data_skipped": 0, "error": "DB not initialized"}
        
        session = self.SessionLocal()
        stored_count = 0
        skipped_count = 0
        data_stored = 0
        data_skipped = 0
        
        try:
            # Test connection
            session.execute(text("SELECT 1"))
            session.commit()
            
            batch_size = 500
            total_records = len(final_df)
            
            print(f"   📊 Storing {total_records:,} records to database...")
            
            # First, get the current max id to know what's new
            result = session.execute(text("SELECT COALESCE(MAX(id), 0) FROM teliosgeojson"))
            max_existing_id = result.scalar()
            
            # Process in batches
            for i in range(0, total_records, batch_size):
                batch = final_df.iloc[i:i+batch_size]
                batch_stored = 0
                
                for _, row in batch.iterrows():
                    try:
                        unitid = int(row.get('unitid', 0))
                        
                        # Check if record exists by unitid
                        check_sql = text("SELECT id FROM teliosgeojson WHERE unitid = :unitid LIMIT 1")
                        existing = session.execute(check_sql, {"unitid": unitid}).fetchone()
                        
                        if existing:
                            skipped_count += 1
                            # Still need to ensure teliosgeojsondata exists for Mapless
                            teliosgeojson_id = existing[0]
                            if self._ensure_geojsondata_exists(session, teliosgeojson_id, row):
                                data_stored += 1
                            else:
                                data_skipped += 1
                            continue
                        
                        # Prepare data for teliosgeojson
                        geometry = row.get('geometry', '{}')
                        if isinstance(geometry, str):
                            try:
                                geometry = json.loads(geometry) if geometry else {}
                            except:
                                geometry = {}
                        
                        # Get data type (Map or Mapless)
                        data_type = row.get('data_type', 'Map')
                        
                        # For Mapless, we still store empty geo_json
                        geo_json_value = geometry if geometry else {}
                        
                        # Insert into teliosgeojson
                        insert_sql = text("""
                            INSERT INTO teliosgeojson 
                            (unitid, parent_id, country_id, levelid, levelkey, 
                             tellevelkey, countnextlevel, unit, geo_json)
                            VALUES 
                            (:unitid, :parent_id, :country_id, :levelid, :levelkey,
                             :tellevelkey, :countnextlevel, :unit, :geo_json)
                            RETURNING id
                        """)
                        
                        result = session.execute(insert_sql, {
                            'unitid': unitid,
                            'parent_id': int(row.get('parentid', 0)),
                            'country_id': int(row.get('country_id', 0)),
                            'levelid': int(row.get('countryLevelId', 0)),
                            'levelkey': str(row.get('levelKey', ''))[:50],
                            'tellevelkey': str(row.get('telioslevelKey', ''))[:255],
                            'countnextlevel': int(row.get('countnextLevel', 0)),
                            'unit': str(row.get('unit', ''))[:255],
                            'geo_json': json.dumps(geo_json_value) if geo_json_value else '{}'
                        })
                        
                        teliosgeojson_id = result.fetchone()[0]
                        stored_count += 1
                        batch_stored += 1
                        
                        # Always create entry in teliosgeojsondata
                        # For Mapless, geojson can be empty
                        geojson_value = geometry if data_type == 'Map' else {}
                        
                        insert_data_sql = text("""
                            INSERT INTO teliosgeojsondata 
                            (teliosgeojson_id, geojson, levelkey)
                            VALUES 
                            (:teliosgeojson_id, :geojson, :levelkey)
                        """)
                        
                        session.execute(insert_data_sql, {
                            'teliosgeojson_id': teliosgeojson_id,
                            'geojson': json.dumps(geojson_value) if geojson_value else '{}',
                            'levelkey': str(row.get('levelKey', ''))[:50]
                        })
                        data_stored += 1
                        
                        if batch_stored % 100 == 0:
                            session.commit()
                            
                    except IntegrityError as e:
                        session.rollback()
                        skipped_count += 1
                        continue
                    except Exception as e:
                        session.rollback()
                        print(f"   ⚠️ Error for unit {row.get('unitid', 'unknown')}: {str(e)[:100]}")
                        skipped_count += 1
                        continue
                
                session.commit()
                print(f"   📦 Batch {i//batch_size + 1}: +{batch_stored} records (Total stored: {stored_count:,}, Skipped: {skipped_count:,})")
            
            print(f"✅ Stored {stored_count:,} new records in teliosgeojson")
            print(f"✅ Stored {data_stored:,} records in teliosgeojsondata (skipped {data_skipped:,})")
            
            return {
                "stored": stored_count,
                "skipped": skipped_count,
                "data_stored": data_stored,
                "data_skipped": data_skipped
            }
            
        except Exception as e:
            session.rollback()
            print(f"❌ Database error: {e}")
            import traceback
            traceback.print_exc()
            return {
                "stored": 0,
                "skipped": 0,
                "data_stored": 0,
                "data_skipped": 0,
                "error": str(e)
            }
        finally:
            session.close()
    
    def _ensure_geojsondata_exists(self, session, teliosgeojson_id: int, row: pd.Series) -> bool:
        """Ensure a record exists in teliosgeojsondata for the given ID"""
        try:
            # Check if exists
            check_sql = text("SELECT id FROM teliosgeojsondata WHERE teliosgeojson_id = :id LIMIT 1")
            existing = session.execute(check_sql, {"id": teliosgeojson_id}).fetchone()
            
            if existing:
                return True
            
            # Create if not exists
            data_type = row.get('data_type', 'Map')
            geometry = row.get('geometry', '{}')
            if isinstance(geometry, str):
                try:
                    geometry = json.loads(geometry) if geometry else {}
                except:
                    geometry = {}
            
            # For Mapless, geojson can be empty
            geojson_value = geometry if data_type == 'Map' else {}
            
            insert_sql = text("""
                INSERT INTO teliosgeojsondata 
                (teliosgeojson_id, geojson, levelkey)
                VALUES 
                (:teliosgeojson_id, :geojson, :levelkey)
            """)
            
            session.execute(insert_sql, {
                'teliosgeojson_id': teliosgeojson_id,
                'geojson': json.dumps(geojson_value) if geojson_value else '{}',
                'levelkey': str(row.get('levelKey', ''))[:50]
            })
            session.commit()
            return True
            
        except Exception as e:
            print(f"   ⚠️ Error ensuring geojsondata for ID {teliosgeojson_id}: {e}")
            return False
    
    def get_countries(self) -> list:
        """Get list of processed countries"""
        if self.SessionLocal is None:
            return []
        
        try:
            with self.SessionLocal() as session:
                result = session.execute(
                    text("""
                        SELECT 
                            unit as country_name,
                            country_id,
                            COUNT(*) as record_count,
                            MIN(unitid) as min_id,
                            MAX(unitid) as max_id
                        FROM teliosgeojson
                        WHERE levelid = 0
                        GROUP BY unit, country_id
                        ORDER BY unit
                    """)
                )
                countries = []
                for row in result:
                    countries.append({
                        "country": row[0],
                        "country_code": f"ID{row[1]}",
                        "record_count": row[2],
                        "min_id": row[3],
                        "max_id": row[4]
                    })
                return countries
        except Exception as e:
            print(f"⚠️ Could not query countries: {e}")
            return []
    
    def export_country_data(self, country_name: str, format: str) -> str:
        """Export country data"""
        if self.sync_engine is None:
            raise Exception("Database not available")
        
        query = text("""
            SELECT t.*, d.geojson
            FROM teliosgeojson t
            LEFT JOIN teliosgeojsondata d ON t.id = d.teliosgeojson_id
            WHERE t.unit = :country
            ORDER BY t.unitid
        """)
        
        try:
            df = pd.read_sql(query, self.sync_engine, params={"country": country_name})
            
            export_dir = Path("/tmp")
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            export_path = export_dir / f"{country_name}_export_{timestamp}.{format}"
            
            if format == "csv":
                df.to_csv(export_path, index=False)
            elif format == "json":
                df.to_json(export_path, orient="records")
            elif format == "excel":
                df.to_excel(export_path, index=False)
            
            return str(export_path)
        except Exception as e:
            print(f"Export error: {e}")
            raise
    
    def validate_country_data(self, country_name: str) -> dict:
        """Validate country data - check both tables"""
        try:
            with self.SessionLocal() as session:
                # Check orphans in teliosgeojson
                orphan_result = session.execute(
                    text("""
                        SELECT COUNT(*) 
                        FROM teliosgeojson t1
                        LEFT JOIN teliosgeojson t2 ON t1.parent_id = t2.id
                        WHERE t1.unit = :country 
                        AND t1.levelid > 0 
                        AND t2.id IS NULL
                    """),
                    {"country": country_name}
                )
                orphans = orphan_result.scalar() or 0
                
                # Check missing teliosgeojsondata entries
                missing_data = session.execute(
                    text("""
                        SELECT COUNT(*)
                        FROM teliosgeojson t
                        LEFT JOIN teliosgeojsondata d ON t.id = d.teliosgeojson_id
                        WHERE t.unit = :country AND d.id IS NULL
                    """),
                    {"country": country_name}
                )
                missing_geojsondata = missing_data.scalar() or 0
                
                return {
                    "country": country_name,
                    "orphaned_records": orphans,
                    "missing_geojsondata": missing_geojsondata,
                    "hierarchy_issues": orphans,
                    "duplicate_keys": 0,
                    "valid": orphans == 0 and missing_geojsondata == 0
                }
        except Exception as e:
            print(f"Validation error: {e}")
            return {
                "country": country_name,
                "orphaned_records": 0,
                "missing_geojsondata": 0,
                "hierarchy_issues": 0,
                "duplicate_keys": 0,
                "valid": False,
                "error": str(e)
            }
