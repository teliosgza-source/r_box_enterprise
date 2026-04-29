"""
Country mapping utility for staging database IDs.
Loads country mappings from YAML config file.
"""

import yaml
from pathlib import Path
from typing import Dict, Optional, Tuple

class CountryMapper:
    """Maps country names to staging database IDs and ISO codes."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize country mapper with config file.
        
        Args:
            config_path: Path to country_ids.yaml config file.
                        If None, looks in default locations.
        """
        self.country_map: Dict[str, Dict] = {}
        self.config_path = self._find_config(config_path)
        self._load_config()
        
    def _find_config(self, config_path: Optional[Path]) -> Path:
        """Find the country_ids.yaml config file."""
        if config_path and Path(config_path).exists():
            return Path(config_path)
        
        # Try default locations
        possible_paths = [
            Path(__file__).parent.parent.parent / "config" / "country_ids.yaml",
            Path(__file__).parent.parent / "config" / "country_ids.yaml",
            Path.cwd() / "config" / "country_ids.yaml",
            Path.cwd() / "country_ids.yaml",
        ]
        
        for path in possible_paths:
            if path.exists():
                print(f"📁 Found country config at: {path}")
                return path
        
        # If no config found, create default config
        default_config = Path(__file__).parent.parent.parent / "config" / "country_ids.yaml"
        default_config.parent.mkdir(parents=True, exist_ok=True)
        
        # Create default config with commonly used countries
        default_mapping = {
            'country_ids': {
                'India': {'id': 204, 'iso': 'IND'},
                'Indonesia': {'id': 205, 'iso': 'IDN'},
                'Bangladesh': {'id': 201, 'iso': 'BGD'},
                'Nigeria': {'id': 156, 'iso': 'NGA'},
                'Pakistan': {'id': 166, 'iso': 'PAK'},
                'Myanmar': {'id': 151, 'iso': 'MMR'},
                'Laos': {'id': 119, 'iso': 'LAO'},
                "Côte d'Ivoire": {'id': 155, 'iso': 'CIV'},
                'Uganda': {'id': 229, 'iso': 'UGA'},
            }
        }
        
        with open(default_config, 'w') as f:
            yaml.dump(default_mapping, f, default_flow_style=False)
        
        print(f"📁 Created default country config at: {default_config}")
        return default_config
    
    def _load_config(self):
        """Load country mappings from YAML config file."""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                self.country_map = config.get('country_ids', {})
            print(f"✅ Loaded {len(self.country_map)} country mappings")
        except Exception as e:
            print(f"⚠️ Error loading country config: {e}")
            self.country_map = {}
    
    def get_country_id(self, country_name: str) -> int:
        """
        Get staging database ID for a country.
        
        Args:
            country_name: Name of the country (e.g., 'India')
            
        Returns:
            Database ID if found, otherwise 0 (will be logged as warning)
        """
        # Try exact match
        if country_name in self.country_map:
            return self.country_map[country_name]['id']
        
        # Try case-insensitive match
        country_lower = country_name.lower()
        for name, data in self.country_map.items():
            if name.lower() == country_lower:
                return data['id']
        
        # Try fuzzy match (remove common variations)
        country_clean = country_name.replace("'", "").replace("-", " ").lower()
        for name, data in self.country_map.items():
            name_clean = name.replace("'", "").replace("-", " ").lower()
            if name_clean == country_clean:
                return data['id']
        
        print(f"⚠️ No staging DB ID found for country: '{country_name}'")
        return 0
    
    def get_country_iso(self, country_name: str) -> str:
        """
        Get ISO code for a country.
        
        Args:
            country_name: Name of the country
            
        Returns:
            ISO code if found, otherwise uppercase first 3 letters of country name
        """
        if country_name in self.country_map:
            return self.country_map[country_name]['iso']
        
        # Try case-insensitive match
        country_lower = country_name.lower()
        for name, data in self.country_map.items():
            if name.lower() == country_lower:
                return data['iso']
        
        # Default to first 3 letters uppercase
        return country_name[:3].upper()
    
    def get_country_info(self, country_name: str) -> Tuple[int, str]:
        """
        Get both staging DB ID and ISO code for a country.
        
        Returns:
            Tuple of (database_id, iso_code)
        """
        country_id = self.get_country_id(country_name)
        country_iso = self.get_country_iso(country_name)
        return country_id, country_iso
    
    def add_country_mapping(self, country_name: str, country_id: int, iso_code: str):
        """Add or update a country mapping."""
        self.country_map[country_name] = {'id': country_id, 'iso': iso_code}
        
    def save_config(self):
        """Save current mappings back to config file."""
        config = {'country_ids': self.country_map}
        with open(self.config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        print(f"✅ Saved {len(self.country_map)} country mappings to {self.config_path}")