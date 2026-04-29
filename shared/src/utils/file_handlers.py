"""
File handling utilities for I/O operations.
"""

import os
import pandas as pd
from pathlib import Path
from typing import Union

def ensure_directory(directory: Union[str, Path]) -> Path:
    """Ensure directory exists, create if it doesn't."""
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    return path

def save_dataframe(df: pd.DataFrame, directory: Union[str, Path], 
                   filename: str, sheet_name: str = None) -> tuple:
    """
    Save DataFrame to both CSV and Excel formats.
    """
    dir_path = ensure_directory(directory)
    csv_path = dir_path / f"{filename}.csv"
    df.to_csv(csv_path, index=False)
    excel_path = dir_path / f"{filename}.xlsx"
    if sheet_name is None:
        sheet_name = filename[:31]
    df.to_excel(excel_path, index=False, sheet_name=sheet_name)
    return csv_path, excel_path

def get_file_size(path: Union[str, Path]) -> int:
    """Get file size in bytes."""
    return Path(path).stat().st_size

def save_outputs(df: pd.DataFrame, output_path: str, level_name: str):
    """
    Save processor outputs to CSV and Excel files.
    Used by level processors.
    """
    if df is None or df.empty:
        print(f"   ⚠️ No data to save for {level_name}")
        return
        
    save_dataframe(df, output_path, level_name, sheet_name=level_name)
    print(f"   ✅ Saved {level_name}: {len(df)} records")