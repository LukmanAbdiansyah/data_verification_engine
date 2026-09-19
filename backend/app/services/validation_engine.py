import asyncio
import json
import logging
import os
import re
import time
from typing import List, Dict, Any, Optional
from collections import defaultdict

from .file_classifier import classify_file, is_format_match
from .candidate_filter import get_product_folder
from .decision_engine import decide_requirement
from .ai_client import AIClient
from .ai_folder_matcher import AIFolderMatcher, reconcile_unmapped_segy_ascii
from .segy_parser import validate_segy
from .office_inspector import inspect_office_file

logger = logging.getLogger(__name__)


def _build_folder_summary(files: List[Dict[str, Any]], segy_enabled: bool = True) -> List[Dict[str, Any]]:
    """Group files by logical deliverable package folder and extract sample metadata."""
    folder_dict = defaultdict(list)
    for f in files:
        pf = get_product_folder(f.get('relative_path', ''))
        folder_dict[pf].append(f)
        
    folder_summaries = []
    for pf, f_list in sorted(folder_dict.items()):
        ext_counts = defaultdict(int)
        for f in f_list:
            ext = f.get('extension', '')
            if ext:
                ext_counts[ext] += 1
        
        # Pick representative sample file
        sample_file = f_list[0]
        for ff in f_list[:5]:
            fname = ff['filename'].lower()
            if any(kw in fname for kw in ['stack', 'gather', 'vel', 'report', 'near', 'mid', 'far', 'plot']):
                sample_file = ff
                break
                
        hl = []
        cp = None
        ext = sample_file.get('extension', '').lower()
        if ext in ('.sgy', '.segy') and segy_enabled:
            tech = validate_segy(sample_file['full_path'])
            all_lines = tech.get('textual_header_lines', [])
            key_lines = [l.strip() for l in all_lines[:6] if l.strip()]
            extra_lines = [l.strip() for l in all_lines[6:] if re.search(r'DATA\s*TYPES?|PROCESS|PRODUCT|OUTPUT|STACK|GATHER|VELOCITY', l, re.I)]
            hl = (key_lines + extra_lines)[:8]
        elif ext in ('.pdf', '.docx', '.xlsx', '.txt'):
            cp = inspect_office_file(sample_file['full_path'])
            
        folder_summaries.append({
            'name': pf,
            'file_count': len(f_list),
            'extensions': dict(ext_counts),
            'sample_files': [f['filename'] for f in f_list[:8]],
            'header_lines': hl,
            'content_preview': cp,
            'files': f_list,
            'sample_file': sample_file
        })
        
    return folder_summaries


