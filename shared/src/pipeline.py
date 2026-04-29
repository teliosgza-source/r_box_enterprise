"""
Core pipeline orchestration for geospatial data processing.
Uses the actual processor methods correctly.
"""

import pandas as pd
import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

# Import processors with correct methods
from processors.level0_processor import Level0Processor
from processors.level1_processor import Level1Processor
from processors.level2_processor import Level2Processor
from processors.level3_processor import Level3Processor
from processors.level4_processor import Level4Processor
from utils.country_mapper import CountryMapper


@dataclass
class ProcessingConfig:
    """Configuration for processing a country."""
    country_name: str
    country_id: int
    base_path: str
    states: List[str]
    max_level: int = 4


class GeoSpatialPipeline:
    """Main pipeline class for processing geospatial administrative data."""
    
    _global_unit_id_counter = 1
    _country_mapper = None
    
    LEVEL_DESCRIPTIONS = {
        0: 'country', 1: 'state', 2: 'district', 
        3: 'block', 4: 'village'
    }
    
    @classmethod
    def _get_country_mapper(cls):
        if cls._country_mapper is None:
            cls._country_mapper = CountryMapper()
        return cls._country_mapper
    
    @classmethod
    def reset_global_counter(cls):
        cls._global_unit_id_counter = 1
    
    FALLBACK_COUNTRY_CODES = {
        'India': 'IND', 'Indonesia': 'IDN', 'Bangladesh': 'BGD',
        'Nigeria': 'NGA', 'Pakistan': 'PAK', 'Myanmar': 'MMR',
        'Laos': 'LAO', "Côte d'Ivoire": 'CIV', 'Uganda': 'UGA',
    }
    
    def __init__(self, config: ProcessingConfig):
        self.config = config
        self.country_mapper = self._get_country_mapper()
        self.db_country_id, self.country_code = self.country_mapper.get_country_info(config.country_name)
        
        if self.db_country_id == 0:
            print(f"⚠️ Using fallback ID for {config.country_name}")
            self.db_country_id = config.country_id
            self.country_code = self.FALLBACK_COUNTRY_CODES.get(
                config.country_name, 
                config.country_name[:3].upper()
            )
        
        # State mapping for telios keys
        self.state_mapping = {state: f"{idx:02d}" 
                             for idx, state in enumerate(sorted(config.states), 1)}
        
        self.raw_data: List[Dict] = []
        self.transformed_data: Optional[pd.DataFrame] = None
        self.final_data: Optional[pd.DataFrame] = None
        self.country_start_id = None
        self.country_end_id = None
        self.temp_output = Path(config.base_path).parent / "temp_processing"
        self.temp_output.mkdir(exist_ok=True)
    
    def extract(self) -> 'GeoSpatialPipeline':
        """Extract all raw data using the correct processor methods."""
        print(f"\n🔍 Extracting data for {self.config.country_name}")
        
        base_path = Path(self.config.base_path)
        
        # ============ LEVEL 0 - COUNTRY ============
        level0_path = base_path / "Level0.geojson"
        if level0_path.exists():
            try:
                level0_proc = Level0Processor()
                level0_df = level0_proc.process_file(level0_path)
                
                if level0_df is not None and not level0_df.empty:
                    if 'levelKey' not in level0_df.columns:
                        level0_df['levelKey'] = level0_df['Level0_id']
                    if 'unit' not in level0_df.columns:
                        level0_df['unit'] = level0_df['Level0']
                    level0_df['countryLevelId'] = 0
                    level0_df['level'] = 0
                    level0_df['state'] = None
                    
                    self.raw_data.extend(level0_df.to_dict('records'))
                    print(f"   ✅ Level 0: {len(level0_df)} record")
            except Exception as e:
                print(f"❌ Error processing Level 0: {e}")
        
        # ============ CHECK FOR FLAT STRUCTURE ============
        level1_root = base_path / "Level1.geojson"
        level2_root = base_path / "Level2.geojson"
        level3_root = base_path / "Level3.geojson"
        level4_root = base_path / "Level4.geojson"
        
        has_flat_structure = level1_root.exists()
        
        if has_flat_structure:
            print(f"   📁 Detected flat structure - processing root level files")
            
            # Process Level 1 from root
            try:
                level1_proc = Level1Processor()
                level1_df = level1_proc.process_file(level1_root)
                
                if level1_df is not None and not level1_df.empty:
                    if 'levelKey' not in level1_df.columns:
                        level1_df['levelKey'] = level1_df['Level1_id']
                    if 'unit' not in level1_df.columns:
                        level1_df['unit'] = level1_df['Level1']
                    level1_df['countryLevelId'] = 1
                    level1_df['level'] = 1
                    level1_df['state'] = level1_df['unit']
                    
                    self.raw_data.extend(level1_df.to_dict('records'))
                    print(f"      ✅ Level 1 (flat): {len(level1_df)} records")
                    
                    # Create parent lookup for Level 2
                    parent_df = pd.DataFrame({
                        'Level1': level1_df['unit'].tolist(),
                        'Level1_id': level1_df['levelKey'].tolist()
                    })
                    
                    # Process Level 2 - Check if it's a directory or single file
                    if level2_root.exists():
                        try:
                            level2_proc = Level2Processor()
                            
                            # Check if Level2 is a directory or a single file
                            if level2_root.is_file():
                                # It's a single GeoJSON file containing all districts
                                print(f"      📄 Processing single Level2.geojson file")
                                # For single file, we need to read it directly
                                import geopandas as gpd
                                gdf = gpd.read_file(str(level2_root))
                                level2_records = []
                                for _, feature in gdf.iterrows():
                                    level1_name = feature.get('Level1', None)
                                    level1_id = parent_df[parent_df['Level1'] == level1_name]['Level1_id'].values
                                    level1_id_val = level1_id[0] if len(level1_id) > 0 else None
                                    
                                    geometry = {}
                                    if feature.geometry is not None:
                                        try:
                                            geometry = feature.geometry.__geo_interface__
                                        except:
                                            geometry = {}
                                    
                                    record = {
                                        'levelKey': feature.get('Level2_id', ''),
                                        'unit': feature.get('Level2', ''),
                                        'parent_id': level1_id_val,
                                        'geometry': geometry,
                                        'countryLevelId': 2,
                                        'level': 2,
                                        'state': level1_name
                                    }
                                    level2_records.append(record)
                                
                                if level2_records:
                                    level2_df = pd.DataFrame(level2_records)
                                    self.raw_data.extend(level2_df.to_dict('records'))
                                    print(f"      ✅ Level 2 (flat): {len(level2_df)} records")
                                    
                                    # Process Level 3
                                    if level3_root.exists() and level3_root.is_file():
                                        print(f"      📄 Processing single Level3.geojson file")
                                        gdf3 = gpd.read_file(str(level3_root))
                                        level3_records = []
                                        for _, feature in gdf3.iterrows():
                                            level2_name = feature.get('Level2', None)
                                            parent_id = None
                                            if level2_name in level2_df['unit'].values:
                                                parent_id = level2_df[level2_df['unit'] == level2_name]['levelKey'].values
                                                parent_id = parent_id[0] if len(parent_id) > 0 else None
                                            
                                            geometry = {}
                                            if feature.geometry is not None:
                                                try:
                                                    geometry = feature.geometry.__geo_interface__
                                                except:
                                                    geometry = {}
                                            
                                            record = {
                                                'levelKey': feature.get('Level3_id', ''),
                                                'unit': feature.get('Level3', ''),
                                                'parent_id': parent_id,
                                                'geometry': geometry,
                                                'countryLevelId': 3,
                                                'level': 3,
                                                'state': level2_df[level2_df['unit'] == level2_name]['state'].values[0] if level2_name in level2_df['unit'].values else ''
                                            }
                                            level3_records.append(record)
                                        
                                        if level3_records:
                                            level3_df = pd.DataFrame(level3_records)
                                            self.raw_data.extend(level3_df.to_dict('records'))
                                            print(f"      ✅ Level 3 (flat): {len(level3_df)} records")
                            else:
                                # It's a directory - use the processor's process method
                                print(f"      📁 Processing Level2 directory")
                                level2_df = level2_proc.process(
                                    str(level2_root),
                                    parent_df,
                                    str(level3_root.parent) if level3_root.exists() else None,
                                    str(self.temp_output)
                                )
                                
                                if level2_df is not None and not level2_df.empty:
                                    if 'levelKey' not in level2_df.columns:
                                        level2_df = level2_df.rename(columns={'Level2_id': 'levelKey', 'Level2': 'unit'})
                                    level2_df['countryLevelId'] = 2
                                    level2_df['level'] = 2
                                    level2_df['state'] = level2_df.apply(
                                        lambda row: self._find_state_for_district(row.get('Level1', ''), parent_df),
                                        axis=1
                                    )
                                    self.raw_data.extend(level2_df.to_dict('records'))
                                    print(f"      ✅ Level 2 (flat): {len(level2_df)} records")
                        except Exception as e:
                            print(f"      ❌ Error processing Level 2: {e}")
            except Exception as e:
                print(f"❌ Error processing flat Level 1: {e}")
        
        # ============ PROCESS HIERARCHICAL STRUCTURE (State directories) ============
        for state in self.config.states:
            state_path = base_path / state
            if not state_path.exists():
                continue
            
            # Skip if we already processed this state in flat structure
            if has_flat_structure and (state_path / "Level1.geojson").exists():
                continue
            
            print(f"\n   📍 Processing {state}...")
            
            # Level 1 - State file
            level1_path = state_path / "Level1.geojson"
            if level1_path.exists():
                try:
                    level1_proc = Level1Processor()
                    level1_df = level1_proc.process_file(level1_path)
                    
                    if level1_df is not None and not level1_df.empty:
                        if 'levelKey' not in level1_df.columns:
                            level1_df['levelKey'] = level1_df['Level1_id']
                        if 'unit' not in level1_df.columns:
                            level1_df['unit'] = level1_df['Level1']
                        level1_df['countryLevelId'] = 1
                        level1_df['level'] = 1
                        level1_df['state'] = state
                        
                        self.raw_data.extend(level1_df.to_dict('records'))
                        print(f"      ✅ Level 1: {len(level1_df)} record")
                        
                        parent_df = pd.DataFrame({
                            'Level1': level1_df['unit'].tolist(),
                            'Level1_id': level1_df['levelKey'].tolist()
                        })
                        
                        # Level 2 directory
                        level2_dir = state_path / "Level2"
                        if level2_dir.exists() and level2_dir.is_dir():
                            level3_dir = state_path / "Level3"
                            level2_proc = Level2Processor()
                            level2_df = level2_proc.process(
                                str(level2_dir),
                                parent_df,
                                str(level3_dir) if level3_dir.exists() else None,
                                str(self.temp_output)
                            )
                            
                            if level2_df is not None and not level2_df.empty:
                                if 'levelKey' not in level2_df.columns:
                                    level2_df = level2_df.rename(columns={'Level2_id': 'levelKey', 'Level2': 'unit'})
                                level2_df['countryLevelId'] = 2
                                level2_df['level'] = 2
                                level2_df['state'] = state
                                
                                self.raw_data.extend(level2_df.to_dict('records'))
                                print(f"      ✅ Level 2: {len(level2_df)} records")
                                
                                # Level 3 directory
                                if level3_dir.exists() and level3_dir.is_dir():
                                    level4_dir = state_path / "Level4"
                                    level3_proc = Level3Processor()
                                    level3_df = level3_proc.process(
                                        str(level3_dir),
                                        level2_df,
                                        str(level4_dir) if level4_dir.exists() else None,
                                        str(self.temp_output)
                                    )
                                    
                                    if level3_df is not None and not level3_df.empty:
                                        if 'levelKey' not in level3_df.columns:
                                            level3_df = level3_df.rename(columns={'Level3_id': 'levelKey', 'Level3': 'unit'})
                                        level3_df['countryLevelId'] = 3
                                        level3_df['level'] = 3
                                        level3_df['state'] = state
                                        
                                        self.raw_data.extend(level3_df.to_dict('records'))
                                        print(f"      ✅ Level 3: {len(level3_df)} records")
                                        
                                        # Level 4 directory
                                        if level4_dir.exists() and level4_dir.is_dir():
                                            level4_proc = Level4Processor()
                                            level4_df = level4_proc.process(
                                                str(level4_dir),
                                                level3_df,
                                                str(self.temp_output)
                                            )
                                            
                                            if level4_df is not None and not level4_df.empty:
                                                if 'levelKey' not in level4_df.columns:
                                                    level4_df = level4_df.rename(columns={'Level4_id': 'levelKey', 'Level4': 'unit'})
                                                level4_df['countryLevelId'] = 4
                                                level4_df['level'] = 4
                                                level4_df['state'] = state
                                                
                                                self.raw_data.extend(level4_df.to_dict('records'))
                                                print(f"      ✅ Level 4: {len(level4_df)} records")
                except Exception as e:
                    print(f"❌ Error processing {state}: {e}")
        
        print(f"\n✅ Extracted {len(self.raw_data)} total records for {self.config.country_name}")
        return self
    
    def _find_state_for_district(self, level1_name: str, parent_df: pd.DataFrame) -> str:
        """Find state name for a district."""
        if parent_df.empty or not level1_name:
            return ''
        state_row = parent_df[parent_df['Level1'] == level1_name]
        if not state_row.empty:
            return state_row.iloc[0]['Level1']
        return ''
    
    def transform(self) -> 'GeoSpatialPipeline':
        """Transform raw data into structured format with hierarchical keys."""
        print(f"🔄 Transforming data for {self.config.country_name}...")
        
        if not self.raw_data:
            raise ValueError("No data to transform. Run extract() first.")
        
        df = pd.DataFrame(self.raw_data)
        
        # Clean geometry
        if 'geometry' in df.columns:
            df['geometry'] = df['geometry'].apply(
                lambda x: x if isinstance(x, str) else json.dumps(x) if x else '{}'
            )
        
        # Remove duplicates
        df = df.drop_duplicates(subset=['levelKey', 'countryLevelId'], keep='first')
        df = df.sort_values(['countryLevelId', 'state', 'levelKey']).reset_index(drop=True)
        
        # Add metadata
        df['country'] = self.config.country_name
        df['country_code'] = self.country_code
        df['levelDescription'] = df['countryLevelId'].map(self.LEVEL_DESCRIPTIONS)
        
        # Generate hierarchical telios keys
        telios_keys, parent_keys, telios_parent_keys = self._generate_keys(df)
        
        df['telioslevelKey'] = telios_keys
        df['parentlevelKey'] = parent_keys
        df['teliosparentlevelKey'] = telios_parent_keys
        df['countnextLevel'] = df.apply(lambda row: self._count_children(row, df), axis=1)
        
        self.transformed_data = df
        print(f"✅ Transformed {len(df)} records")
        return self
    
    def _generate_keys(self, df: pd.DataFrame) -> tuple:
        """Generate hierarchical telios keys."""
        telios_keys = []
        parent_keys = []
        telios_parent_keys = []
        
        level_key_to_pos = {}
        for pos, (idx, row) in enumerate(df.iterrows()):
            level_key_to_pos[(row['countryLevelId'], row['levelKey'])] = pos
        
        counters = {'district': {}, 'block': {}, 'village': {}}
        
        for pos, (idx, row) in enumerate(df.iterrows()):
            level = row['countryLevelId']
            state = row['state']
            level_key = row['levelKey']
            parent_level_key = row.get('parent_id', '')
            
            if level == 0:
                telios_key = self.country_code
                parent_key = ''
                telios_parent = ''
            elif level == 1:
                state_code = self.state_mapping.get(state, '01')
                telios_key = f"{self.country_code}-{state_code}"
                parent_key = ''
                telios_parent = self.country_code
            elif level == 2:
                state_code = self.state_mapping.get(state, '01')
                telios_parent = f"{self.country_code}-{state_code}"
                parent_pos = level_key_to_pos.get((1, state))
                if parent_pos is not None:
                    telios_parent = telios_keys[parent_pos]
                
                counter_key = state
                if counter_key not in counters['district']:
                    counters['district'][counter_key] = 1
                seq_num = counters['district'][counter_key]
                counters['district'][counter_key] += 1
                telios_key = f"{telios_parent}-{seq_num:03d}"
                parent_key = parent_level_key
            elif level == 3:
                parent_pos = level_key_to_pos.get((2, parent_level_key))
                if parent_pos is not None:
                    telios_parent = telios_keys[parent_pos]
                else:
                    telios_parent = f"{self.country_code}-001-001"
                
                counter_key = telios_parent
                if counter_key not in counters['block']:
                    counters['block'][counter_key] = 1
                seq_num = counters['block'][counter_key]
                counters['block'][counter_key] += 1
                telios_key = f"{telios_parent}-{seq_num:04d}"
                parent_key = parent_level_key
            else:
                parent_pos = level_key_to_pos.get((3, parent_level_key))
                if parent_pos is not None:
                    telios_parent = telios_keys[parent_pos]
                else:
                    telios_parent = f"{self.country_code}-001-001-0001"
                
                counter_key = telios_parent
                if counter_key not in counters['village']:
                    counters['village'][counter_key] = 1
                seq_num = counters['village'][counter_key]
                counters['village'][counter_key] += 1
                telios_key = f"{telios_parent}-{seq_num:06d}"
                parent_key = parent_level_key
            
            telios_keys.append(telios_key)
            parent_keys.append(parent_key)
            telios_parent_keys.append(telios_parent)
        
        return telios_keys, parent_keys, telios_parent_keys
    
    def _count_children(self, row, df) -> int:
        if row['countryLevelId'] >= self.config.max_level:
            return 0
        child_level = row['countryLevelId'] + 1
        children = df[
            (df['parentlevelKey'] == row['levelKey']) & 
            (df['countryLevelId'] == child_level)
        ]
        return len(children)
    
    def finalize(self) -> 'GeoSpatialPipeline':
        """Finalize data with sequential global IDs."""
        print(f"🏁 Finalizing data for {self.config.country_name}...")
        
        if self.transformed_data is None:
            raise ValueError("No transformed data. Run transform() first.")
        
        df = self.transformed_data.copy()
        df = df.sort_values(['countryLevelId', 'telioslevelKey']).reset_index(drop=True)
        
        self.country_start_id = self.__class__._global_unit_id_counter
        record_count = len(df)
        
        df['unitid'] = range(self.country_start_id, self.country_start_id + record_count)
        self.__class__._global_unit_id_counter += record_count
        self.country_end_id = self.__class__._global_unit_id_counter - 1
        
        telios_to_unitid = dict(zip(df['telioslevelKey'], df['unitid']))
        df['parentid'] = df['teliosparentlevelKey'].map(telios_to_unitid)
        
        country_mask = df['countryLevelId'] == 0
        df.loc[country_mask, 'parentid'] = df.loc[country_mask, 'unitid']
        df['parentid'] = df['parentid'].fillna(0).astype(int)
        df['country_id'] = self.db_country_id
        df['data_type'] = getattr(self.config, 'data_type', 'Map')
        
        self.final_data = df
        
        print(f"✅ Finalized {len(df)} records")
        print(f"   Global UnitID range: {self.country_start_id} to {self.country_end_id}")
        
        return self
    
    def get_country_data(self) -> Optional[pd.DataFrame]:
        return self.final_data.copy() if self.final_data is not None else None


