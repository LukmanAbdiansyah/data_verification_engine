import openpyxl
import pandas
import io
import re
import csv
from pathlib import Path
from typing import Tuple, List, Dict, Optional

PROGRESS_ALIASES = [
    'progress', 'deliverable', 'deliverable name', 'deliverable item', 'item', 
    'description', 'file', 'filename', 'file name', 'name', 'nama', 'nama file',
    'title', 'judul', 'item deliverable', 'data'
]

FORMAT_ALIASES = [
    'format', 'expected format', 'file format', 'data format', 'output format', 
    'fmt', 'extension', 'ext', 'tipe', 'type', 'format file'
]

INDEX_ALIASES = ['no', 'no.', 'nomor', 'number', '#', 'id', 'idx', 'index', 'item no', 'item #']


def _detect_delimiter(text: str) -> str:
    """Detect the most likely delimiter in the text (tab, comma, semicolon, pipe)."""
    first_few_lines = [l for l in text.strip().split('\n') if l.strip()][:3]
    if not first_few_lines:
        return '\t'
    
    sample = '\n'.join(first_few_lines)
    candidates = ['\t', ',', ';', '|']
    counts = {c: sample.count(c) for c in candidates}
    
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else '\t'


def _detect_columns(headers: List[str]) -> Dict[str, str | None]:
    """Case-insensitive column detection with smart fallback for non-standard headers."""
    result: Dict[str, str | None] = {'progress': None, 'format': None}
    normalized = {h: h.strip().lower() for h in headers}

    # Pass 1: Exact alias match
    for header, norm in normalized.items():
        if norm in PROGRESS_ALIASES and result['progress'] is None:
            result['progress'] = header
        elif norm in FORMAT_ALIASES and result['format'] is None:
            result['format'] = header

    # Pass 2: Substring matching if still missing
    if result['progress'] is None:
        for header, norm in normalized.items():
            if header != result['format'] and any(alias in norm for alias in ['deliverable', 'progress', 'file', 'item', 'desc']):
                if norm not in INDEX_ALIASES:
                    result['progress'] = header
                    break

    if result['format'] is None:
        for header, norm in normalized.items():
            if header != result['progress'] and any(alias in norm for alias in ['format', 'fmt', 'ext']):
                result['format'] = header
                break

    # Pass 3: Smart position-based fallback
    # Exclude index columns like "No.", "ID"
    non_index_headers = [h for h in headers if normalized[h] not in INDEX_ALIASES]

    if result['progress'] is None and non_index_headers:
        # If format is already known, pick the first other non-index header
        candidates = [h for h in non_index_headers if h != result['format']]
        if candidates:
            result['progress'] = candidates[0]

    if result['format'] is None and len(non_index_headers) >= 2:
        # If progress is known, pick second non-index header for format
        candidates = [h for h in non_index_headers if h != result['progress']]
        if candidates:
            result['format'] = candidates[0]

    return result


def parse_xlsx(file_path: str) -> Tuple[List[Dict[str, str]], Dict[str, str | None], List[str]]:
    """Parse XLSX file. Returns (rows, column_mapping, all_headers)"""
    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    ws = wb.active
    rows_data = []
    headers = []
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            headers = [str(c).strip() if c else f'Column_{j}' for j, c in enumerate(row)]
            continue
        row_dict = {}
        for j, cell in enumerate(row):
            if j < len(headers):
                row_dict[headers[j]] = str(cell).strip() if cell is not None else ''
        if any(v.strip() for v in row_dict.values()):
            rows_data.append(row_dict)
    wb.close()
    
    mapping = _detect_columns(headers)
    parsed = []
    for row in rows_data:
        progress = row.get(mapping['progress'], '') if mapping['progress'] else ''
        fmt = row.get(mapping['format'], '') if mapping['format'] else ''
        if progress.strip() or fmt.strip():
            parsed.append({'progress': progress.strip(), 'format_str': fmt.strip()})
    return parsed, mapping, headers


def parse_csv(file_path: str) -> Tuple[List[Dict[str, str]], Dict[str, str | None], List[str]]:
    """Parse CSV file similarly with delimiter auto-detection."""
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        sample = f.read(4096)
        delimiter = _detect_delimiter(sample)
    
    df = pandas.read_csv(file_path, sep=delimiter, dtype=str, keep_default_na=False)
    headers = [str(c).strip() for c in df.columns]
    mapping = _detect_columns(headers)
    parsed = []
    for _, row in df.iterrows():
        progress = str(row.get(mapping['progress'], '')).strip() if mapping['progress'] else ''
        fmt = str(row.get(mapping['format'], '')).strip() if mapping['format'] else ''
        if progress or fmt:
            parsed.append({'progress': progress, 'format_str': fmt})
    return parsed, mapping, headers


def parse_paste(text: str) -> Tuple[List[Dict[str, str]], Dict[str, str | None], List[str]]:
    """Parse pasted text supporting tab, comma, semicolon, or pipe delimiters."""
    clean_text = text.strip()
    if not clean_text:
        return [], {'progress': None, 'format': None}, []

    delimiter = _detect_delimiter(clean_text)
    
    reader = csv.reader(io.StringIO(clean_text), delimiter=delimiter)
    raw_rows = [[col.strip() for col in row] for row in reader if any(c.strip() for c in row)]
    
    if not raw_rows:
        return [], {'progress': None, 'format': None}, []

    headers = raw_rows[0]
    mapping = _detect_columns(headers)
    
    # If first row looks like data rather than headers (e.g. no known headers detected and line 0 has data)
    # Check if first row is actually a data row without headers
    is_header_row = (mapping['progress'] is not None or mapping['format'] is not None)
    
    start_row = 1 if is_header_row else 0
    if not is_header_row:
        # Fallback: assume column 0 is No (if numeric), column 1 is Progress, column 2 is Format
        # or column 0 is Progress, column 1 is Format
        if len(headers) >= 2:
            if headers[0].isdigit() and len(headers) >= 3:
                mapping = {'progress': 'Col_1', 'format': 'Col_2'}
                headers = ['Col_0', 'Col_1', 'Col_2']
            else:
                mapping = {'progress': 'Col_0', 'format': 'Col_1'}
                headers = [f'Col_{i}' for i in range(len(headers))]

    parsed = []
    for row in raw_rows[start_row:]:
        if not row:
            continue
        progress = ''
        fmt = ''
        
        if is_header_row:
            for i, h in enumerate(headers):
                val = row[i].strip() if i < len(row) else ''
                if mapping['progress'] and h == mapping['progress']:
                    progress = val
                elif mapping['format'] and h == mapping['format']:
                    fmt = val
        else:
            # Positional mapping
            if mapping['progress'] == 'Col_1' and len(row) >= 3:
                progress = row[1]
                fmt = row[2]
            elif len(row) >= 2:
                progress = row[0]
                fmt = row[1]
            elif len(row) == 1:
                progress = row[0]
                fmt = 'OTHER'

        if progress or fmt:
            parsed.append({'progress': progress, 'format_str': fmt})

    return parsed, mapping, headers
