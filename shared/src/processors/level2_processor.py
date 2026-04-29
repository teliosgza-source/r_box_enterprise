import geopandas as gpd
import pandas as pd
import json
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

class Level2Processor:
    def process_file(self, file_path):
        """Process a single Level2 GeoJSON file"""
        try:
            gdf = gpd.read_file(file_path)
            if gdf.empty:
                return None
            
            records = []
            for _, row in gdf.iterrows():
                record = {
                    'levelKey': row.get('Level2_id', ''),
                    'unit': row.get('Level2', ''),
                    'parent_id': row.get('Level1_id', ''),
                    'geometry': row.geometry.__geo_interface__ if row.geometry else {}
                }
                records.append(record)
            
            return pd.DataFrame(records)
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return None
