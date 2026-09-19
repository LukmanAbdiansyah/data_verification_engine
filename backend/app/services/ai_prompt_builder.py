import json
import hashlib
from typing import Dict, List, Any, Optional

SYSTEM_PROMPT = """You are an expert seismic data deliverable verification assistant.

Your task: Given a deliverable requirement, evaluate whether the candidate folder(s) and file(s) from the repository satisfy it.

You will be given:
1. The REQUIREMENT: what deliverable is expected
2. The FULL FOLDER CONTEXT: a summary of ALL top-level folders in the repository (so you understand the overall data organization)
3. The CANDIDATE: the specific folder/files being evaluated for this requirement, including file samples and SEG-Y textual headers if available

Domain knowledge for seismic deliverables:
1. Pre-Migration Gathers at final datum are inherently without NMO (no NMO). Header confirmation of Pre-Migration Gather at final datum satisfies the 'no NMO' requirement.
2. If a requirement specifies both Minimum & Zero Phase and the candidate set contains both MP and ZP files from the respective folders, this satisfies the phase requirement.
3. For final stack deliverables, industry-standard TVF/TVS (Time Variant Filter / Time Variant Scaling) post-stack processing constitutes the final stack.
4. For report deliverables where the expected format is 'PDF & hard copy', the digital PDF deliverable in the repository satisfies the digital verification requirement.
5. For velocity deliverables with expected format 'SEGY & ASCII', valid ASCII (.txt) or SEGY velocity tables satisfy the format expectation.
6. Folder names in seismic data repositories are highly descriptive and usually encode the deliverable type (e.g. "01_PRESERVED_AMPLITUDE_STACK_AFTER_PSTM" clearly indicates preserved amplitude stack data).
7. When a requirement asks for "CDP Gather After PSTM with NMO Applied Zerophase", look for folders containing "ZERO_PHASE" or "ZP" or "ZEROPHASE" in the path.
8. Seismic plot deliverables are typically image files (TIFF, PNG, etc.) showing the processed seismic sections.

IMPORTANT matching rules:
- Focus on the FOLDER NAME as the primary matching signal. Seismic data is organized in descriptively-named folders.
- Consider the full path context, not just individual filenames.
- A folder named "02_FINAL_PRESERVED_AMPLITUDE_STACK..." matches "Final Preserved Amplitude Stack", not "Final Non-Preserved Amplitude Stack".
- A folder named "03_FINAL_NON_PRESERVED_AMPLITUDE..." matches "Final Non-Preserved Amplitude Stack".
- If the candidate folder name clearly describes the deliverable type and matches the requirement, that is strong evidence of SUPPORTED.
- Only report CONFLICT or NOT_SUPPORTED if the folder/file evidence clearly contradicts the requirement.

Return valid JSON only with this exact schema:
{
  "assessment": "SUPPORTED | PARTIALLY_SUPPORTED | INSUFFICIENT_EVIDENCE | CONFLICT | NOT_SUPPORTED",
  "matched_evidence": ["list of evidence supporting the match"],
  "missing_evidence": ["list of expected evidence not found"],
  "contradictions": ["list of conflicting evidence"],
  "reasoning_summary": "brief explanation (1-2 sentences)"
}"""


def _build_folder_context(all_folders: List[Dict[str, Any]]) -> str:
    """Build a concise summary of ALL top-level folders for context."""
    if not all_folders:
        return "No folder structure available."
    
    lines = ["REPOSITORY FOLDER STRUCTURE (all top-level folders):"]
    for folder in all_folders:
        name = folder.get('name', '')
        file_count = folder.get('file_count', 0)
        extensions = folder.get('extensions', {})
        ext_str = ', '.join(f"{ext}:{cnt}" for ext, cnt in sorted(extensions.items())[:5])
        subfolder_count = folder.get('subfolder_count', 0)
        
        detail = f"  - {name}/ ({file_count} files"
        if ext_str:
            detail += f", types: {ext_str}"
        if subfolder_count > 0:
            detail += f", {subfolder_count} subfolders"
        detail += ")"
        lines.append(detail)
    
    return '\n'.join(lines)


