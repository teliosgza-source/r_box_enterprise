"""
Processor for Level 1 (State) data.
Outputs complete FeatureCollection format, matching Level2 processor style.
Handles both Map and Mapless data.
"""

import geopandas as gpd
import pandas as pd
import json
from pathlib import Path
from typing import Dict, Optional
from .base_processor import BaseProcessor

class Level1Processor(BaseProcessor):
    """Processor for state-level GeoJSON data."""
    
    def __init__(self):
        super().__init__(1)
    
    def _process_feature(self, feature) -> Optional[Dict]:
        """Process a single state feature."""
        try:
            # Get feature properties
            level0 = str(feature.get('Level0', ''))
            level0_id = str(feature.get('Level0_id', ''))
            level1 = str(feature.get('Level1', ''))
            level1_id = str(feature.get('Level1_id', ''))
            
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
                "name": level1,
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
                        "Level0_id": level0_id,
                        "Level1": level1,
                        "Level1_id": level1_id
                    },
                    "geometry": geometry
                }]
            }
            
            return {
                'Level0': level0,
                'Level0_id': level0_id,
                'Level1': level1,
                'Level1_id': level1_id,
                'parent_id': level0_id,
                'geometry': json.dumps(geojson),  # Store complete FeatureCollection
                'countryLevelId': 1,
                'levelKey': level1_id,
                'unit': level1,
                'state': level1,
                'level': 1,
                'original_id': level1_id
            }
        except Exception as e:
            print(f"❌ Error processing Level 1 feature: {e}")
            return None
    
    def process_file(self, file_path: Path) -> Optional[pd.DataFrame]:
        """Process Level 1 GeoJSON file."""
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
            print(f"Error processing Level 1 file {file_path}: {e}")
            return None