class ValidationEngine:
    """AI-First Deliverable Validation Engine with Multi-Folder and Full File Tracking."""
    
    def __init__(self, ai_client: Optional[AIClient] = None, ai_enabled: bool = True, segy_enabled: bool = True):
        self.ai_client = ai_client
        self.ai_enabled = ai_enabled
        self.segy_enabled = segy_enabled
    
    async def run_validation(self, run_id: str, requirements: List[Dict[str, Any]], files: List[Dict[str, Any]], settings: Dict[str, Any], progress_callback=None, cancel_event=None) -> List[Dict[str, Any]]:
        results = []
        total = len(requirements)
        
        # Stage 1: Classify all files
        if progress_callback:
            await progress_callback({
                'stage': 'file_classification', 'processed': 0, 'total': len(files),
                'message': 'Classifying files...', 'status': 'running', 'run_id': run_id
            })
        
        for f in files:
            f['file_type'] = classify_file(f['extension'])
        
        if progress_callback:
            await progress_callback({
                'stage': 'file_classification', 'processed': len(files), 'total': len(files),
                'message': 'File classification complete', 'status': 'completed', 'run_id': run_id
            })
        
        # Stage 2: Discover and summarize deliverable folders
        if progress_callback:
            await progress_callback({
                'stage': 'folder_discovery', 'processed': 0, 'total': total,
                'message': 'Analyzing deliverable folder structure...', 'status': 'running', 'run_id': run_id
            })
            
        folder_summaries = _build_folder_summary(files, segy_enabled=self.segy_enabled)
        logger.info(f"Discovered {len(folder_summaries)} deliverable package folders")
        
        # Stage 3: AI-First Folder Matching
        if progress_callback:
            await progress_callback({
                'stage': 'ai_matching', 'processed': 0, 'total': total,
                'message': 'AI matching requirements to deliverable folders...', 'status': 'running', 'run_id': run_id
            })
            
        ai_matcher = AIFolderMatcher(ai_client=self.ai_client if self.ai_enabled else None)
        folder_mappings = await ai_matcher.match_all(requirements, folder_summaries, settings)
        folder_mappings = reconcile_unmapped_segy_ascii(folder_mappings, requirements, folder_summaries)
        
        # Stage 4: Technical Validation per requirement & format
        for idx, req in enumerate(requirements):
            if cancel_event and cancel_event.is_set():
                break
                
            req_id = req.get('req_id', '')
            formats = req.get('formats', [])
            mapping = folder_mappings.get(req_id, {})
            
            if progress_callback:
                await progress_callback({
                    'stage': 'validation', 'processed': idx, 'total': total,
                    'message': f"Validating: {req['progress'][:50]}...",
                    'status': 'running', 'run_id': run_id
                })
                
            format_results = {}
            req_detail_results = []
            
            for fmt in formats:
                decision = self._verify_single_format(req, fmt, mapping, folder_summaries)
                format_results[fmt] = decision['system_status']
                req_detail_results.append(decision)
                
            overall_status = decide_requirement(format_results)
            
            results.append({
                'requirement': req,
                'format_results': req_detail_results,
                'overall_status': overall_status,
            })
            
        if progress_callback:
            await progress_callback({
                'stage': 'completed', 'processed': total, 'total': total,
                'message': 'Validation complete', 'status': 'completed', 'run_id': run_id
            })
            
        return results

    def _verify_single_format(self, req: Dict[str, Any], fmt: str, mapping: Dict[str, Any], folder_summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Verify format requirements against the mapped deliverable folder(s)."""
        format_folders = mapping.get('format_folders', {})
        matched_folders = mapping.get('matched_folders', [])
        ai_status = mapping.get('status', 'MISSING')
        confidence = mapping.get('confidence', 'MEDIUM')
        reasoning = mapping.get('reasoning', '')
        
        # Collect all folders fulfilling this format
        target_folders = []
        fmt_target = format_folders.get(fmt)
        if isinstance(fmt_target, list):
            target_folders.extend(fmt_target)
        elif isinstance(fmt_target, str) and fmt_target:
            target_folders.append(fmt_target)
            
        # Also include any folders in matched_folders that contain this format
        for mf in matched_folders:
            if mf not in target_folders:
                fs = next((f for f in folder_summaries if f['name'] == mf), None)
                if fs and any(is_format_match(ext, fmt) for ext in fs['extensions'].keys()):
                    target_folders.append(mf)
                    
        result = {
            'format_name': fmt,
            'matched_file_id': None,
            'matched_file': None,
            'matched_file_path': None,
            'technical_validation': None,
            'evidence_level': 'INSUFFICIENT',
            'system_status': 'MISSING',
            'candidates': [],
            'ai_assessment': {
                'assessment': 'SUPPORTED' if ai_status == 'PASS' else ('NOT_SUPPORTED' if ai_status == 'MISSING' else 'PARTIALLY_SUPPORTED'),
                'matched_evidence': target_folders if target_folders else [],
                'missing_evidence': [] if target_folders else [f"No deliverable folder for {fmt}"],
                'contradictions': [],
                'reasoning_summary': reasoning
            }
        }
        
        if not target_folders:
            result['system_status'] = 'MISSING'
            return result
            
        # Gather ALL matching files from all target folders
        all_matching_files = []
        for tf in target_folders:
            fs = next((f for f in folder_summaries if f['name'] == tf), None)
            if fs:
                m_files = [f for f in fs['files'] if is_format_match(f.get('extension', ''), fmt)]
                # Also include companion seismic data files in the same deliverable folder (e.g. ASCII velocity with SEG-Y)
                companion_files = [f for f in fs['files'] if f not in m_files and f.get('extension', '').lower() in ('.sgy', '.segy', '.txt', '.asc', '.dat')]
                all_matching_files.extend(m_files)
                all_matching_files.extend(companion_files)
                
        if not all_matching_files:
            result['system_status'] = 'MISSING'
            return result
            
        sample = next((f for f in all_matching_files if is_format_match(f.get('extension', ''), fmt)), all_matching_files[0])
        tech_val = None
        
        # Run technical format check if SEG-Y
        if fmt == 'SEG-Y' and self.segy_enabled:
            tech_val = validate_segy(sample['full_path'])
            result['technical_validation'] = tech_val
            if not tech_val.get('valid_segy', False):
                result['system_status'] = 'INVALID'
                result['matched_file'] = sample['filename']
                result['matched_file_path'] = sample['relative_path']
                result['matched_file_id'] = sample.get('id')
                return result
                
        # Status assignment
        if ai_status == 'PASS':
            status = 'PASS'
            ev_level = 'VERY_HIGH'
        elif ai_status == 'REVIEW_REQUIRED':
            status = 'REVIEW_REQUIRED'
            ev_level = 'MEDIUM'
        elif ai_status == 'MISSING':
            status = 'MISSING'
            ev_level = 'INSUFFICIENT'
        else:
            status = 'PASS' if confidence in ('HIGH', 'MEDIUM') else 'REVIEW_REQUIRED'
            ev_level = 'HIGH' if confidence == 'HIGH' else 'MEDIUM'
            
        if len(target_folders) > 1:
            folder_summary_str = ', '.join(target_folders[:3]) + (f' (+{len(target_folders)-3} folders)' if len(target_folders) > 3 else '')
            matched_filename = f"{len(all_matching_files)} files ({folder_summary_str})"
            matched_path = ', '.join(target_folders)
        elif len(all_matching_files) > 1:
            matched_filename = f"{len(all_matching_files)} files ({target_folders[0]})"
            matched_path = target_folders[0]
        else:
            matched_filename = sample['filename']
            matched_path = sample['relative_path']
            
        result['system_status'] = status
        result['evidence_level'] = ev_level
        result['matched_file'] = matched_filename
        result['matched_file_path'] = matched_path
        result['matched_file_id'] = sample.get('id')
        
        # Build candidate list with ALL matching deliverable files (no truncating to 5!)
        candidates_list = []
        for f in all_matching_files:
            candidates_list.append({
                'filename': f['filename'],
                'relative_path': f['relative_path'],
                'evidence_level': ev_level,
                'contradictions': []
            })
                
        result['candidates'] = candidates_list
        return result
