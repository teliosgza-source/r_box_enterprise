"""
Processor for Level 0 (Country) data.
Outputs complete FeatureCollection format, matching Level2 processor style.
Handles both Map and Mapless data.
"""

import geopandas as gpd
import pandas as pd
import json
from pathlib import Path
from typing import Dict, Optional
from .base_processor import BaseProcessor

class Level0Processor(BaseProcessor):
    """Processor for country-level GeoJSON data."""
    
    def __init__(self):
        super().__init__(0)
    
    def _process_feature(self, feature) -> Optional[Dict]:
        """Process a single country feature."""
        try:
            # Get feature properties
            level0 = str(feature.get('Level0', ''))
            level0_id = str(feature.get('Level0_id', ''))
            
            # Handle geometry safely - check if it exists and has __geo_interface__
            geometry = {}
            if feature.geometry is not None:
                try:
                    geometry = feature.geometry.__geo_interface__
                except AttributeError:
                    geometry = {}
            
            # Create complete FeatureCollection format (with or without geometry)
            geojson = {
                "type": "FeatureCollection",
                "name": level0,
                "crs": {
                    "type": "name",
                    "properties": {
                        "name": "urn:ogc:def:crs:OGC:1.3:CRS84"
                    }
                },
                "features": [{
                    "type": "Feature",
                    "properties": {
                        "Level0": level0,
                        "Level0_id": level0_id
                    },
                    "geometry": geometry
                }]
            }
            
            return {
                'Level0': level0,
                'Level0_id': level0_id,
                'geometry': json.dumps(geojson),  # Store complete FeatureCollection
                'countryLevelId': 0,
                'levelKey': level0_id,
                'unit': level0,
                'level': 0,
                'original_id': level0_id
            }
        except Exception as e:
            print(f"❌ Error processing Level 0 feature: {e}")
            return None
    
    def process_file(self, file_path: Path) -> Optional[pd.DataFrame]:
        """Process Level 0 GeoJSON file."""
        try:
            gdf = self.read_geojson(file_path)
            if gdf is None:
                return None
            
            all_rows = []
            for _, feature in gdf.iterrows():
                row = self._process_feature(feature)
                if row:
                    all_rows.append(row)
            
            if not all_rows:
                return None
                
            df = pd.DataFrame(all_rows)
            return df
            
        except Exception as e:
            print(f"Error processing Level 0 file {file_path}: {e}")
            return None
