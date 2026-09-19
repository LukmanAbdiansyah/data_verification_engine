import os
import re
from typing import List, Dict, Any
from collections import defaultdict
from .file_classifier import is_format_match
from .segy_parser import validate_segy
from .ascii_inspector import inspect_ascii
from .office_inspector import inspect_office_file
from .evidence_service import build_evidence_list, score_candidate

import logging
logger = logging.getLogger(__name__)


def get_product_folder(rel_path: str) -> str:
    """Extract the deliverable package folder name from relative path.
    
    Handles nested structures like:
    FINAL PRODUCT.../02_FINAL_PRESERVED.../MINIMUM_PHASE/file.sgy -> 02_FINAL_PRESERVED...
    04_CDP_GATHER.../file.sgy -> 04_CDP_GATHER...
    """
    clean = rel_path.replace('/', os.sep).replace('\\', '/')
    parts = clean.split('/')
    if len(parts) <= 1:
        return '(root)'
    dir_parts = parts[:-1]
    # If any directory part has a numbered prefix (01_, 02_, 13_), that's the deliverable package!
    for p in reversed(dir_parts):
        if re.match(r'^\d+[\._]', p):
            return p
    # If no numbered prefix, return innermost non-phase directory
    for p in reversed(dir_parts):
        if p.upper() not in ('MINIMUM_PHASE', 'ZERO_PHASE', 'MINIMUM PHASE', 'ZERO PHASE'):
            return p
    return dir_parts[0]


def _group_by_folder(files: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group files by their logical deliverable product folder."""
    groups = defaultdict(list)
    for f in files:
        folder = get_product_folder(f.get('relative_path', ''))
        groups[folder].append(f)
    return dict(groups)


def find_candidates(requirement: Dict[str, Any], files: List[Dict[str, Any]], format_name: str) -> List[Dict[str, Any]]:
    """Find and evaluate candidate files for a requirement+format.
    
    Groups files by deliverable folder and deeply inspects a sample file per folder.
    Folders are evaluated based on their deliverable package semantics.
    """
    prog = requirement.get('progress', '')
    
    # Step 1: Filter files by format
    format_matched = [f for f in files if f.get('readable', True) and is_format_match(f['extension'], format_name)]
    
    if not format_matched:
        return []
    
    # Step 2: Group by deliverable product folder
    folder_groups = _group_by_folder(format_matched)
    
    candidates = []
    
    for folder_name, folder_files in folder_groups.items():
        # Pick a representative sample file for deep inspection
        sample_file = folder_files[0]
        for ff in folder_files[:5]:
            fname = ff['filename'].lower()
            if any(kw in fname for kw in ['stack', 'gather', 'vel', 'report', 'near', 'mid', 'far', 'plot']):
                sample_file = ff
                break
        
        candidate = {
            'file_info': sample_file,
            'technical_validation': None,
            'header_lines': [],
            'content_preview': None,
            'evidence': [],
            'evidence_level': 'INSUFFICIENT',
            'contradictions': [],
            'score': 0,
            'folder_name': folder_name,
            'folder_file_count': len(folder_files),
        }
        
        # Deep inspection on sample file only
        if format_name == 'SEG-Y':
            tech = validate_segy(sample_file['full_path'])
            candidate['technical_validation'] = tech
            if tech.get('textual_header_lines'):
                candidate['header_lines'] = tech['textual_header_lines']
        elif format_name in ('ASCII', 'TXT', 'CSV', 'UKOOA', 'UKOOA P6/98', 'P1/90', 'P2/94'):
            preview = inspect_ascii(sample_file['full_path'])
            candidate['content_preview'] = preview
        elif format_name in ('DOC', 'DOCX', 'XLS', 'XLSX', 'PDF', 'PPT', 'PPTX', 'MS-OFFICE'):
            office_result = inspect_office_file(sample_file['full_path'])
            candidate['content_preview'] = office_result
        elif format_name in ('TIFF', 'IMAGE'):
            candidate['content_preview'] = {
                'type': 'TIFF',
                'note': f'{len(folder_files)} file(s) in deliverable folder {folder_name}'
            }
        
        candidate['evidence'] = build_evidence_list(
            candidate['technical_validation'],
            candidate['header_lines'],
            candidate['content_preview'],
            sample_file['filename'],
            sample_file['relative_path']
        )
        
        # Ensure file_info used for scoring reflects the product folder name
        scoring_fi = dict(sample_file)
        scoring_fi['parent_directory'] = folder_name
        scoring_fi['relative_path'] = f"{folder_name}/{sample_file['filename']}"
        
        level, contras, score = score_candidate(
            requirement_progress=prog,
            file_info=scoring_fi,
            tech_val=candidate['technical_validation'],
            header_lines=candidate['header_lines'],
            content_preview=candidate['content_preview']
        )
        
        candidate['evidence_level'] = level
        candidate['contradictions'] = contras
        candidate['score'] = score
        
        if len(folder_files) > 1:
            candidate['all_folder_files'] = folder_files
        
        # Only include candidate if it has a positive score (actual relevance)
        if score > 0:
            candidates.append(candidate)
    
    # Sort: Highest score first, then evidence level
    level_order = {'VERY_HIGH': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3, 'INSUFFICIENT': 4}
    candidates.sort(key=lambda c: (-c.get('score', 0), level_order.get(c['evidence_level'], 5)))
    
    # If there are strong matches without contradictions, prioritize them
    strong_matches = [c for c in candidates if c.get('evidence_level') in ('VERY_HIGH', 'HIGH') and not c.get('contradictions')]
    if strong_matches:
        return strong_matches
        
    return candidates