class GlobalGeoSpatialProcessor:
    """Global processor for multiple countries."""
    
    def __init__(self, output_base: str = "Finale"):
        self.output_base = Path(output_base)
        self.output_base.mkdir(parents=True, exist_ok=True)
        GeoSpatialPipeline.reset_global_counter()
        self.all_country_data: List[pd.DataFrame] = []
        self.processing_results: List[Dict] = []
    
    def process_country(self, country_config: dict) -> Dict:
        """Process a single country."""
        print(f"\n{'='*70}")
        print(f"🏁 PROCESSING COUNTRY: {country_config['name']}")
        print(f"{'='*70}")
        
        data_type = country_config.get('data_type', 'Map')
        
        config = ProcessingConfig(
            country_name=country_config['name'],
            country_id=country_config.get('countryId', 1),
            base_path=country_config['base_path'],
            states=country_config.get('states', []),
            max_level=country_config.get('max_level', 4)
        )
        config.data_type = data_type
        
        pipeline = GeoSpatialPipeline(config)
        pipeline.extract().transform().finalize()
        
        country_df = pipeline.get_country_data()
        if country_df is not None:
            self.all_country_data.append(country_df)
        
        result = {
            'country': country_config['name'],
            'country_code': pipeline.country_code,
            'db_country_id': pipeline.db_country_id,
            'record_count': len(country_df) if country_df is not None else 0,
            'start_id': pipeline.country_start_id,
            'end_id': pipeline.country_end_id,
            'states_processed': len(config.states),
            'max_level': config.max_level,
            'data_type': data_type
        }
        
        self.processing_results.append(result)
        return result
    
    def get_final_dataframe(self) -> Optional[pd.DataFrame]:
        if not self.all_country_data:
            return None
        return pd.concat(self.all_country_data, ignore_index=True)
    
    def consolidate_outputs(self) -> Optional[pd.DataFrame]:
        """Consolidate all countries' data into output files."""
        if not self.all_country_data:
            print("❌ No data to consolidate")
            return None
        
        final_df = pd.concat(self.all_country_data, ignore_index=True)
        final_df = final_df.sort_values('unitid').reset_index(drop=True)
        
        print(f"✅ Consolidated {len(final_df)} total records")
        
        # Save all output files
        self._save_output_files(final_df)
        self._generate_report(final_df)
        
        return final_df
    
    def _save_output_files(self, final_df: pd.DataFrame):
        """Save all output CSV files."""
        
        # Unit.csv
        unit_cols = ['unitid', 'parentid', 'country_id', 'country', 'country_code',
                     'levelDescription', 'countryLevelId', 'levelKey', 'telioslevelKey', 
                     'countnextLevel', 'unit', 'parentlevelKey', 'teliosparentlevelKey']
        available_cols = [col for col in unit_cols if col in final_df.columns]
        unit_df = final_df[available_cols].copy()
        unit_df.to_csv(self.output_base / "Unit.csv", index=False)
        print(f"   ✅ Unit.csv: {len(unit_df)} records")
        
        # PSQL_Geo.csv
        psql_cols = ['unitid', 'parentid', 'country_id', 'countryLevelId',
                     'levelKey', 'telioslevelKey', 'countnextLevel', 'unit', 'geometry']
        psql_available = [col for col in psql_cols if col in final_df.columns]
        psql_df = final_df[psql_available].copy()
        if not psql_df.empty:
            psql_df.columns = ['unitid', 'parent_id', 'country_id', 'levelid',
                               'levelkey', 'tellevelkey', 'countnextlevel', 'unit', 'geometry']
            psql_df.to_csv(self.output_base / "PSQL_Geo.csv", index=False)
            print(f"   ✅ PSQL_Geo.csv: {len(psql_df)} records")
        
        # teliosgeojson.csv
        telios_df = pd.DataFrame({
            'unitid': final_df['unitid'],
            'parent_id': final_df['parentid'],
            'country_id': final_df['country_id'],
            'levelid': final_df['countryLevelId'],
            'levelkey': final_df.get('levelKey', ''),
            'tellevelkey': final_df['telioslevelKey'],
            'countnextlevel': final_df['countnextLevel'],
            'unit': final_df['unit'],
            'geo_json': final_df.get('geometry', '{}')
        })
        telios_df.to_csv(self.output_base / "teliosgeojson.csv", index=False)
        print(f"   ✅ teliosgeojson.csv: {len(telios_df)} records")
        
        # teliosgeojsondata.csv
        telios_data_df = pd.DataFrame({
            'teliosgeojson_id': final_df['unitid'],
            'geojson': final_df.get('geometry', '{}'),
            'levelkey': final_df.get('levelKey', '')
        })
        telios_data_df.to_csv(self.output_base / "teliosgeojsondata.csv", index=False)
        print(f"   ✅ teliosgeojsondata.csv: {len(telios_data_df)} records")
        
        # GeoJSON.csv (legacy)
        geojson_df = pd.DataFrame({
            'teliosgeojson_id': final_df['unitid'],
            'geojson': final_df.get('geometry', '{}')
        })
        geojson_df.to_csv(self.output_base / "GeoJSON.csv", index=False)
        print(f"   ✅ GeoJSON.csv: {len(geojson_df)} records")
    
    def _generate_report(self, final_df: pd.DataFrame):
        """Generate processing report."""
        report_file = self.output_base / "global_processing_report.txt"
        
        with open(report_file, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("🌍 GLOBAL GEOSPATIAL PROCESSING REPORT\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Output Directory: {self.output_base.absolute()}\n\n")
            
            f.write("📊 COUNTRIES PROCESSED\n")
            f.write("-" * 80 + "\n")
            
            total_records = 0
            for result in self.processing_results:
                f.write(f"  {result['country']:<20} "
                       f"[{result.get('data_type', 'Map'):<7}] "
                       f"{result['record_count']:>10,} records\n")
                total_records += result['record_count']
            
            f.write("-" * 80 + "\n")
            f.write(f"  TOTAL:{' ':<18} {total_records:>10,} records\n\n")
            
            f.write("📋 LEVEL DISTRIBUTION:\n")
            for level in sorted(final_df['countryLevelId'].unique()):
                count = len(final_df[final_df['countryLevelId'] == level])
                desc = GeoSpatialPipeline.LEVEL_DESCRIPTIONS.get(level, f'Level {level}')
                f.write(f"  {desc:<10}: {count:>10,} records\n")
            
            f.write("\n" + "=" * 80 + "\n")
            f.write("✅ PROCESSING COMPLETED SUCCESSFULLY\n")
            f.write("=" * 80 + "\n")
        
        print(f"\n📄 Report: {report_file}")