def build_verification_prompt(requirement: Dict[str, Any], candidate: Dict[str, Any],
                               folder_context: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, str]]:
    """Build verification prompt with folder context awareness."""
    user_parts = []
    
    # Section 1: The Requirement
    user_parts.append("=" * 60)
    user_parts.append("REQUIREMENT")
    user_parts.append("=" * 60)
    user_parts.append(f"Deliverable: {requirement.get('progress', '')}")
    user_parts.append(f"Expected Format: {candidate.get('format_name', '')}")
    user_parts.append("")
    
    # Section 2: Full Repository Context (so AI sees the big picture)
    if folder_context:
        user_parts.append("=" * 60)
        user_parts.append(_build_folder_context(folder_context))
        user_parts.append("")
    
    # Section 3: The Candidate being evaluated
    user_parts.append("=" * 60)
    user_parts.append("CANDIDATE BEING EVALUATED")
    user_parts.append("=" * 60)
    
    # Show folder-level info
    candidate_folder = candidate.get('folder_name', '')
    candidate_folder_path = candidate.get('folder_path', '')
    if candidate_folder:
        user_parts.append(f"Folder: {candidate_folder}")
    if candidate_folder_path and candidate_folder_path != candidate_folder:
        user_parts.append(f"Full Path: {candidate_folder_path}")
    
    matching_files = candidate.get('matching_files', [])
    matching_paths = candidate.get('matching_paths', [])
    
    if matching_files and len(matching_files) > 1:
        folder_display = candidate.get('folder_display') or candidate.get('folder_name', '') or candidate['file_info'].get('parent_directory', '')
        user_parts.append(f"File Count: {len(matching_files)} files in '{folder_display}'")
        user_parts.append("")
        user_parts.append("Sample files:")
        
        # Smart sampling: show representative files
        shown = set()
        samples = []
        
        # Try to show diverse samples (different subdirectories, different names)
        for mf, mp in zip(matching_files, matching_paths):
            if len(samples) >= 10:
                break
            # Show files from different subdirectories
            parent = mp.replace('\\', '/').rsplit('/', 1)[0] if '/' in mp.replace('\\', '/') else ''
            key = parent if parent else mf
            if key not in shown or len(samples) < 5:
                shown.add(key)
                samples.append(f"  - {mp}")
        
        for s in samples:
            user_parts.append(s)
        if len(matching_files) > len(samples):
            user_parts.append(f"  - ... and {len(matching_files) - len(samples)} more files")
    elif matching_files:
        user_parts.append(f"File: {matching_files[0]}")
        if matching_paths:
            user_parts.append(f"Path: {matching_paths[0]}")
    else:
        user_parts.append(f"Filename: {candidate['file_info']['filename']}")
        user_parts.append(f"Path: {candidate['file_info']['relative_path']}")
    
    # Show subfolders if available
    subfolders = candidate.get('subfolders', [])
    if subfolders:
        user_parts.append("")
        user_parts.append("Subfolders in candidate directory:")
        for sf in subfolders[:15]:
            user_parts.append(f"  - {sf}")
        if len(subfolders) > 15:
            user_parts.append(f"  - ... and {len(subfolders) - 15} more subfolders")
    
    # Technical validation
    tech = candidate.get('technical_validation')
    if tech:
        user_parts.append("")
        user_parts.append("TECHNICAL VALIDATION")
        if tech.get('valid_segy') is not None:
            user_parts.append(f"SEG-Y Valid: {tech['valid_segy']}")
    
    # Textual headers from SEG-Y files
    header_lines = candidate.get('header_lines', [])
    non_empty_headers = [l for l in header_lines if l.strip()]
    if non_empty_headers:
        user_parts.append("")
        user_parts.append("SEG-Y TEXTUAL HEADER (from sample file)")
        for line in non_empty_headers[:20]:
            user_parts.append(line)
    
    # Extra headers (e.g. complementary phase)
    extra_headers = candidate.get('extra_headers', [])
    if extra_headers:
        non_empty_extra = [l for l in extra_headers if l.strip()]
        if non_empty_extra:
            user_parts.append("")
            user_parts.append("ADDITIONAL SEG-Y HEADER (complementary phase/variant)")
            for line in non_empty_extra[:10]:
                user_parts.append(line)
    
    # Content preview (for PDF/Office documents)
    content = candidate.get('content_preview')
    if content and isinstance(content, dict):
        user_parts.append("")
        user_parts.append("DOCUMENT CONTENT EVIDENCE")
        if content.get('title'):
            user_parts.append(f"Title: {content['title']}")
        if content.get('headings'):
            user_parts.append(f"Headings: {', '.join(content['headings'][:5])}")
        if content.get('pages_text'):
            for i, page_text in enumerate(content['pages_text'][:2]):
                user_parts.append(f"Page {i+1} excerpt: {page_text[:300]}")
        elif content.get('preview_lines'):
            user_parts.append("First lines:")
            for line in content['preview_lines'][:10]:
                user_parts.append(f"  {line}")
        elif content.get('content_preview'):
            user_parts.append(f"Content: {content['content_preview'][:300]}")
    
    # Task instruction
    user_parts.append("")
    user_parts.append("=" * 60)
    user_parts.append("TASK")
    user_parts.append("=" * 60)
    user_parts.append("Evaluate whether the CANDIDATE folder/files satisfy the REQUIREMENT.")
    user_parts.append("Use the REPOSITORY FOLDER STRUCTURE context to understand the overall data organization.")
    user_parts.append("Focus on folder names as primary evidence — seismic data is organized in descriptively-named folders.")
    user_parts.append("Return the structured JSON assessment immediately.")
    
    return [
        {'role': 'system', 'content': SYSTEM_PROMPT},
        {'role': 'user', 'content': '\n'.join(user_parts)}
    ]


def compute_cache_key(requirement: Dict[str, Any], candidate: Dict[str, Any], model_name: str, prompt_version: str = 'v2') -> str:
    key_data = {
        'progress': requirement.get('progress', ''),
        'format': candidate.get('format_name', ''),
        'folder_name': candidate.get('folder_name', ''),
        'file_path': candidate['file_info']['relative_path'],
        'file_size': candidate['file_info']['size_bytes'],
        'file_mtime': candidate['file_info']['modified_time'],
        'model': model_name,
        'prompt_version': prompt_version,
    }
    key_str = json.dumps(key_data, sort_keys=True)
    return hashlib.sha256(key_str.encode()).hexdigest()
