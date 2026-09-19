import re
from typing import List, Dict, Any, Tuple, Optional

EVIDENCE_LEVELS = ['VERY_HIGH', 'HIGH', 'MEDIUM', 'LOW', 'INSUFFICIENT']

def parse_seismic_concepts(text: str) -> Dict[str, bool]:
    """Parse seismic keywords, deliverable semantics, angles, phases, and processing flavors."""
    t = text.replace('_', ' ').replace('-', ' ').replace('.', ' ').replace('/', ' ').replace('\\', ' ').lower()
    
    # Angle stacks & specific angle bins
    has_angle = bool(re.search(r'\b(angle|angles|angle stack|angle stacks|angle migration)\b', t))
    has_near = bool(re.search(r'\b(near|near angle)\b', t))
    has_mid = bool(re.search(r'\b(mid|mid angle|middle)\b', t))
    has_far = bool(re.search(r'(?<!ultra\s)(?<!ultra)\bfar\b', t))
    has_ultra_far = bool(re.search(r'\b(ultra far|ultrafar|ufar)\b', t))
    is_angle_stack = has_angle or has_near or has_mid or has_far or has_ultra_far
    
    # Phases
    has_min_phase = bool(re.search(r'\b(minimum phase|min phase|minimum|mp)\b', t))
    has_zero_phase = bool(re.search(r'\b(zero phase|0 phase|zero|zp|zerophase)\b', t))
    
    # Gathers & NMO status
    is_gather = bool(re.search(r'\b(gather|gathers|cmp gather|cdp gather|sp gather)\b', t))
    has_no_nmo = bool(re.search(r'\b(no nmo|without nmo|pre migration|pre migration gather|pre migration gathers)\b', t))
    has_nmo = bool(re.search(r'\b(nmo applied|with nmo|final pstm gather|final gather|pstm gather|pstm gathers)\b', t))
    
    # Specific stage keywords
    is_sp_nav = bool(re.search(r'\b(sp|sp gather|navigation|nav merge|merge)\b', t))
    is_precond = bool(re.search(r'\b(precondition|preconditioning|precond)\b', t))
    
    # Processing flavor
    is_tvf_tvs = bool(re.search(r'\b(tvf|tvs|time variant filter|time variant scaling)\b', t))
    is_non_pres = bool(re.search(r'\b(non preserved|nonpreserved|agc|scaling)\b', t)) or is_tvf_tvs
    is_raw = bool(re.search(r'(?<!non\s)(?<!non)preserved\b|\b(raw|true amplitude)\b', t))
    is_final = bool(re.search(r'\b(final)\b', t)) or is_tvf_tvs
    
    # Velocity
    is_velocity = bool(re.search(r'\b(vel|velocity|vint|vrms|velocity model|interval velocity|stacking velocity)\b', t))
    is_rms = bool(re.search(r'\b(rms|vrms|stacking velocity)\b', t))
    is_interval = bool(re.search(r'\b(interval|vint)\b', t))
    
    # Stacks & Plots
    is_stack = bool(re.search(r'\b(stack|stacks|migrated stack)\b', t))
    is_seismic_plot = bool(re.search(r'\b(seismic plot|plot|section)\b', t))
    
    return {
        'velocity': is_velocity,
        'is_rms': is_rms,
        'is_interval': is_interval,
        'gather': is_gather,
        'has_no_nmo': has_no_nmo,
        'has_nmo': has_nmo,
        'is_sp_nav': is_sp_nav,
        'is_precond': is_precond,
        'stack': is_stack,
        'is_angle_stack': is_angle_stack,
        'has_angle': has_angle,
        'has_near': has_near,
        'has_mid': has_mid,
        'has_far': has_far,
        'has_ultra_far': has_ultra_far,
        'has_min_phase': has_min_phase,
        'has_zero_phase': has_zero_phase,
        'report': bool(re.search(r'\b(report|processing report)\b', t)),
        'presentation': bool(re.search(r'\b(presentation)\b', t)),
        'raw': is_raw,
        'final': is_final,
        'non_preserved': is_non_pres,
        'is_seismic_plot': is_seismic_plot,
        'depth': bool(re.search(r'\b(depth|psdm|pre sdm)\b', t)),
        'time': bool(re.search(r'\b(time|pstm|pre stm)\b', t)),
    }

