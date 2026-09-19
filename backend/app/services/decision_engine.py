import os
from typing import Dict, List, Any, Optional

VALID_STATUSES = ['PASS', 'PARTIAL', 'MISSING', 'INVALID', 'REVIEW_REQUIRED']

def get_folder_summary(paths: List[str], fallback_parent: str = '') -> str:
    """Find highest common directory or list distinct top directories for multi-file sets."""
    if not paths:
        return fallback_parent
    try:
        common = os.path.commonpath([p for p in paths if p])
        if common and common != '.':
            return common
    except Exception:
        pass
    
    top_dirs = sorted(list(set(p.replace('\\', '/').split('/')[0] for p in paths if p)))
    if top_dirs:
        return ', '.join(top_dirs[:2]) + (f' (+{len(top_dirs)-2} dirs)' if len(top_dirs) > 2 else '')
    return fallback_parent

def decide_single_format(requirement: Dict[str, Any], format_name: str, candidates: List[Dict[str, Any]], ai_assessment: Optional[Dict[str, Any]] = None, ai_enabled: bool = True, ai_available: bool = True) -> Dict[str, Any]:
    result = {
        'format_name': format_name,
        'matched_file_id': None,
        'matched_file': None,
        'matched_file_path': None,
        'technical_validation': None,
        'evidence_level': 'INSUFFICIENT',
        'system_status': 'MISSING',
        'candidates': []
    }
    
    if not candidates:
        result['system_status'] = 'MISSING'
        return result
    
    matching_candidates = [c for c in candidates if c.get('evidence_level') in ('VERY_HIGH', 'HIGH') and not c.get('contradictions')]
    if not matching_candidates:
        matching_candidates = [c for c in candidates if c.get('score', 0) > 0 and not c.get('contradictions')]
    if not matching_candidates:
        matching_candidates = candidates
    
    result['candidates'] = [{
        'filename': c['file_info']['filename'],
        'relative_path': c['file_info']['relative_path'],
        'evidence_level': c.get('evidence_level', 'INSUFFICIENT'),
        'contradictions': c.get('contradictions', []),
    } for c in matching_candidates]
    
    best = matching_candidates[0]
    tech = best.get('technical_validation')
    num_matches = len(matching_candidates)
    
    folder_name = best.get('folder_name')
    folder_file_count = best.get('folder_file_count', len(best.get('all_folder_files', [])))
    
    if folder_name and folder_file_count > 1:
        matched_filename = f"{folder_file_count} files ({folder_name})"
        matched_path = folder_name
    elif num_matches > 1:
        paths = [c['file_info']['relative_path'] for c in matching_candidates if c.get('file_info', {}).get('relative_path')]
        common_dir = get_folder_summary(paths, best['file_info'].get('parent_directory', ''))
        matched_filename = f"{num_matches} files ({common_dir})"
        matched_path = common_dir
    else:
        matched_filename = best['file_info']['filename']
        matched_path = best['file_info']['relative_path']
    
    # SEG-Y technical validation check
    if format_name == 'SEG-Y' and tech:
        if not tech.get('valid_segy', False):
            result['system_status'] = 'INVALID'
            result['technical_validation'] = tech
            result['matched_file_id'] = best['file_info'].get('id')
            result['matched_file'] = matched_filename
            result['matched_file_path'] = matched_path
            return result
    
    # If AI assessment is available, trust it as the primary decision maker
    if ai_assessment:
        assessment = ai_assessment.get('assessment', '')
        ai_contradictions = ai_assessment.get('contradictions', [])
        
        if assessment == 'SUPPORTED':
            result['system_status'] = 'PASS'
        elif assessment == 'PARTIALLY_SUPPORTED':
            if not ai_contradictions:
                result['system_status'] = 'PASS'
            else:
                result['system_status'] = 'REVIEW_REQUIRED'
        elif assessment == 'CONFLICT':
            result['system_status'] = 'REVIEW_REQUIRED'
        elif assessment == 'NOT_SUPPORTED':
            result['system_status'] = 'REVIEW_REQUIRED'
        elif assessment == 'INSUFFICIENT_EVIDENCE':
            el = best.get('evidence_level', 'INSUFFICIENT')
            if el in ('VERY_HIGH', 'HIGH'):
                result['system_status'] = 'PASS'
            else:
                result['system_status'] = 'REVIEW_REQUIRED'
        else:
            result['system_status'] = 'REVIEW_REQUIRED'
    elif not ai_enabled:
        el = best.get('evidence_level', 'INSUFFICIENT')
        if el in ('VERY_HIGH', 'HIGH', 'MEDIUM'):
            result['system_status'] = 'PASS'
        else:
            result['system_status'] = 'REVIEW_REQUIRED'
    elif not ai_available:
        el = best.get('evidence_level', 'INSUFFICIENT')
        if el in ('VERY_HIGH', 'HIGH'):
            result['system_status'] = 'PASS'
        else:
            result['system_status'] = 'REVIEW_REQUIRED'
    else:
        result['system_status'] = 'REVIEW_REQUIRED'
    
    result['evidence_level'] = best.get('evidence_level', 'INSUFFICIENT')
    result['matched_file_id'] = best['file_info'].get('id')
    result['matched_file'] = matched_filename
    result['matched_file_path'] = matched_path
    result['technical_validation'] = tech
    
    return result

def decide_requirement(format_results: Dict[str, str]) -> str:
    statuses = list(format_results.values())
    if not statuses:
        return 'MISSING'
    if all(s == 'PASS' for s in statuses):
        return 'PASS'
    if all(s == 'MISSING' for s in statuses):
        return 'MISSING'
    if all(s == 'INVALID' for s in statuses):
        return 'INVALID'
    if 'PASS' in statuses and ('MISSING' in statuses or 'INVALID' in statuses):
        return 'PARTIAL'
    if 'REVIEW_REQUIRED' in statuses:
        return 'REVIEW_REQUIRED'
    return 'PARTIAL'
