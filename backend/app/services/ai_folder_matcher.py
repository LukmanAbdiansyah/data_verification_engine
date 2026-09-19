import os
import re
import json
import logging
from typing import List, Dict, Any, Optional
from .file_classifier import is_format_match
from .evidence_service import score_candidate, parse_seismic_concepts

logger = logging.getLogger(__name__)

FOLDER_MATCHING_SYSTEM_PROMPT = """You are a principal seismic data manager and senior data auditor.
Your mission is to examine all deliverables in a seismic data processing project and map each deliverable requirement to the matching folder(s) in the repository.

MANDATORY CRITICAL REQUIREMENT:
- ZERO UNMAPPED SEISMIC FILES: Every single folder in the repository containing SEG-Y (.sgy, .segy) or ASCII (.txt, .asc, .dat) files MUST be accounted for and mapped to the most appropriate deliverable requirement. Do NOT leave any SEG-Y or ASCII folders unassigned.

Hierarchical Matching & Verification Criteria:
1. PRIMARY CRITERIA - FOLDER NAME & FILENAMES:
   - In seismic projects, both folder names and filenames follow standard naming conventions (e.g. folder '02_FINAL_PRESERVED_AMPLITUDE_STACK_AFTER_PSTM' containing files like 'FINAL_PRESERVED_AMPLITUDE_STACK_AFTER_PSTM_LINE_NSO19-P11001-057.sgy').
   - Always evaluate both the folder name AND the filename patterns inside the folder.
2. VERIFICATION CRITERIA - SEG-Y TEXTUAL HEADER:
   - If the folder name or filename is abbreviated, generic, or if you need to be 100% certain of the processing stage, examine the decoded SEG-Y Textual Header (especially line C03 'DATA TYPES:', 'PROCESS:', 'PRODUCT:').
   - For example, line 'C03DATA TYPES: FINAL PRESERVED AMPLITUDE STACK AFTER PSTM' explicitly confirms the deliverable type.
3. MULTI-FOLDER DELIVERABLES & MULTI-DOMAIN:
   - Certain seismic deliverables are delivered across MULTIPLE folders. You MUST map ALL corresponding folders in 'matched_folders':
   - 'Depth and Time Domain' (e.g. 'Raw PSDM Stack (Preserved) Depth and Time Domain'):
     MUST map BOTH Depth and Time folders: ['RAW_PSDM_DEPTH_STACK', 'RAW_PSDM_TIME_STACK'].
   - 'Final PSDM Stack (Non-Preserved) Depth and Time Domain':
     In seismic processing, non-preserved stacks encompass both final filtered/scaled stacks AND AGC (Automatic Gain Control) stacks across Depth and Time domains. Map ALL relevant folders: ['FINAL_PSDM_DEPTH_STACK', 'FINAL_PSDM_TIME_STACK', 'AGC_PSDM_DEPTH_STACK', 'AGC_PSDM_TIME_STACK'].
   - 'Final Angle Stack (Near Angle Stack, Mid Angle Stack, Far Angle Stack, Ultra Far Angle Stack)':
     Must map to ALL matching angle stack folders: ['04_NEAR_ANGLE_STACK', '05_MID_ANGLE_STACK', '06_FAR_ANGLE_STACK', '07_ULTRA_FAR_ANGLE_STACK'] (and their zero-phase counterparts '16_NEAR_ANGLE_STACK__ZERO_PHASE', '17_MID_ANGLE_STACK_ZERO_PHASE', '18_FAR_ANGLE_STACK_ZERO_PHASE', '19_ULTRA_FAR_ANGLE_STACK_ZERO_PHASE' if present).
   - Deliverables with complementary phase volumes (e.g. minimum phase and zero phase): include both in 'matched_folders'.
   - Multi-format deliverables (e.g. 'Final Velocity RMS' requiring both SEG-Y and ASCII): list both '08_FINAL_VELOCITY_RMS_SEGY' and '10_FINAL_VELOCITY_RMS_ASCII'.
4. FORMAT MATCHING:
   - 'SEG-Y': files with .sgy, .segy
   - 'ASCII': files with .txt, .asc, .dat
   - 'TIFF': files with .tif, .tiff (seismic plot sections)
   - 'PDF': files with .pdf (final reports)
   - 'MS-OFFICE' / 'MS WORD FORMAT': files with .doc, .docx
5. PRESERVED VS NON-PRESERVED:
   - 'Final Preserved Amplitude Stack' maps to folders containing 'PRESERVED' and 'PSTM'.
   - 'Final Non-Preserved Amplitude Stack' maps to folders containing 'NON_PRESERVED' or 'AGC'.
6. MISSING DELIVERABLES:
   - If a deliverable was clearly NOT delivered in this repository (e.g. 'SP Gather Navigation Merge' when only PSTM CDP gathers exist, or 'CDP Gather After Preconditioning' when no preconditioning gather folder exists), assign status 'MISSING'.
   - DO NOT falsely map unrelated folders to a requirement.
7. STATUS VALUES:
   - 'PASS': The required deliverable folder(s) exist and match the requirement, filename pattern, and formats.
   - 'MISSING': No matching folder/file exists in the repository for this deliverable.
   - 'REVIEW_REQUIRED': Partial match, ambiguity, or potential conflict that requires human inspection.

Return ONLY a valid JSON object matching this exact schema:
{
  "mappings": [
    {
      "req_id": "REQ-001",
      "status": "PASS | REVIEW_REQUIRED | MISSING",
      "confidence": "HIGH | MEDIUM | LOW",
      "format_folders": {
        "SEG-Y": ["folder_name_1", "folder_name_2"]
      },
      "matched_folders": ["folder_name_1", "folder_name_2"],
      "reasoning": "Brief explanation citing folder name, filename pattern, and SEG-Y header confirmation"
    }
  ]
}"""