def detect_contradictions(requirement_progress: str, filename: str, header_lines: List[str], content_preview: Optional[Dict] = None, parent_dir: str = '', relative_path: str = '') -> List[str]:
    """Detect clear contradictions between requirement and candidate file metadata/headers."""
    contradictions = []
    r = parse_seismic_concepts(requirement_progress)
    
    product_lines = [l for l in header_lines if re.search(r'C0[1-8]|PROCESS|PRODUCT|OUTPUT', l, re.I)]
    product_header = ' '.join(product_lines) if product_lines else ''
    content_str = str(content_preview) if content_preview else ''
    
    f_header = parse_seismic_concepts(product_header) if product_header else {}
    f_path = parse_seismic_concepts(f'{relative_path} {parent_dir} {filename}')
    f_content = parse_seismic_concepts(content_str) if content_str else {}
    
    def f_has(concept):
        return f_header.get(concept, False) or f_path.get(concept, False) or f_content.get(concept, False)
    
    # 1. Domain conflicts
    if r['time'] and not r['depth'] and f_has('depth') and not f_has('time'):
        if f_header.get('depth', False):
            contradictions.append('Requirement expects time domain, but SEG-Y header indicates depth domain')
    if r['depth'] and not r['time'] and f_has('time') and not f_has('depth'):
        if f_header.get('time', False):
            contradictions.append('Requirement expects depth domain, but SEG-Y header indicates time domain')
    
    # 2. Report vs Presentation
    if r['report'] and f_has('presentation') and not f_has('report'):
        contradictions.append('Requirement expects processing report, but candidate is a presentation')
        
    return contradictions

