"""
Base processor class for level-specific processing.
"""

import geopandas as gpd
import pandas as pd
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional


class BaseProcessor(ABC):
    """Abstract base class for GeoJSON level processors."""

    def __init__(self, level: int):
        self.level = level
        self.id_field = f"Level{level}_id"
        self.name_field = f"Level{level}"

    def read_geojson(self, file_path: Path) -> Optional[gpd.GeoDataFrame]:
        """Read GeoJSON file with error handling."""
        try:
            return gpd.read_file(str(file_path))
        except Exception as e:
            print(f"❌ Error reading {file_path}: {e}")
            return None

    def extract_features(self, gdf: gpd.GeoDataFrame) -> List[Dict]:
        """Extract features from GeoDataFrame."""
        features = []
        for _, feature in gdf.iterrows():
            row = self._process_feature(feature)
            if row:
                features.append(row)
        return features

    @abstractmethod
    def _process_feature(self, feature) -> Optional[Dict]:
        """Process a single feature. Override in subclass."""
        pass

    def process_file(self, file_path: Path) -> Optional[pd.DataFrame]:
        """Process a single GeoJSON file."""
        gdf = self.read_geojson(file_path)
        if gdf is None:
            return None

        features = self.extract_features(gdf)
        if not features:
            return None

        return pd.DataFrame(features)

    def process_directory(self, directory: Path) -> Optional[pd.DataFrame]:
        """Process all GeoJSON files in a directory."""
        if not directory.exists():
            return None

        all_data = []
        for geojson_file in directory.glob("*.geojson"):
            df = self.process_file(geojson_file)
            if df is not None:
                all_data.append(df)

        if not all_data:
            return None

        return pd.concat(all_data, ignore_index=True)
