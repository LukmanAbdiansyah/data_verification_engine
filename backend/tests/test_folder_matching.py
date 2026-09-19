from app.services.candidate_filter import get_product_folder
from app.services.requirement_normalizer import split_formats, normalize_format
from app.services.file_classifier import is_format_match, classify_file

def test_get_product_folder():
    p1 = r"FINAL PRODUCT STACK VELOCITY SEISMIC PLOT FINAL REPORT\02_FINAL_PRESERVED_AMPLITUDE_STACK_AFTER_PSTM\MINIMUM_PHASE\file.sgy"
    assert get_product_folder(p1) == "02_FINAL_PRESERVED_AMPLITUDE_STACK_AFTER_PSTM"
    
    p2 = r"04_CDP_GATHER_AFTER_PSTM_NMO_APPLIED_PART2\file.sgy"
    assert get_product_folder(p2) == "04_CDP_GATHER_AFTER_PSTM_NMO_APPLIED_PART2"
    
    p3 = r"FINAL PRODUCT STACK VELOCITY SEISMIC PLOT FINAL REPORT\13_FINAL_REPORT\report.pdf"
    assert get_product_folder(p3) == "13_FINAL_REPORT"
    
    p4 = r"FINAL PRODUCT STACK VELOCITY SEISMIC PLOT FINAL REPORT\12_SEISMIC_PLOT\ZERO_PHASE\plot.tiff"
    assert get_product_folder(p4) == "12_SEISMIC_PLOT"

def test_split_formats_with_ampersand():
    res1 = split_formats("SEGY & ASCII")
    assert res1 == ["SEG-Y", "ASCII"]
    
    res2 = split_formats("PDF & hard copy")
    assert res2 == ["PDF"]
    
    res3 = split_formats("MS. WORD FORMAT")
    assert res3 == ["MS-OFFICE"]

def test_tiff_format_support():
    assert classify_file(".tiff") == "TIFF"
    assert classify_file(".tif") == "TIFF"
    assert is_format_match(".tiff", "TIFF") is True
    assert is_format_match(".tif", "TIFF") is True

def test_reconcile_unmapped_segy_ascii():
    from app.services.ai_folder_matcher import reconcile_unmapped_segy_ascii
    
    requirements = [
        {'req_id': 'REQ-001', 'progress': 'Raw PSDM Stack (Preserved)Depth and Time Domain', 'formats': ['SEG-Y']},
        {'req_id': 'REQ-002', 'progress': 'Final Velocity PSDM', 'formats': ['SEG-Y']}
    ]
    
    # Mappings where RAW_PSDM_DEPTH_STACK was initially left unmapped
    mappings = {
        'REQ-001': {
            'req_id': 'REQ-001',
            'status': 'PASS',
            'confidence': 'HIGH',
            'format_folders': {'SEG-Y': ['RAW_PSDM_TIME_STACK']},
            'matched_folders': ['RAW_PSDM_TIME_STACK'],
            'reasoning': 'Matched time stack'
        },
        'REQ-002': {
            'req_id': 'REQ-002',
            'status': 'PASS',
            'confidence': 'HIGH',
            'format_folders': {'SEG-Y': ['INTERVAL_VELOCITY']},
            'matched_folders': ['INTERVAL_VELOCITY'],
            'reasoning': 'Matched velocity'
        }
    }
    
    folders = [
        {
            'name': 'RAW_PSDM_TIME_STACK',
            'extensions': {'.sgy': 4},
            'files': [{'filename': '01.SEGY_RAW_PSDM_TIME_STACK_01.sgy', 'extension': '.sgy'}],
            'header_lines': ['C05 PROCESS : RAW PSDM TIME STACK']
        },
        {
            'name': 'RAW_PSDM_DEPTH_STACK',
            'extensions': {'.sgy': 4},
            'files': [{'filename': '01.SEGY_RAW_PSDM_DEPTH_STACK_01.sgy', 'extension': '.sgy'}],
            'header_lines': ['C05 PROCESS : RAW PSDM DEPTH STACK']
        },
        {
            'name': 'INTERVAL_VELOCITY',
            'extensions': {'.sgy': 4, '.txt': 4},
            'files': [{'filename': '04.SEGY_INTERVAL_VELOCITY_PSDM_01.sgy', 'extension': '.sgy'}],
            'header_lines': ['C05 PROCESS : INTERVAL VELOCITY']
        }
    ]
    
    updated = reconcile_unmapped_segy_ascii(mappings, requirements, folders)
    
    # RAW_PSDM_DEPTH_STACK must be reconciled to REQ-001
    assert 'RAW_PSDM_DEPTH_STACK' in updated['REQ-001']['matched_folders']
    assert 'RAW_PSDM_DEPTH_STACK' in updated['REQ-001']['format_folders']['SEG-Y']

def test_heuristic_match_depth_and_time():
    from app.services.ai_folder_matcher import AIFolderMatcher
    
    matcher = AIFolderMatcher(ai_client=None)
    requirements = [
        {'req_id': 'REQ-003', 'progress': 'Raw PSDM Stack (Preserved)Depth and Time Domain', 'formats': ['SEG-Y']},
    ]
    folders = [
        {
            'name': 'RAW_PSDM_TIME_STACK',
            'extensions': {'.sgy': 4},
            'files': [{'filename': '01.SEGY_RAW_PSDM_TIME_STACK_01.sgy', 'extension': '.sgy'}],
            'header_lines': ['C05 PROCESS : RAW PSDM TIME STACK']
        },
        {
            'name': 'RAW_PSDM_DEPTH_STACK',
            'extensions': {'.sgy': 4},
            'files': [{'filename': '01.SEGY_RAW_PSDM_DEPTH_STACK_01.sgy', 'extension': '.sgy'}],
            'header_lines': ['C05 PROCESS : RAW PSDM DEPTH STACK']
        }
    ]
    
    res = matcher._heuristic_match_all(requirements, folders)
    assert 'RAW_PSDM_TIME_STACK' in res['REQ-003']['matched_folders']
    assert 'RAW_PSDM_DEPTH_STACK' in res['REQ-003']['matched_folders']
    assert res['REQ-003']['status'] == 'PASS'

