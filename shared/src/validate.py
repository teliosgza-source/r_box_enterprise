# === CODE FOR src/validate.py ===
# src/validate.py
"""
Validation script to ensure ID consistency across all output files.
Run after processing to verify data integrity.
"""

import pandas as pd
import argparse
from pathlib import Path
from typing import Dict, List, Tuple

class IDValidator:
    """Validates ID consistency across generated output files."""

    def __init__(self, country_name: str, output_dir: str):
        self.country_name = country_name
        self.output_dir = Path(output_dir) / country_name.replace(' ', '_')
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def load_files(self) -> Dict[str, pd.DataFrame]:
        """Load all output files for validation."""
        files = {}

        file_mapping = {
            'unit': 'Unit.csv',
            'psql_geo': 'PSQL_Geo.csv',
            'geojson': 'GeoJSON.csv',
            'teliosgeojson': 'teliosgeojson.csv',
            'teliosgeojsondata': 'teliosgeojsondata.csv'
        }

        for key, filename in file_mapping.items():
            file_path = self.output_dir / filename
            if file_path.exists():
                files[key] = pd.read_csv(file_path)
                print(f"✅ Loaded {filename}: {len(files[key])} records")
            else:
                self.errors.append(f"Missing file: {filename}")

        return files

    def validate_unitid_consistency(self, files: Dict[str, pd.DataFrame]) -> bool:
        """Check that unitid values are consistent across files."""
        if 'unit' not in files:
            return False

        unit_df = files['unit']

        # Check 1: No duplicate unitids in Unit.csv
        duplicates = unit_df['unitid'].duplicated().sum()
        if duplicates > 0:
            self.errors.append(f"Found {duplicates} duplicate unitid values in Unit.csv")
            return False

        # Check 2: Sequential IDs starting from 1
        expected_ids = set(range(1, len(unit_df) + 1))
        actual_ids = set(unit_df['unitid'].values)

        if expected_ids != actual_ids:
            missing = expected_ids - actual_ids
            extra = actual_ids - expected_ids
            if missing:
                self.errors.append(f"Missing unitid values: {sorted(missing)}")
            if extra:
                self.errors.append(f"Unexpected unitid values: {sorted(extra)}")
            return False

        print("✅ UnitID consistency passed")
        return True

    def validate_parentid_references(self, files: Dict[str, pd.DataFrame]) -> bool:
        """Check that all parentid values reference existing unitids."""
        if 'unit' not in files:
            return False

        unit_df = files['unit']
        valid_ids = set(unit_df['unitid'].values)

        # Check parentid references
        parent_ids = set(unit_df['parentid'].values)
        invalid_parents = parent_ids - valid_ids

        if invalid_parents:
            self.errors.append(f"Invalid parentid references: {sorted(invalid_parents)}")
            return False

        # Check country (level 0) is its own parent
        country = unit_df[unit_df['countryLevelId'] == 0]
        if not country.empty:
            country_unitid = country.iloc[0]['unitid']
            country_parentid = country.iloc[0]['parentid']
            if country_unitid != country_parentid:
                self.errors.append(f"Country parentid ({country_parentid}) should equal unitid ({country_unitid})")
                return False

        print("✅ ParentID references passed")
        return True

    def validate_geojson_id_mapping(self, files: Dict[str, pd.DataFrame]) -> bool:
        """Check that teliosgeojson_id matches unitid across files."""
        if 'unit' not in files or 'geojson' not in files:
            return False

        unit_ids = set(files['unit']['unitid'].values)

        # Check GeoJSON.csv
        geojson_ids = set(files['geojson']['teliosgeojson_id'].values)
        if unit_ids != geojson_ids:
            missing = unit_ids - geojson_ids
            extra = geojson_ids - unit_ids
            if missing:
                self.errors.append(f"GeoJSON.csv missing IDs: {sorted(missing)}")
            if extra:
                self.errors.append(f"GeoJSON.csv extra IDs: {sorted(extra)}")
            return False

        # Check teliosgeojsondata.csv
        if 'teliosgeojsondata' in files:
            data_ids = set(files['teliosgeojsondata']['teliosgeojson_id'].values)
            if unit_ids != data_ids:
                missing = unit_ids - data_ids
                extra = data_ids - unit_ids
                if missing:
                    self.errors.append(f"teliosgeojsondata.csv missing IDs: {sorted(missing)}")
                if extra:
                    self.errors.append(f"teliosgeojsondata.csv extra IDs: {sorted(extra)}")
                return False

        print("✅ GeoJSON ID mapping passed")
        return True

    def validate_hierarchy_integrity(self, files: Dict[str, pd.DataFrame]) -> bool:
        """Check parent-child relationships are consistent."""
        if 'unit' not in files:
            return False

        unit_df = files['unit']

        # Build parent-child mapping
        issues = []
        for _, row in unit_df.iterrows():
            level = row['countryLevelId']
            unitid = row['unitid']
            parentid = row['parentid']
            telios_key = row['telioslevelKey']
            telios_parent = row['teliosparentlevelKey']

            if level == 0:
                # Country should be its own parent
                if unitid != parentid:
                    issues.append(f"Country {unitid} should be its own parent")
                continue

            # Find parent
            parent = unit_df[unit_df['unitid'] == parentid]
            if parent.empty:
                issues.append(f"Unit {unitid} (level {level}) has missing parent {parentid}")
                continue

            parent_row = parent.iloc[0]

            # Check parent level is one less
            if parent_row['countryLevelId'] != level - 1:
                issues.append(f"Unit {unitid} (level {level}) parent {parentid} is level {parent_row['countryLevelId']}")

            # Check telios parent key matches
            if parent_row['telioslevelKey'] != telios_parent:
                issues.append(f"Unit {unitid} telios parent mismatch: {telios_parent} vs {parent_row['telioslevelKey']}")

        if issues:
            for issue in issues[:10]:  # Show first 10
                self.errors.append(issue)
            if len(issues) > 10:
                self.errors.append(f"... and {len(issues) - 10} more hierarchy issues")
            return False

        print("✅ Hierarchy integrity passed")
        return True

    def validate_countnextlevel(self, files: Dict[str, pd.DataFrame]) -> bool:
        """Verify countnextLevel matches actual child count."""
        if 'unit' not in files:
            return False

        unit_df = files['unit']

        # Calculate actual child counts
        child_counts = unit_df.groupby('parentid').size().to_dict()

        mismatches = []
        for _, row in unit_df.iterrows():
            unitid = row['unitid']
            level = row['countryLevelId']
            reported = row['countnextLevel']

            # Skip leaf nodes (villages)
            if level >= 4:
                if reported != 0 and pd.notna(reported):
                    mismatches.append(f"Leaf node {unitid} should have countnextLevel=0, got {reported}")
                continue

            actual = child_counts.get(unitid, 0)
            if reported != actual:
                mismatches.append(f"Unit {unitid}: reported {reported} children, actual {actual}")

        if mismatches:
            for mismatch in mismatches[:10]:
                self.warnings.append(mismatch)
            if len(mismatches) > 10:
                self.warnings.append(f"... and {len(mismatches) - 10} more count mismatches")
            print("⚠️  countnextLevel warnings (non-critical)")
            return True  # Warnings don't fail validation

        print("✅ countnextLevel validation passed")
        return True

    def run_all_validations(self) -> bool:
        """Run all validation checks."""
        print(f"\n🔍 Validating {self.country_name}...")
        print("=" * 60)

        files = self.load_files()
        if not files:
            print("❌ No files to validate")
            return False

        checks = [
            ("UnitID Consistency", self.validate_unitid_consistency),
            ("ParentID References", self.validate_parentid_references),
            ("GeoJSON ID Mapping", self.validate_geojson_id_mapping),
            ("Hierarchy Integrity", self.validate_hierarchy_integrity),
            ("CountNextLevel", self.validate_countnextlevel),
        ]

        all_passed = True
        for name, check_func in checks:
            print(f"\n📋 {name}...")
            if not check_func(files):
                all_passed = False

        # Report results
        print("\n" + "=" * 60)
        if all_passed and not self.errors:
            print("✅ ALL VALIDATIONS PASSED")
        else:
            print("❌ VALIDATION FAILED")

        if self.errors:
            print(f"\nErrors ({len(self.errors)}):")
            for error in self.errors:
                print(f"  ❌ {error}")

        if self.warnings:
            print(f"\nWarnings ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  ⚠️  {warning}")

        print("=" * 60)
        return all_passed and not self.errors

def main():
    parser = argparse.ArgumentParser(description='Validate output file ID consistency')
    parser.add_argument('--country', type=str, required=True, help='Country name to validate')
    parser.add_argument('--output-dir', type=str, default='output', help='Output directory')

    args = parser.parse_args()

    validator = IDValidator(args.country, args.output_dir)
    succes<response clipped><NOTE>Result is longer than **10000 characters**, will be **truncated**.</NOTE>