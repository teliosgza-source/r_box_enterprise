"""
Simplified entry point for geospatial data processing.
Usage: python src/main.py --data-root /path/to/data
Auto-detects Map vs Mapless data and saves to appropriate Finale_Map or Finale_Mapless folder.
Uses staging database IDs from config file.
"""

import argparse
import yaml
import sys
from pathlib import Path

import sys
from pathlib import Path
src_path = Path(__file__).parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Add parent directory to path for direct execution
sys.path.insert(0, str(Path(__file__).parent.parent))

# Use absolute imports
from src.pipeline import GlobalGeoSpatialProcessor
from src.utils.country_mapper import CountryMapper

# Base output path for processed data
PROCESSED_DATA_PATH = Path("/home/linson/workspace/dev/data/processed/Telios")

def load_config(config_path: str) -> dict:
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def auto_discover_config(data_root: str, country_mapper: CountryMapper) -> dict:
    """
    Auto-discover country structure from data directory.
    Uses country_mapper to get staging DB IDs.
    """
    root = Path(data_root)
    countries = []

    # Look for continent directories
    for continent_dir in root.iterdir():
        if not continent_dir.is_dir():
            continue

        # Look for country directories
        for country_dir in continent_dir.iterdir():
            if not country_dir.is_dir():
                continue

            # Check for Level0.geojson
            if (country_dir / "Level0.geojson").exists():
                # Get staging DB ID from mapper
                country_name = country_dir.name
                db_country_id, country_iso = country_mapper.get_country_info(country_name)
                
                # Discover states
                states = []
                for state_dir in country_dir.iterdir():
                    if state_dir.is_dir() and (state_dir / "Level1.geojson").exists():
                        states.append(state_dir.name)

                if states:
                    # Determine max level
                    max_level = 1
                    sample_state = country_dir / states[0]
                    for level in range(2, 5):
                        if (sample_state / f"Level{level}").exists():
                            max_level = level

                    country_config = {
                        'name': country_name,
                        'base_path': str(country_dir),
                        'countryId': db_country_id,  # Use staging DB ID
                        'country_iso': country_iso,
                        'max_level': max_level,
                        'states': sorted(states)
                    }
                    
                    countries.append(country_config)
                    
                    # Show if using staging ID or fallback
                    if db_country_id == 0:
                        print(f"   ⚠️ Discovered: {country_name} (NO STAGING ID - using fallback {country_config['countryId']})")
                    else:
                        print(f"   ✅ Discovered: {country_name} (Staging ID: {db_country_id}, ISO: {country_iso})")

    return {'countries': countries}

def detect_data_type(data_root: str) -> str:
    """Detect whether the data is Map or Mapless by checking for geometry in Level2 files."""
    root = Path(data_root)
    
    # Look for first Level2 directory with geojson files
    for continent_dir in root.iterdir():
        if not continent_dir.is_dir():
            continue
            
        for country_dir in continent_dir.iterdir():
            if not country_dir.is_dir():
                continue
                
            # Check for Level0.geojson (valid country)
            if not (country_dir / "Level0.geojson").exists():
                continue
                
            # Look for first state with Level2 directory
            for state_dir in country_dir.iterdir():
                if not state_dir.is_dir():
                    continue
                    
                level2_dir = state_dir / "Level2"
                if not level2_dir.exists():
                    continue
                    
                # Check first Level2 geojson file for geometry
                level2_files = list(level2_dir.glob("*.geojson"))
                if not level2_files:
                    continue
                    
                try:
                    # Read first file and check for geometry
                    import geopandas as gpd
                    gdf = gpd.read_file(str(level2_files[0]))
                    
                    # Check if any feature has non-null geometry
                    for _, feature in gdf.iterrows():
                        if feature.geometry is not None and not feature.geometry.is_empty:
                            print(f"   📍 Detected Map data from: {level2_files[0].name}")
                            return "Map"
                    
                    # If we get here, all geometries are None or empty
                    print(f"   📍 Detected Mapless data from: {level2_files[0].name}")
                    return "Mapless"
                    
                except Exception as e:
                    print(f"   ⚠️ Error detecting data type: {e}")
                    continue
    
    # Default to Mapless if can't detect
    print("   ⚠️ Could not detect data type, defaulting to Mapless")
    return "Mapless"