def build_folder_matching_prompt(requirements: List[Dict[str, Any]], folders: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Build the prompt for AI folder-first matching."""
    user_lines = []
    
    user_lines.append("=" * 80)
    user_lines.append("DELIVERABLE REQUIREMENTS TO VERIFY")
    user_lines.append("=" * 80)
    for req in requirements:
        fmts = req.get('formats', [])
        fmt_str = ', '.join(fmts) if fmts else 'ANY'
        user_lines.append(f"- [{req.get('req_id', 'REQ')}] {req.get('progress', '')} | Expected Format(s): [{fmt_str}]")
    
    user_lines.append("")
    user_lines.append("=" * 80)
    user_lines.append(f"REPOSITORY FOLDERS & FILES AVAILABLE ({len(folders)} folders discovered)")
    user_lines.append("=" * 80)
    
    for i, f in enumerate(folders):
        name = f.get('name', '')
        count = f.get('file_count', 0)
        exts = f.get('extensions', {})
        ext_summary = ', '.join(f"{k}:{v}" for k, v in exts.items()) if exts else 'unknown'
        
        user_lines.append(f"\nFolder {i+1}: {name}")
        user_lines.append(f"  Total Files: {count} ({ext_summary})")
        
        samples = f.get('sample_files', [])
        if samples:
            user_lines.append("  Sample Filenames in Folder:")
            for s in samples[:6]:
                user_lines.append(f"    - {s}")
            
        header_lines = f.get('header_lines', [])
        if header_lines:
            user_lines.append("  SEG-Y Textual Header (for verification):")
            for hl in header_lines[:6]:
                user_lines.append(f"    {hl}")
                
        preview = f.get('content_preview')
        if preview and isinstance(preview, dict):
            if preview.get('title'):
                user_lines.append(f"  Document Title: {preview['title']}")
            if preview.get('headings'):
                user_lines.append(f"  Headings: {', '.join(preview['headings'][:4])}")
    
    user_lines.append("")
    user_lines.append("=" * 80)
    user_lines.append("TASK")
    user_lines.append("=" * 80)
    user_lines.append("For EACH requirement listed above, map it to the exact folder(s) that fulfill it, or mark it MISSING.")
    user_lines.append("CRITICAL REQUIREMENT: Ensure ALL repository folders containing SEG-Y (.sgy, .segy) or ASCII (.txt, .asc, .dat) files are mapped to one of the requirements. Zero unmapped seismic folders.")
    user_lines.append("If a requirement specifies 'Depth and Time Domain', map BOTH Depth and Time folders.")
    user_lines.append("If a deliverable is split across multiple folders (e.g. Angle Stacks Near/Mid/Far/Ultra-Far, or Final + AGC Stacks), list ALL relevant folders.")
    user_lines.append("Check the folder name AND the filename patterns. If needed, verify against the SEG-Y header.")
    user_lines.append("Return ONLY the valid JSON object with the 'mappings' list.")
    
    return [
        {"role": "system", "content": FOLDER_MATCHING_SYSTEM_PROMPT},
        {"role": "user", "content": "\n".join(user_lines)}
    ]


def reconcile_unmapped_segy_ascii(
    mappings: Dict[str, Dict[str, Any]], 
    requirements: List[Dict[str, Any]], 
    folders: List[Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    """
    Ensure 100% of SEG-Y (.sgy, .segy) and ASCII (.txt, .asc, .dat) folders in the repository
    are mapped to at least one deliverable requirement.
    """
    # 1. Identify all folders containing SEG-Y or ASCII files
    segy_ascii_folders = []
    for f in folders:
        exts = [k.lower() for k in f.get('extensions', {}).keys()]
        if any(ext in ('.sgy', '.segy', '.txt', '.asc', '.dat') for ext in exts):
            segy_ascii_folders.append(f)
            
    # 2. Collect all currently mapped folders across all requirements
    mapped_folder_names = set()
    for m in mappings.values():
        for fld in m.get('matched_folders', []):
            mapped_folder_names.add(fld)
        for fmt_flds in m.get('format_folders', {}).values():
            if isinstance(fmt_flds, list):
                for fld in fmt_flds:
                    mapped_folder_names.add(fld)
            elif isinstance(fmt_flds, str):
                mapped_folder_names.add(fmt_flds)
                
    # 3. Find unmapped folders
    unmapped = [f for f in segy_ascii_folders if f['name'] not in mapped_folder_names]
    if not unmapped:
        logger.info("All SEG-Y and ASCII folders are already mapped (100% coverage)")
        return mappings

    logger.info(f"Reconciling {len(unmapped)} unmapped SEG-Y/ASCII folder(s): {[f['name'] for f in unmapped]}")
    
    for f_data in unmapped:
        f_name = f_data['name']
        sample_file = f_data.get('files', [{}])[0] if f_data.get('files') else {}
        fi = {
            'filename': sample_file.get('filename', f_name),
            'parent_directory': f_name,
            'relative_path': f"{f_name}/{sample_file.get('filename', '')}",
            'extension': sample_file.get('extension', '')
        }
        
        # Score this unmapped folder against each requirement
        best_req_id = None
        best_score = -999
        best_fmt = 'SEG-Y' if any(ext in ('.sgy', '.segy') for ext in f_data.get('extensions', {}).keys()) else 'ASCII'
        
        for req in requirements:
            req_id = req.get('req_id')
            prog = req.get('progress', '')
            formats = req.get('formats', [])
            
            level, contras, score = score_candidate(
                requirement_progress=prog,
                file_info=fi,
                tech_val={'valid_segy': True} if best_fmt == 'SEG-Y' else None,
                header_lines=f_data.get('header_lines', []),
                content_preview=f_data.get('content_preview')
            )
            
            # Format compatibility: check if requirement expects this format or can accept it
            fmt_compat = any(is_format_match(ext, fmt) for ext in f_data.get('extensions', {}).keys() for fmt in formats)
            if fmt_compat:
                score += 15
                
            r_concepts = parse_seismic_concepts(prog)
            f_concepts = parse_seismic_concepts(f_name)
            # Bonus for matching velocity, gather, stack, depth, time
            for key in ('velocity', 'gather', 'stack', 'raw', 'final', 'non_preserved', 'depth', 'time'):
                if r_concepts.get(key) and f_concepts.get(key):
                    score += 10
            
            if score > best_score:
                best_score = score
                best_req_id = req_id
                
        # If we found a compatible requirement
        if best_req_id and best_score > -10:
            m = mappings.get(best_req_id)
            if not m:
                m = {
                    'req_id': best_req_id,
                    'status': 'PASS',
                    'confidence': 'HIGH',
                    'format_folders': {},
                    'matched_folders': [],
                    'reasoning': ''
                }
                mappings[best_req_id] = m
                
            if f_name not in m['matched_folders']:
                m['matched_folders'].append(f_name)
                
            fmt_folders = m.setdefault('format_folders', {})
            # Determine target format bucket
            target_fmt = best_fmt
            target_req = next((r for r in requirements if r.get('req_id') == best_req_id), {})
            for fmt in target_req.get('formats', []):
                if any(is_format_match(ext, fmt) for ext in f_data.get('extensions', {}).keys()):
                    target_fmt = fmt
                    break
            
            if target_fmt not in fmt_folders:
                fmt_folders[target_fmt] = []
            if isinstance(fmt_folders[target_fmt], list) and f_name not in fmt_folders[target_fmt]:
                fmt_folders[target_fmt].append(f_name)
                
            if m.get('status') == 'MISSING':
                m['status'] = 'PASS'
                
            m['reasoning'] = (m.get('reasoning', '') + f" Reconciled folder '{f_name}'.").strip()
            logger.info(f"Reconciled unmapped folder '{f_name}' -> requirement [{best_req_id}] (score={best_score})")

    return mappings


class AIFolderMatcher:
    """AI-First folder matcher that evaluates all requirements against all repository folders."""
    
    def __init__(self, ai_client: Optional[Any] = None):
        self.ai_client = ai_client
        
    async def match_all(self, requirements: List[Dict[str, Any]], folders: List[Dict[str, Any]], settings: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
        """Match all requirements to repository folders using AI with automatic heuristic fallback."""
        if self.ai_client is not None:
            try:
                messages = build_folder_matching_prompt(requirements, folders)
                if hasattr(self.ai_client, 'chat_completion_json'):
                    response_json = await self.ai_client.chat_completion_json(messages)
                else:
                    response_json = await self.ai_client.chat_completion(messages)
                    
                if response_json and isinstance(response_json, dict) and 'mappings' in response_json:
                    mappings_list = response_json['mappings']
                    result_map = {}
                    for m in mappings_list:
                        req_id = m.get('req_id')
                        if req_id:
                            result_map[req_id] = m
                    logger.info(f"AI folder matcher succeeded: {len(result_map)} requirements mapped")
                    # Guarantee complete coverage of all SEG-Y and ASCII folders
                    result_map = reconcile_unmapped_segy_ascii(result_map, requirements, folders)
                    return result_map
            except Exception as e:
                logger.warning(f"AI folder matcher call failed, falling back to heuristic matcher: {e}")
        
        # Heuristic fallback
        logger.info("Using heuristic folder matcher fallback")
        return self._heuristic_match_all(requirements, folders)
        
    def _heuristic_match_all(self, requirements: List[Dict[str, Any]], folders: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Heuristic folder matching fallback with multi-folder, multi-domain, and coverage support."""
        folder_dict = {f['name']: f for f in folders}
        mappings = {}
        
        for req in requirements:
            req_id = req.get('req_id', '')
            prog = req.get('progress', '')
            formats = req.get('formats', [])
            r_concepts = parse_seismic_concepts(prog)
            is_angle_req = r_concepts.get('is_angle_stack', False)
            has_both_domains = r_concepts.get('depth', False) and r_concepts.get('time', False)
            is_non_pres = r_concepts.get('non_preserved', False)
            
            format_folders = {}
            all_matched_folders = []
            
            for fmt in formats:
                scored_folders = []
                for f_name, f_data in folder_dict.items():
                    exts = f_data.get('extensions', {})
                    has_fmt = any(is_format_match(ext, fmt) for ext in exts.keys())
                    if not has_fmt:
                        continue
                        
                    sample_file = f_data.get('files', [{}])[0] if f_data.get('files') else {}
                    fi = {
                        'filename': sample_file.get('filename', f_name),
                        'parent_directory': f_name,
                        'relative_path': f"{f_name}/{sample_file.get('filename', '')}",
                        'extension': sample_file.get('extension', '')
                    }
                    
                    level, contras, score = score_candidate(
                        requirement_progress=prog,
                        file_info=fi,
                        tech_val={'valid_segy': True} if fmt == 'SEG-Y' else None,
                        header_lines=f_data.get('header_lines', []),
                        content_preview=f_data.get('content_preview')
                    )
                    
                    if score > 0:
                        scored_folders.append((score, f_name))
                
                scored_folders.sort(key=lambda x: -x[0])
                
                if is_angle_req:
                    # Match ALL angle stack folders with strong positive score
                    angle_matches = [f_name for sc, f_name in scored_folders if sc >= 15 and 'angle' in f_name.lower()]
                    if angle_matches:
                        format_folders[fmt] = angle_matches
                        for am in angle_matches:
                            if am not in all_matched_folders:
                                all_matched_folders.append(am)
                elif has_both_domains:
                    # Collect best matching depth folder AND best matching time folder (including AGC/Final variants)
                    depth_matches = [f_name for sc, f_name in scored_folders if sc >= 10 and any(w in f_name.lower() for w in ('depth', 'sdm'))]
                    time_matches = [f_name for sc, f_name in scored_folders if sc >= 10 and any(w in f_name.lower() for w in ('time', 'stm'))]
                    domain_matches = list(dict.fromkeys(depth_matches + time_matches))
                    if domain_matches:
                        format_folders[fmt] = domain_matches
                        for dm in domain_matches:
                            if dm not in all_matched_folders:
                                all_matched_folders.append(dm)
                elif scored_folders:
                    best_sc, best_f = scored_folders[0]
                    format_folders[fmt] = [best_f]
                    if best_f not in all_matched_folders:
                        all_matched_folders.append(best_f)
                        
            if not all_matched_folders:
                status = 'MISSING'
                confidence = 'HIGH'
                reasoning = f"No matching folder found in repository for '{prog}'"
            elif len(format_folders) == len(formats):
                status = 'PASS'
                confidence = 'HIGH'
                folder_desc = f"{len(all_matched_folders)} folder(s): {', '.join(all_matched_folders)}"
                reasoning = f"Deliverable verified across {folder_desc}"
            else:
                status = 'REVIEW_REQUIRED'
                confidence = 'MEDIUM'
                reasoning = f"Partially matched folders: {', '.join(all_matched_folders)}"
                
            mappings[req_id] = {
                'req_id': req_id,
                'status': status,
                'confidence': confidence,
                'format_folders': format_folders,
                'matched_folders': all_matched_folders,
                'reasoning': reasoning
            }
            
        # Reconcile any remaining unmapped SEG-Y or ASCII folders
        mappings = reconcile_unmapped_segy_ascii(mappings, requirements, folders)
        return mappings
