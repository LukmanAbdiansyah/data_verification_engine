import re
from typing import List, Dict, Tuple

FORMAT_CANONICAL_MAP = {
    'SEGY': 'SEG-Y', 'SEG Y': 'SEG-Y', 'SGY': 'SEG-Y', 'Seg-Y': 'SEG-Y', 'segy': 'SEG-Y', 'seg-y': 'SEG-Y',
    'SEGD': 'SEG-D', 'SEG D': 'SEG-D', 'Seg-D': 'SEG-D', 'segd': 'SEG-D',
    'MS-OFFICE': 'MS-OFFICE', 'MS OFFICE': 'MS-OFFICE', 'MSOFFICE': 'MS-OFFICE',
    'MS WORD FORMAT': 'MS-OFFICE', 'MS WORD': 'MS-OFFICE', 'WORD': 'MS-OFFICE',
    'MS Word Format': 'MS-OFFICE', 'Ms Word Format': 'MS-OFFICE',
    'MS. WORD FORMAT': 'MS-OFFICE', 'MS. Word Format': 'MS-OFFICE', 'Ms. Word Format': 'MS-OFFICE', 'ms. word format': 'MS-OFFICE',
    'TXT': 'TXT', 'txt': 'TXT',
    'ASCII': 'ASCII', 'ascii': 'ASCII', 'Ascii': 'ASCII',
    'CSV': 'CSV', 'csv': 'CSV',
    'PDF': 'PDF', 'pdf': 'PDF',
    'TIFF': 'TIFF', 'tiff': 'TIFF', 'TIF': 'TIFF', 'tif': 'TIFF',
    'XLS': 'XLS', 'xls': 'XLS',
    'XLSX': 'XLSX', 'xlsx': 'XLSX',
    'DOC': 'DOC', 'doc': 'DOC',
    'DOCX': 'DOCX', 'docx': 'DOCX',
    'PPT': 'PPT', 'ppt': 'PPT',
    'PPTX': 'PPTX', 'pptx': 'PPTX',
    'UKOOA': 'UKOOA', 'ukooa': 'UKOOA',
    'UKOOA P6/98': 'UKOOA P6/98', 'P6/98': 'UKOOA P6/98',
    'P1/90': 'P1/90',
    'P2/94': 'P2/94'
}

# Tokens to ignore when splitting formats (physical media, not digitally verifiable)
IGNORED_TOKENS = {'hard copy', 'hardcopy', 'hard copies', 'printed', 'print'}

def normalize_format(fmt: str) -> str:
    stripped = fmt.strip()
    # Check direct lookup first
    if stripped in FORMAT_CANONICAL_MAP:
        return FORMAT_CANONICAL_MAP[stripped]
    # Case-insensitive lookup
    for key, val in FORMAT_CANONICAL_MAP.items():
        if key.lower() == stripped.lower():
            return val
    return stripped

def split_formats(format_str: str) -> List[str]:
    """Split format string by comma, ampersand, or slash separators."""
    # Normalize separators: replace & and / with comma (but preserve known multi-word formats)
    s = format_str.strip()
    # Protect known multi-word format names before splitting
    protected = {
        'UKOOA P6/98': '__UKOOA_P698__',
        'P6/98': '__P698__',
        'P1/90': '__P190__',
        'P2/94': '__P294__',
        'MS. WORD FORMAT': '__MSWORD__',
        'MS. Word Format': '__MSWORD__',
        'MS WORD FORMAT': '__MSWORD__',
        'MS Word Format': '__MSWORD__',
        'MS OFFICE': '__MSOFFICE__',
    }
    for orig, placeholder in protected.items():
        s = s.replace(orig, placeholder)
    
    # Split by comma, &, or standalone /
    parts = re.split(r'[,&]|(?<!\w)/(?!\w)', s)
    
    # Restore protected tokens
    reverse_protected = {v: k for k, v in protected.items()}
    
    result = []
    for part in parts:
        p = part.strip()
        # Restore any protected tokens
        for placeholder, orig in reverse_protected.items():
            p = p.replace(placeholder, orig)
        if not p:
            continue
        # Skip physical media tokens
        if p.lower() in IGNORED_TOKENS:
            continue
        normalized = normalize_format(p)
        if normalized:
            result.append(normalized)
    return result

def detect_duplicates(requirements: List[Dict]) -> List[Tuple[int, int]]:
    duplicates = []
    seen = {}
    for i, req in enumerate(requirements):
        key = (req.get('progress', ''), tuple(sorted(req.get('formats', []))))
        if key in seen:
            duplicates.append((seen[key], i))
        else:
            seen[key] = i
    return duplicates

def normalize_requirements(rows: List[Dict]) -> List[Dict]:
    requirements = []
    for i, row in enumerate(rows):
        formats_input = row.get('formats')
        if isinstance(formats_input, list):
            fmts = [normalize_format(str(f)) for f in formats_input if str(f).strip()]
        else:
            fmts = split_formats(str(row.get('format_str', '')))

        req = {
            'req_id': row.get('req_id') or f'REQ-{i+1:03d}',
            'source_row': row.get('source_row') or (i + 1),
            'progress': str(row.get('progress', '')).strip(),
            'formats': fmts,
            'validation_note': None
        }
        requirements.append(req)
        
    dupes = detect_duplicates(requirements)
    dupe_indices = {pair[1] for pair in dupes}
    
    for i, req in enumerate(requirements):
        if not req['progress']:
            req['validation_note'] = 'Empty Progress'
        elif not req['formats']:
            req['validation_note'] = 'Empty Format'
        elif i in dupe_indices:
            req['validation_note'] = 'Duplicate Requirement'
        else:
            unknown_formats = [f for f in req['formats'] if f not in set(FORMAT_CANONICAL_MAP.values())]
            if unknown_formats:
                req['validation_note'] = f"Unknown Format: {', '.join(unknown_formats)}"
    
    return requirements