def score_candidate(requirement_progress: str, file_info: Dict[str, Any], tech_val: Optional[Dict[str, Any]], header_lines: List[str], content_preview: Optional[Dict[str, Any]]) -> Tuple[str, List[str], int]:
    """Score candidate relevance against requirement progress string."""
    r = parse_seismic_concepts(requirement_progress)
    # Focus strictly on lines defining data type or product, avoiding acquisition parameters (CMP INTERVAL, SP RANGE)
    product_lines = [l for l in header_lines if re.search(r'DATA\s*TYPES?|PROCESS\b|PRODUCT\b|OUTPUT\b', l, re.I)]
    if not product_lines:
        product_lines = [l for l in header_lines[:12] if re.search(r'\b(stack|gather|velocity|velocities)\b', l, re.I)]
    product_header = ' '.join(product_lines) if product_lines else ''
    content_str = str(content_preview) if content_preview else ''
    parent_dir = file_info.get('parent_directory', '')
    rel_path = file_info.get('relative_path', '')
    path_str = f"{rel_path} {parent_dir} {file_info.get('filename', '')}"
    
    contras = detect_contradictions(
        requirement_progress=requirement_progress,
        filename=file_info.get('filename', ''),
        header_lines=header_lines,
        content_preview=content_preview,
        parent_dir=parent_dir,
        relative_path=rel_path
    )
    if contras:
        return 'INSUFFICIENT', contras, -10
        
    h_toks = parse_seismic_concepts(product_header)
    c_toks = parse_seismic_concepts(content_str)
    p_toks = parse_seismic_concepts(path_str)
    
    def matched(concept):
        return h_toks.get(concept, False) or p_toks.get(concept, False) or c_toks.get(concept, False)
    
    has_header_match = False
    has_content_match = False
    has_path_match = False
    
    score = 0
    
    # 1. Product type
    if r['velocity']:
        if matched('velocity'):
            score += 10
            if h_toks['velocity']: has_header_match = True
            if p_toks['velocity']: has_path_match = True
        elif matched('stack') or matched('gather'):
            score -= 15  # Penalty for wrong product type
            
    if r['gather']:
        if matched('gather'):
            score += 10
            if h_toks['gather']: has_header_match = True
            if p_toks['gather']: has_path_match = True
        elif matched('stack') or matched('velocity'):
            score -= 15
            
    if r['stack'] and not r['is_seismic_plot']:
        if matched('stack'):
            score += 10
            if h_toks['stack']: has_header_match = True
            if p_toks['stack']: has_path_match = True
        elif matched('gather') and not r['is_angle_stack']:
            score -= 15
            
    if r['report']:
        if matched('report'):
            score += 10
            if c_toks['report']: has_content_match = True
            if p_toks['report']: has_path_match = True
            
    if r['is_seismic_plot']:
        if matched('is_seismic_plot'):
            score += 15
            if p_toks['is_seismic_plot']: has_path_match = True
            
    # 2. Velocity subtypes: RMS vs Interval
    if r['is_rms']:
        if matched('is_rms'):
            score += 10
        elif matched('is_interval'):
            score -= 10
    if r['is_interval']:
        if matched('is_interval'):
            score += 10
        elif matched('is_rms'):
            score -= 10
            
    # 3. Gather stages: SP / Nav vs Preconditioning vs PSTM
    if r['is_sp_nav']:
        if matched('is_sp_nav') and 'sp gather' in path_str.lower():
            score += 15
        elif matched('has_nmo') or 'pstm' in path_str.lower():
            score -= 20  # PSTM gather is NOT SP gather!
            
    if r['is_precond']:
        if matched('is_precond'):
            score += 10
        elif 'pstm' in path_str.lower():
            score -= 15
            
    if r['has_nmo'] and matched('has_nmo'):
        score += 8
    if r['has_no_nmo'] and matched('has_no_nmo'):
        score += 8
        
    # 4. Processing flavor: Preserved vs Non-Preserved
    if r['non_preserved']:
        if matched('non_preserved') or (matched('final') and not matched('raw')):
            score += 10
        elif matched('raw') and not matched('non_preserved') and not matched('final'):
            score -= 15
    elif r['raw'] and not r['final']:
        if matched('raw') and not matched('non_preserved'):
            score += 10
        elif matched('non_preserved') or (matched('final') and not matched('raw')):
            score -= 15
    elif r['raw']:
        if matched('raw') and not matched('non_preserved'):
            score += 10
        elif matched('non_preserved'):
            score -= 10
            
    # 5. Angle stacks bonus
    if r['is_angle_stack']:
        if matched('is_angle_stack'):
            score += 15
            if h_toks['is_angle_stack']: has_header_match = True
            if p_toks['is_angle_stack']: has_path_match = True
        for b in ['near', 'mid', 'far', 'ultra_far']:
            if r[f'has_{b}'] and matched(f'has_{b}'):
                score += 3
                
    # 6. Flavors, Domain, Phases
    if r['final'] and matched('final'): score += 5
    if r['depth'] and matched('depth'): score += 3
    if r['time'] and matched('time'): score += 3
    if r['has_min_phase'] and matched('has_min_phase'): score += 2
    if r['has_zero_phase'] and matched('has_zero_phase'): score += 2
    
    ext = file_info.get('extension', '').lower()
    has_tech = (tech_val is not None and tech_val.get('valid_segy')) or (ext in ('.pdf', '.docx', '.xlsx', '.txt', '.asc', '.csv', '.tiff', '.tif'))
    
    if score <= 0:
        level = 'INSUFFICIENT'
    elif has_tech and (has_header_match or has_content_match) and score >= 10:
        level = 'VERY_HIGH'
    elif has_tech and has_path_match and score >= 8:
        level = 'HIGH'
    elif has_tech and score >= 5:
        level = 'MEDIUM'
    elif has_tech and score > 0:
        level = 'LOW'
    else:
        level = 'INSUFFICIENT'
        
    return level, contras, score

def calculate_evidence_level(has_technical_validation: bool, has_internal_content_match: bool, has_header_match: bool, has_filename_match: bool, has_folder_match: bool, has_contradiction: bool) -> str:
    if has_contradiction:
        return 'INSUFFICIENT'
    if has_technical_validation and (has_internal_content_match or has_header_match):
        return 'VERY_HIGH'
    if has_technical_validation and (has_filename_match or has_folder_match):
        return 'HIGH'
    if has_technical_validation:
        return 'LOW'
    return 'INSUFFICIENT'

def build_evidence_list(technical_result: Optional[Dict], header_lines: List[str], content_preview: Optional[Dict], filename: str, relative_path: str) -> List[Dict[str, str]]:
    evidences = []
    if technical_result:
        evidences.append({'evidence_type': 'technical_validation', 'content': str(technical_result), 'strength': 'strong'})
    if header_lines:
        non_empty = [l for l in header_lines if l.strip()]
        if non_empty:
            evidences.append({'evidence_type': 'textual_header', 'content': '\n'.join(non_empty[:10]), 'strength': 'very_strong'})
    if content_preview:
        evidences.append({'evidence_type': 'content_preview', 'content': str(content_preview), 'strength': 'very_strong'})
    evidences.append({'evidence_type': 'filename', 'content': filename, 'strength': 'supporting'})
    evidences.append({'evidence_type': 'path', 'content': relative_path, 'strength': 'supporting'})
    return evidences
