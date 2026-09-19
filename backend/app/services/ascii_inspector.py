import os
from typing import Dict, Any

PREVIEW_SIZE = 65536  # 64KB

def inspect_ascii(file_path: str, max_bytes: int = PREVIEW_SIZE) -> Dict[str, Any]:
    """Read first max_bytes of a text file and extract useful info."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read(max_bytes)
        lines = content.split('\n')
        meaningful_lines = [l.strip() for l in lines if l.strip()][:50]
        likely_title = meaningful_lines[0] if meaningful_lines else ''
        file_size = os.path.getsize(file_path)
        return {
            'preview_lines': meaningful_lines,
            'likely_title': likely_title,
            'total_lines_in_preview': len(lines),
            'file_size': file_size,
            'is_text': True
        }
    except Exception as e:
        return {
            'preview_lines': [],
            'likely_title': '',
            'total_lines_in_preview': 0,
            'file_size': 0,
            'is_text': False,
            'error': str(e)
        }