def main():
    parser = argparse.ArgumentParser(description='Geospatial Data Processor - Global Consolidation')
    parser.add_argument('--data-root', type=str, required=True, help='Root data directory')
    parser.add_argument('--config', type=str, help='Config file path')
    parser.add_argument('--output', type=str, default=None, 
                       help='Output directory (optional - auto-detects Map/Mapless if not specified)')
    parser.add_argument('--country-config', type=str, default=None,
                       help='Path to country_ids.yaml config file (optional)')
    parser.add_argument('--processed-path', type=str, default=None,
                       help='Base path for processed data (default: /home/linson/workspace/dev/data/processed/Telios)')

    args = parser.parse_args()

    # Initialize country mapper
    country_mapper = CountryMapper(args.country_config)

    # Load configuration
    if args.config:
        config = load_config(args.config)
        print(f"📁 Loading config from: {args.config}")
    elif args.data_root:
        print(f"🔍 Auto-discovering countries in: {args.data_root}")
        config = auto_discover_config(args.data_root, country_mapper)
    else:
        print("❌ Error: Provide either --data-root or --config")
        sys.exit(1)

    if not config['countries']:
        print("❌ No countries found to process")
        sys.exit(1)

    # Determine base output path
    if args.processed_path:
        base_output_path = Path(args.processed_path)
    else:
        base_output_path = PROCESSED_DATA_PATH
    
    # Create base output directory if it doesn't exist
    base_output_path.mkdir(parents=True, exist_ok=True)
    
    # Auto-detect Map vs Mapless if output not specified
    if args.output is None:
        data_type = detect_data_type(args.data_root)
        output_folder = base_output_path / f"Finale_{data_type}"
        print(f"\n📊 Detected data type: {data_type}")
        print(f"📁 Output will be saved to: {output_folder}/")
    else:
        output_folder = base_output_path / args.output
        print(f"\n📁 Using specified output folder: {output_folder}/")

    print(f"\n{'='*70}")
    print(f"🚀 GLOBAL PROCESSING - {len(config['countries'])} COUNTRIES")
    print(f"{'='*70}")
    print(f"{'='*70}\n")

    # Initialize global processor with the full output path
    global_processor = GlobalGeoSpatialProcessor(output_base=str(output_folder))

    # Process each country with global sequencing
    results = []
    for idx, country_config in enumerate(config['countries'], 1):
        print(f"\n{'='*70}")
        print(f"📌 Processing country {idx}/{len(config['countries'])}")
        print(f"{'='*70}")
        
        try:
            result = global_processor.process_country(country_config)
            results.append(result)
            print(f"\n✅ Completed: {result['country']}")
            print(f"   Records: {result['record_count']:,}")
            print(f"   UnitIDs: {result['start_id']} - {result['end_id']}")
            print(f"   Staging DB ID: {result['db_country_id']}")
        except Exception as e:
            print(f"\n❌ Failed {country_config['name']}: {e}")
            import traceback
            traceback.print_exc()

    # Consolidate all countries into the output folder
    print(f"\n{'='*70}")
    print(f"📊 CONSOLIDATING ALL COUNTRIES INTO {output_folder}/")
    print(f"{'='*70}")
    
    final_df = global_processor.consolidate_outputs()

    # Final Summary
    print(f"\n{'='*70}")
    print(f"🎯 GLOBAL PROCESSING COMPLETE")
    print(f"{'='*70}")
    print(f"\n📊 PROCESSING SUMMARY:")
    print(f"{'-'*70}")
    
    total_records = 0
    for result in results:
        db_id = result.get('db_country_id', 'N/A')
        print(f"   ✅ {result['country']:<20} {result['record_count']:>10,} records  "
              f"(UnitIDs: {result['start_id']:>7} - {result['end_id']:>7})  [DB ID: {db_id}]")
        total_records += result['record_count']
    
    print(f"{'-'*70}")
    print(f"   📌 TOTAL:{' ':<17} {total_records:>10,} records")
    print(f"{'='*70}")
    print(f"\n📁 All output files saved in: {output_folder}/")
    print(f"   📄 Unit.csv")
    print(f"   📄 PSQL_Geo.csv")
    print(f"   📄 GeoJSON.csv")
    print(f"   📄 teliosgeojson.csv")
    print(f"   📄 teliosgeojsondata.csv")
    print(f"   📄 global_processing_report.txt")
    print(f"\n{'='*70}")
    print(f"✅ GLOBAL PROCESSING COMPLETED SUCCESSFULLY")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()