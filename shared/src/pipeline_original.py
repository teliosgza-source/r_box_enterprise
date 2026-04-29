"""
Core pipeline orchestration for geospatial data processing.
Single responsibility: Coordinate extraction, transformation, and output generation.
Features: Continuous global ID sequencing across all countries, consolidated Finale output.
Uses staging database IDs from config file.
"""

import pandas as pd
import geopandas as gpd
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime

# Import ALL processors (Level 0-4)
from processors.level0_processor import Level0Processor
from processors.level1_processor import Level1Processor
from processors.level2_processor import Level2Processor
from processors.level3_processor import Level3Processor
from processors.level4_processor import Level4Processor

# Import country mapper
from utils.country_mapper import CountryMapper

@dataclass
class ProcessingConfig:
    """Configuration for processing a country/state."""
    country_name: str
    country_id: int
    base_path: str
    states: List[str]
    max_level: int = 4

class GeoSpatialPipeline:
    """
    Main pipeline class for processing geospatial administrative data.
    
    Features:
    - Continuous global unitid sequencing across all countries
    - Consolidated Finale output folder
    - Consistent FeatureCollection format for all levels
    - Staging database IDs from config file
    """
    
    # Class-level variable to track global unit ID across ALL countries
    _global_unit_id_counter = 1
    
    # Initialize country mapper (class-level to share across instances)
    _country_mapper = None
    
    @classmethod
    def _get_country_mapper(cls):
        """Get or create the country mapper instance."""
        if cls._country_mapper is None:
            cls._country_mapper = CountryMapper()
        return cls._country_mapper
    
    @classmethod
    def reset_global_counter(cls):
        """Reset the global counter (useful for testing)."""
        cls._global_unit_id_counter = 1
    
    @classmethod
    def get_next_global_id(cls, increment=1):
        """Get next global unit ID and increment counter."""
        current = cls._global_unit_id_counter
        cls._global_unit_id_counter += increment
        return current
    
    # Country code mapping (fallback if not in config)
    FALLBACK_COUNTRY_CODES = {
        'India': 'IND', 'Indonesia': 'IDN', 'Bangladesh': 'BGD',
        'Nigeria': 'NGA', 'Pakistan': 'PAK', 'Myanmar': 'MMR',
        'Laos': 'LAO', "Côte d'Ivoire": 'CIV', 'Uganda': 'UGA',
        'Ivory Coast': 'CIV', 'Myanmar': 'MMR'
    }
    
    LEVEL_DESCRIPTIONS = {
        0: 'country', 1: 'state', 2: 'district', 
        3: 'block', 4: 'village'
    }
    
    def __init__(self, config: ProcessingConfig):
        self.config = config
        
        # Get staging database ID and ISO code from mapper
        self.country_mapper = self._get_country_mapper()
        self.db_country_id, self.country_code = self.country_mapper.get_country_info(config.country_name)
        
        # If not found in config, use fallback
        if self.db_country_id == 0:
            print(f"⚠️ Using fallback ID for {config.country_name}")
            self.db_country_id = config.country_id
            self.country_code = self.FALLBACK_COUNTRY_CODES.get(
                config.country_name, 
                config.country_name[:3].upper()
            )
        
        # State mapping (alphabetical)
        self.state_mapping = {state: f"{idx:02d}" 
                             for idx, state in enumerate(sorted(config.states), 1)}
        
        # Data storage
        self.raw_data: List[Dict] = []
        self.transformed_data: Optional[pd.DataFrame] = None
        self.final_data: Optional[pd.DataFrame] = None
        
        # Track start ID for this country
        self.country_start_id = None
        self.country_end_id = None
        
    def extract(self) -> 'GeoSpatialPipeline':
        """Extract all raw data from GeoJSON files using processors for ALL levels (0-4)."""
        print(f"\n🔍 Extracting data for {self.config.country_name}")
        
        base_path = Path(self.config.base_path)
        
        # ============ LEVEL 0 - COUNTRY ============
        level0_path = base_path / "Level0.geojson"
        if level0_path.exists():
            try:
                level0_proc = Level0Processor()
                level0_df = level0_proc.process_file(level0_path)
                
                if level0_df is not None and not level0_df.empty:
                    # Ensure consistent column naming
                    if 'levelKey' not in level0_df.columns:
                        level0_df['levelKey'] = level0_df['Level0_id']
                    if 'unit' not in level0_df.columns:
                        level0_df['unit'] = level0_df['Level0']
                    level0_df['countryLevelId'] = 0
                    level0_df['level'] = 0
                    level0_df['state'] = None
                    level0_df['original_id'] = level0_df['Level0_id']
                    
                    self.raw_data.extend(level0_df.to_dict('records'))
                    print(f"   ✅ Level 0: {len(level0_df)} record")
            except Exception as e:
                print(f"❌ Error processing Level 0: {e}")
        else:
            print(f"⚠️ Level0.geojson not found at {level0_path}")
        
        # ============ PROCESS EACH STATE ============
        for state in self.config.states:
            state_path = base_path / state
            if not state_path.exists():
                print(f"⚠️ State path not found: {state_path}")
                continue
            
            print(f"\n   📍 Processing {state}...")
            
            # ============ LEVEL 1 - STATE ============
            level1_path = state_path / "Level1.geojson"
            level1_df = None
            parent_df = pd.DataFrame()
            
            if level1_path.exists():
                try:
                    level1_proc = Level1Processor()
                    level1_df = level1_proc.process_file(level1_path)
                    
                    if level1_df is not None and not level1_df.empty:
                        # Ensure consistent column naming
                        if 'levelKey' not in level1_df.columns:
                            level1_df['levelKey'] = level1_df['Level1_id']
                        if 'unit' not in level1_df.columns:
                            level1_df['unit'] = level1_df['Level1']
                        level1_df['countryLevelId'] = 1
                        level1_df['level'] = 1
                        level1_df['state'] = state
                        level1_df['original_id'] = level1_df['Level1_id']
                        
                        self.raw_data.extend(level1_df.to_dict('records'))
                        print(f"      ✅ Level 1: {len(level1_df)} record")
                        
                        # Create parent DataFrame for Level 2 processor
                        if 'Level1' in level1_df.columns and 'Level1_id' in level1_df.columns:
                            parent_df = pd.DataFrame({
                                'Level1': level1_df['Level1'].tolist(),
                                'Level1_id': level1_df['Level1_id'].tolist()
                            })
                except Exception as e:
                    print(f"❌ Error processing Level 1: {e}")
            else:
                print(f"      ⚠️ Level1.geojson not found")
            
            # ============ LEVEL 2 - DISTRICTS ============
            level2_dir = state_path / "Level2"
            level3_dir = state_path / "Level3"
            level2_df = None
            
            if level2_dir.exists() and level2_dir.is_dir():
                try:
                    level2_proc = Level2Processor()
                    # Create temp output path (processors need this but we don't use the files)
                    temp_output = base_path.parent / "temp_processing"
                    temp_output.mkdir(exist_ok=True)
                    
                    level2_df = level2_proc.process(
                        str(level2_dir),
                        parent_df,
                        str(level3_dir) if level3_dir.exists() else None,
                        str(temp_output)
                    )
                    
                    if level2_df is not None and not level2_df.empty:
                        # Rename columns to match pipeline format
                        level2_df = level2_df.rename(columns={
                            'Level2_id': 'levelKey',
                            'Level2': 'unit',
                            'parent_id': 'parent_id'
                        })
                        level2_df['countryLevelId'] = 2
                        level2_df['state'] = state
                        level2_df['level'] = 2
                        level2_df['original_id'] = level2_df['levelKey']
                        
                        self.raw_data.extend(level2_df.to_dict('records'))
                        print(f"      ✅ Level 2: {len(level2_df)} records")
                    else:
                        print(f"      ⚠️ Level 2: No records processed")
                except Exception as e:
                    print(f"      ❌ Error processing Level 2: {e}")
            else:
                print(f"      ⚠️ Level2 directory not found")
            
            # ============ LEVEL 3 - BLOCKS ============
            level3_dir = state_path / "Level3"
            level4_dir = state_path / "Level4"
            level3_df = None
            
            if level3_dir.exists() and level3_dir.is_dir():
                try:
                    level3_proc = Level3Processor()
                    temp_output = base_path.parent / "temp_processing"
                    
                    level3_df = level3_proc.process(
                        str(level3_dir),
                        level2_df if level2_df is not None else pd.DataFrame(),
                        str(level4_dir) if level4_dir.exists() else None,
                        str(temp_output)
                    )
                    
                    if level3_df is not None and not level3_df.empty:
                        # Rename columns to match pipeline format
                        level3_df = level3_df.rename(columns={
                            'Level3_id': 'levelKey',
                            'Level3': 'unit',
                            'parent_id': 'parent_id'
                        })
                        level3_df['countryLevelId'] = 3
                        level3_df['state'] = state
                        level3_df['level'] = 3
                        level3_df['original_id'] = level3_df['levelKey']
                        
                        self.raw_data.extend(level3_df.to_dict('records'))
                        print(f"      ✅ Level 3: {len(level3_df)} records")
                    else:
                        print(f"      ⚠️ Level 3: No records processed")
                except Exception as e:
                    print(f"      ❌ Error processing Level 3: {e}")
            else:
                print(f"      ⚠️ Level3 directory not found")
            
            # ============ LEVEL 4 - VILLAGES ============
            level4_dir = state_path / "Level4"
            
            if level4_dir.exists() and level4_dir.is_dir():
                try:
                    level4_proc = Level4Processor()
                    temp_output = base_path.parent / "temp_processing"
                    
                    level4_df = level4_proc.process(
                        str(level4_dir),
                        level3_df if level3_df is not None else pd.DataFrame(),
                        str(temp_output)
                    )
                    
                    if level4_df is not None and not level4_df.empty:
                        # Rename columns to match pipeline format
                        level4_df = level4_df.rename(columns={
                            'Level4_id': 'levelKey',
                            'Level4': 'unit',
                            'parent_id': 'parent_id'
                        })
                        level4_df['countryLevelId'] = 4
                        level4_df['state'] = state
                        level4_df['level'] = 4
                        level4_df['original_id'] = level4_df['levelKey']
                        
                        self.raw_data.extend(level4_df.to_dict('records'))
                        print(f"      ✅ Level 4: {len(level4_df)} records")
                    else:
                        print(f"      ⚠️ Level 4: No records processed")
                except Exception as e:
                    print(f"      ❌ Error processing Level 4: {e}")
            else:
                print(f"      ⚠️ Level4 directory not found")
        
        print(f"\n✅ Extracted {len(self.raw_data)} total records for {self.config.country_name}")
        return self
    
    def transform(self) -> 'GeoSpatialPipeline':
        """Transform raw data into structured format with proper IDs - FIXED COUNTER KEYS."""
        print(f"🔄 Transforming data for {self.config.country_name}...")
        
        if not self.raw_data:
            raise ValueError("No data to transform. Run extract() first.")
        
        # Create base DataFrame
        df = pd.DataFrame(self.raw_data)
        
        # Ensure geometry is string (should already be JSON string of FeatureCollection)
        if 'geometry' in df.columns:
            df['geometry'] = df['geometry'].apply(
                lambda x: x if isinstance(x, str) else json.dumps(x) if x else '{}'
            )
        
        # Remove duplicates based on levelKey and level
        df = df.drop_duplicates(subset=['levelKey', 'countryLevelId'], keep='first')
        
        # Sort by level, state, and levelKey for consistent ordering
        df = df.sort_values(['countryLevelId', 'state', 'levelKey']).reset_index(drop=True)
        
        # Add metadata
        df['country'] = self.config.country_name
        df['country_code'] = self.country_code
        df['levelDescription'] = df['countryLevelId'].map(self.LEVEL_DESCRIPTIONS)
        
        # Generate Telios keys in a single pass through the dataframe
        telios_keys = []
        parent_keys = []
        telios_parent_keys = []
        
        # Create lookup from (level, levelKey) to row position for parent finding
        level_key_to_pos = {}
        for pos, (idx, row) in enumerate(df.iterrows()):
            level_key_to_pos[(row['countryLevelId'], row['levelKey'])] = pos
        
        # Track sequence numbers per parent for each level
        district_counters = {}  # (state) -> next district number
        block_counters = {}     # (district_telios_key) -> next block number - FIXED
        village_counters = {}   # (block_telios_key) -> next village number - FIXED
        
        for pos, (idx, row) in enumerate(df.iterrows()):
            level = row['countryLevelId']
            state = row['state']
            level_key = row['levelKey']
            parent_level_key = row.get('parent_id', '')
            
            if level == 0:
                # Country
                telios_key = self.country_code
                parent_key = ''
                telios_parent = ''
                
            elif level == 1:
                # State
                state_code = self.state_mapping.get(state, '01')
                telios_key = f"{self.country_code}-{state_code}"
                # Parent is country
                country_pos = level_key_to_pos.get((0, self.country_code))
                if country_pos is not None:
                    parent_key = df.iloc[country_pos]['levelKey']
                else:
                    parent_key = ''
                telios_parent = self.country_code
                
            elif level == 2:
                # District
                state_code = self.state_mapping.get(state, '01')
                
                # Find parent state
                state_mask = (df['countryLevelId'] == 1) & (df['state'] == state)
                state_rows = df[state_mask]
                if state_rows.empty:
                    parent_key = ''
                    telios_parent = f"{self.country_code}-{state_code}"
                else:
                    parent_row = state_rows.iloc[0]
                    parent_key = parent_row['levelKey']
                    parent_pos = level_key_to_pos.get((1, parent_key), 0)
                    telios_parent = telios_keys[parent_pos] if parent_pos < len(telios_keys) else f"{self.country_code}-{state_code}"
                
                # Sequential district number per state
                counter_key = state
                if counter_key not in district_counters:
                    district_counters[counter_key] = 1
                seq_num = district_counters[counter_key]
                district_counters[counter_key] += 1
                
                seq = f"{seq_num:03d}"
                telios_key = f"{telios_parent}-{seq}"
                
            elif level == 3:
                # Block
                state_code = self.state_mapping.get(state, '01')
                
                # Find parent district
                parent_pos = level_key_to_pos.get((2, parent_level_key))
                if parent_pos is None:
                    # Try fuzzy match
                    parent_mask = (df['countryLevelId'] == 2) & (df['state'] == state) & \
                                 (df['levelKey'].str.contains(parent_level_key, na=False))
                    parent_rows = df[parent_mask]
                    if parent_rows.empty:
                        parent_key = parent_level_key
                        telios_parent = f"{self.country_code}-{state_code}-001"
                    else:
                        parent_row = parent_rows.iloc[0]
                        parent_key = parent_row['levelKey']
                        parent_pos = level_key_to_pos.get((2, parent_key), 0)
                        telios_parent = telios_keys[parent_pos] if parent_pos < len(telios_keys) else f"{self.country_code}-{state_code}-001"
                else:
                    parent_key = df.iloc[parent_pos]['levelKey']
                    telios_parent = telios_keys[parent_pos] if parent_pos < len(telios_keys) else f"{self.country_code}-{state_code}-001"
                
                # FIXED: Use district's telios key as counter key for blocks
                counter_key = telios_parent
                
                if counter_key not in block_counters:
                    block_counters[counter_key] = 1
                seq_num = block_counters[counter_key]
                block_counters[counter_key] += 1
                
                seq = f"{seq_num:04d}"
                telios_key = f"{telios_parent}-{seq}"
                
            elif level == 4:
                # Village
                state_code = self.state_mapping.get(state, '01')
                
                # Find parent block
                parent_pos = level_key_to_pos.get((3, parent_level_key))
                if parent_pos is None:
                    # Try fuzzy match
                    parent_mask = (df['countryLevelId'] == 3) & (df['state'] == state) & \
                                 (df['levelKey'].str.contains(parent_level_key, na=False))
                    parent_rows = df[parent_mask]
                    if parent_rows.empty:
                        parent_key = parent_level_key
                        telios_parent = f"{self.country_code}-{state_code}-001-0001"
                    else:
                        parent_row = parent_rows.iloc[0]
                        parent_key = parent_row['levelKey']
                        parent_pos = level_key_to_pos.get((3, parent_key), 0)
                        telios_parent = telios_keys[parent_pos] if parent_pos < len(telios_keys) else f"{self.country_code}-{state_code}-001-0001"
                else:
                    parent_key = df.iloc[parent_pos]['levelKey']
                    telios_parent = telios_keys[parent_pos] if parent_pos < len(telios_keys) else f"{self.country_code}-{state_code}-001-0001"
                
                # FIXED: Use block's telios key as counter key for villages
                counter_key = telios_parent
                
                if counter_key not in village_counters:
                    village_counters[counter_key] = 1
                seq_num = village_counters[counter_key]
                village_counters[counter_key] += 1
                
                seq = f"{seq_num:06d}"
                telios_key = f"{telios_parent}-{seq}"
                
            else:
                telios_key = level_key
                parent_key = parent_level_key
                telios_parent = ''
            
            telios_keys.append(telios_key)
            parent_keys.append(parent_key)
            telios_parent_keys.append(telios_parent)
        
        # Assign to dataframe
        df['telioslevelKey'] = telios_keys
        df['parentlevelKey'] = parent_keys
        df['teliosparentlevelKey'] = telios_parent_keys
        
        # Calculate count of children
        df['countnextLevel'] = df.apply(lambda row: self._count_children(row, df), axis=1)
        
        self.transformed_data = df
        print(f"✅ Transformed {len(df)} records for {self.config.country_name}")
        return self
    
    def _count_children(self, row, df) -> int:
        """Count direct children for this unit."""
        if row['countryLevelId'] >= self.config.max_level:
            return 0
        
        child_level = row['countryLevelId'] + 1
        
        # Count children by matching parentlevelKey
        children = df[
            (df['parentlevelKey'] == row['levelKey']) & 
            (df['countryLevelId'] == child_level)
        ]
        return len(children)
    
    def finalize(self) -> 'GeoSpatialPipeline':
        """
        Finalize data with sequential IDs and parent relationships.
        Uses GLOBAL continuous unitid sequencing across ALL countries.
        """
        print(f"🏁 Finalizing data for {self.config.country_name} with GLOBAL sequential IDs...")
        
        if self.transformed_data is None:
            raise ValueError("No transformed data. Run transform() first.")
        
        df = self.transformed_data.copy()
        
        # Sort by level and telioslevelKey for consistent ordering
        df = df.sort_values(['countryLevelId', 'telioslevelKey']).reset_index(drop=True)
        
        # Get the starting global ID for this country
        self.country_start_id = self.__class__._global_unit_id_counter
        record_count = len(df)
        
        # Assign sequential global unitids starting from current global counter
        df['unitid'] = range(self.country_start_id, self.country_start_id + record_count)
        
        # Update the global counter
        self.__class__._global_unit_id_counter += record_count
        self.country_end_id = self.__class__._global_unit_id_counter - 1
        
        # Create mapping from telioslevelKey to unitid for parent lookup
        telios_to_unitid = dict(zip(df['telioslevelKey'], df['unitid']))
        
        # Assign parentid based on teliosparentlevelKey
        df['parentid'] = df['teliosparentlevelKey'].map(telios_to_unitid)
        
        # Country (Level 0) is its own parent
        country_mask = df['countryLevelId'] == 0
        df.loc[country_mask, 'parentid'] = df.loc[country_mask, 'unitid']
        
        # Fill any missing parentid with 0
        df['parentid'] = df['parentid'].fillna(0).astype(int)
        
        # Add country_id for database (using staging DB ID)
        df['country_id'] = self.db_country_id
        
        self.final_data = df
        
        print(f"✅ Finalized {len(df)} records for {self.config.country_name}")
        print(f"   Global UnitID range: {self.country_start_id} to {self.country_end_id}")
        print(f"   Staging DB ID: {self.db_country_id}")
        
        # Debug: Show sample of generated keys
        print(f"\n📋 Sample TeliosLevelKeys for {self.config.country_name}:")
        for level in [0, 1, 2, 3, 4]:
            sample = df[df['countryLevelId'] == level].head(2)
            for _, row in sample.iterrows():
                print(f"   Level {level}: {row['telioslevelKey']:<35} {row['unit'][:30]} (ID: {row['unitid']})")
        
        # Validate ID consistency
        self._validate_ids()
        
        return self
    
    def _validate_ids(self):
        """Validate ID consistency across the dataset."""
        df = self.final_data
        
        # Check for duplicate unitids within this country (should be none with global counter)
        if df['unitid'].duplicated().any():
            raise ValueError(f"Duplicate unitids found within {self.config.country_name}!")
        
        # Check for duplicate telioslevelKeys
        if df['telioslevelKey'].duplicated().any():
            dups = df[df['telioslevelKey'].duplicated()]['telioslevelKey'].unique()
            raise ValueError(f"Duplicate telioslevelKeys found in {self.config.country_name}: {dups[:5]}")
        
        # Check that all parentids exist (except country)
        non_country = df[df['countryLevelId'] > 0]
        missing_parents = non_country[~non_country['parentid'].isin(df['unitid'])]
        
        if not missing_parents.empty:
            print(f"\n⚠️  Warning: {len(missing_parents)} records with missing parent IDs in {self.config.country_name}")
            print("Setting orphan parentids to 0")
            df.loc[missing_parents.index, 'parentid'] = 0
        
        print(f"✅ ID validation passed for {self.config.country_name}")
    
    def get_country_data(self) -> pd.DataFrame:
        """Return the final data for this country."""
        return self.final_data.copy() if self.final_data is not None else None


