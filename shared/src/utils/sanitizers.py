"""
Utility functions for sanitizing filenames and strings.
"""

import re

def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing or replacing invalid characters.
    """
    if not filename:
        return ""
    filename = str(filename)
    filename = filename.replace(' ', '_')
    filename = re.sub(r'[^a-zA-Z0-9_-]', '', filename)
    return filename