# ============ GLOBAL PROCESSING FUNCTIONS ============

class GlobalGeoSpatialProcessor:
    """
    Global processor that handles multiple countries with continuous ID sequencing.
    All output files are consolidated in a single 'Finale' folder.
    """
    
    def __init__(self, output_base: str = "Finale"):
        self.output_base = Path(output_base)
        self.output_base.mkdir(parents=True, exist_ok=True)
        
        # Reset global counter at start of processing
        GeoSpatialPipeline.reset_global_counter()
        
        # Storage for all countries' data
        self.all_country_data: List[pd.DataFrame] = []
        self.processing_results: List[Dict] = []
        
    def process_country(self, country_config: dict) -> Dict:
        """Process a single country and return its data and stats."""
        print(f"\n{'='*70}")
        print(f"🏁 PROCESSING COUNTRY: {country_config['name']}")
        print(f"{'='*70}")
        
        config = ProcessingConfig(
            country_name=country_config['name'],
            country_id=country_config.get('countryId', 1),
            base_path=country_config['base_path'],
            states=country_config['states'],
            max_level=country_config.get('max_level', 4)
        )
        
        pipeline = GeoSpatialPipeline(config)
        
        # Run pipeline for this country
        pipeline.extract().transform().finalize()
        
        # Get the country data
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
            'max_level': config.max_level
        }
        
        self.processing_results.append(result)
        return result
    
    def consolidate_outputs(self):
        """Consolidate all countries' data into single output files in Finale folder."""
        if not self.all_country_data:
            print("❌ No data to consolidate")
            return
        
        print(f"\n{'='*70}")
        print(f"📊 CONSOLIDATING ALL COUNTRIES INTO FINALE FOLDER")
        print(f"{'='*70}")
        
        # Combine all country data
        final_df = pd.concat(self.all_country_data, ignore_index=True)
        
        # Sort by unitid to ensure global order
        final_df = final_df.sort_values('unitid').reset_index(drop=True)
        
        print(f"✅ Consolidated {len(final_df)} total records from {len(self.all_country_data)} countries")
        print(f"   Global UnitID range: {final_df['unitid'].min()} to {final_df['unitid'].max()}")
        
        # ============ GENERATE CONSOLIDATED OUTPUT FILES ============
        
        # 1. Unit.csv - Core unit table
        unit_df = final_df[[
            'unitid', 'parentid', 'country_id', 'country', 'country_code',
            'levelDescription', 'countryLevelId', 'levelKey', 'telioslevelKey', 
            'countnextLevel', 'unit', 'parentlevelKey', 'teliosparentlevelKey'
        ]].copy()
        
        unit_csv = self.output_base / "Unit.csv"
        unit_xlsx = self.output_base / "Unit.xlsx"
        unit_df.to_csv(unit_csv, index=False)
        unit_df.to_excel(unit_xlsx, index=False, sheet_name='Unit')
        print(f"   ✅ Unit: {len(unit_df)} records -> {unit_csv.name}")
        
        # 2. PSQL_Geo.csv - Spatial data with geometry
        psql_geo_df = final_df[[
            'unitid', 'parentid', 'country_id', 'countryLevelId',
            'levelKey', 'telioslevelKey', 'countnextLevel', 'unit', 'geometry'
        ]].copy()
        
        psql_geo_df.columns = [
            'unitid', 'parent_id', 'country_id', 'levelid',
            'levelkey', 'tellevelkey', 'countnextlevel', 'unit', 'geometry'
        ]
        
        psql_csv = self.output_base / "PSQL_Geo.csv"
        psql_xlsx = self.output_base / "PSQL_Geo.xlsx"
        psql_geo_df.to_csv(psql_csv, index=False)
        psql_geo_df.to_excel(psql_xlsx, index=False, sheet_name='PSQL_Geo')
        print(f"   ✅ PSQL_Geo: {len(psql_geo_df)} records -> {psql_csv.name}")
        
        # 3. GeoJSON.csv - ID to GeoJSON mapping
        geojson_df = pd.DataFrame({
            'teliosgeojson_id': final_df['unitid'],
            'geojson': final_df['geometry']
        })
        
        geojson_csv = self.output_base / "GeoJSON.csv"
        geojson_xlsx = self.output_base / "GeoJSON.xlsx"
        geojson_df.to_csv(geojson_csv, index=False)
        geojson_df.to_excel(geojson_xlsx, index=False, sheet_name='GeoJSON')
        print(f"   ✅ GeoJSON: {len(geojson_df)} records -> {geojson_csv.name}")
        
        # 4. teliosgeojson.csv - Database format (8 columns)
        telios_df = pd.DataFrame({
            'unitid': final_df['unitid'],
            'parent_id': final_df['parentid'],
            'country_id': final_df['country_id'],
            'levelid': final_df['countryLevelId'],
            'levelkey': final_df['levelKey'],
            'tellevelkey': final_df['telioslevelKey'],
            'countnextlevel': final_df['countnextLevel'],
            'unit': final_df['unit']
        })
        
        telios_csv = self.output_base / "teliosgeojson.csv"
        telios_xlsx = self.output_base / "teliosgeojson.xlsx"
        telios_df.to_csv(telios_csv, index=False)
        telios_df.to_excel(telios_xlsx, index=False, sheet_name='teliosgeojson')
        print(f"   ✅ teliosgeojson: {len(telios_df)} records -> {telios_csv.name}")
        
        # 5. teliosgeojsondata.csv - Database format (2 columns)
        telios_data_df = pd.DataFrame({
            'teliosgeojson_id': final_df['unitid'],
            'geojson': final_df['geometry']
        })
        
        telios_data_csv = self.output_base / "teliosgeojsondata.csv"
        telios_data_xlsx = self.output_base / "teliosgeojsondata.xlsx"
        telios_data_df.to_csv(telios_data_csv, index=False)
        telios_data_df.to_excel(telios_data_xlsx, index=False, sheet_name='teliosgeojsondata')
        print(f"   ✅ teliosgeojsondata: {len(telios_data_df)} records -> {telios_data_csv.name}")
        
        # Generate global processing report
        self._generate_global_report(final_df)
        
        return final_df
    
    def _generate_global_report(self, final_df: pd.DataFrame):
        """Generate comprehensive global processing report."""
        report_file = self.output_base / "global_processing_report.txt"
        
        with open(report_file, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("🌍 GLOBAL GEOSPATIAL PROCESSING REPORT\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Output Directory: {self.output_base.absolute()}\n\n")
            
            f.write("=" * 80 + "\n")
            f.write("📊 COUNTRIES PROCESSED\n")
            f.write("=" * 80 + "\n")
            f.write(f"{'Country':<20} {'Code':<6} {'DB ID':<8} {'Records':<12} {'UnitID Range':<20} {'States':<8}\n")
            f.write("-" * 80 + "\n")
            
            total_records = 0
            for result in self.processing_results:
                f.write(f"{result['country']:<20} {result['country_code']:<6} "
                       f"{result['db_country_id']:<8} {result['record_count']:<12,} "
                       f"{result['start_id']}-{result['end_id']:<18} {result['states_processed']:<8}\n")
                total_records += result['record_count']
            
            f.write("-" * 80 + "\n")
            f.write(f"{'TOTAL':<20} {'':<6} {'':<8} {total_records:<12,} "
                   f"{final_df['unitid'].min()}-{final_df['unitid'].max():<18} "
                   f"{len(self.processing_results):<8}\n")
            f.write("=" * 80 + "\n\n")
            
            f.write("=" * 80 + "\n")
            f.write("📈 GLOBAL STATISTICS\n")
            f.write("=" * 80 + "\n")
            f.write(f"Total Countries: {len(self.processing_results)}\n")
            f.write(f"Total Records: {total_records:,}\n")
            f.write(f"Global UnitID Range: {final_df['unitid'].min()} - {final_df['unitid'].max()}\n")
            f.write(f"Global UnitID Span: {final_df['unitid'].max() - final_df['unitid'].min() + 1:,}\n\n")
            
            f.write("📋 LEVEL DISTRIBUTION (Global):\n")
            f.write("-" * 40 + "\n")
            for level in sorted(final_df['countryLevelId'].unique()):
                count = len(final_df[final_df['countryLevelId'] == level])
                desc = GeoSpatialPipeline.LEVEL_DESCRIPTIONS.get(level, f'Level {level}')
                percentage = (count / total_records) * 100
                f.write(f"  {desc:<10} (Level {level}): {count:>10,} records ({percentage:>5.1f}%)\n")
            
            f.write("\n" + "=" * 80 + "\n")
            f.write("✅ GLOBAL PROCESSING COMPLETED SUCCESSFULLY\n")
            f.write("=" * 80 + "\n")
            f.write(f"\nOutput Files saved in: {self.output_base.absolute()}\n")
            f.write("  1. Unit.csv / Unit.xlsx\n")
            f.write("  2. PSQL_Geo.csv / PSQL_Geo.xlsx\n")
            f.write("  3. GeoJSON.csv / GeoJSON.xlsx\n")
            f.write("  4. teliosgeojson.csv / teliosgeojson.xlsx\n")
            f.write("  5. teliosgeojsondata.csv / teliosgeojsondata.xlsx\n")
            f.write("  6. global_processing_report.txt\n")
            f.write("=" * 80 + "\n")
        
        print(f"\n📄 Global report generated: {report_file}")