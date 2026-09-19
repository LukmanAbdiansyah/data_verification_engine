from app.services.decision_engine import decide_single_format, decide_requirement

def test_decide_single_format_missing():
    result = decide_single_format({"progress": "Test"}, "PDF", [])
    assert result['system_status'] == "MISSING"

def test_decide_single_format_segy_invalid():
    candidates = [{
        'file_info': {'filename': 'test.sgy', 'relative_path': 'test.sgy'},
        'technical_validation': {'valid_segy': False},
        'evidence_level': 'INSUFFICIENT'
    }]
    result = decide_single_format({"progress": "Test"}, "SEG-Y", candidates)
    assert result['system_status'] == "INVALID"

def test_decide_single_format_no_ai_very_high():
    candidates = [{
        'file_info': {'filename': 'test.pdf', 'relative_path': 'test.pdf'},
        'evidence_level': 'VERY_HIGH',
        'technical_validation': None
    }]
    result = decide_single_format({"progress": "Test"}, "PDF", candidates, ai_enabled=False)
    assert result['system_status'] == "PASS"

def test_decide_requirement():
    assert decide_requirement({"PDF": "PASS"}) == "PASS"
    assert decide_requirement({"PDF": "PASS", "SEG-Y": "MISSING"}) == "PARTIAL"
    assert decide_requirement({"PDF": "MISSING", "SEG-Y": "MISSING"}) == "MISSING"
    assert decide_requirement({"PDF": "REVIEW_REQUIRED"}) == "REVIEW_REQUIRED"
    assert decide_requirement({"PDF": "INVALID"}) == "INVALID"

def test_get_folder_summary():
    from app.services.decision_engine import get_folder_summary
    paths = [
        r"06.ANGLE_STACK\MINIMUM PHASE\FAR-ANGLE-STACK\file1.sgy",
        r"06.ANGLE_STACK\ZERO PHASE\NEAR-ANGLE-STACK-ZP\file2.sgy"
    ]
    summary = get_folder_summary(paths)
    assert "06.ANGLE_STACK" in summary

def test_parse_angle_stacks():
    from app.services.evidence_service import parse_seismic_concepts
    req = "Angle stack ( near, mid, far, ultra far) : Minimum & Zero Phase"
    c = parse_seismic_concepts(req)
    assert c['is_angle_stack'] is True
    assert c['has_near'] is True
    assert c['has_mid'] is True
    assert c['has_far'] is True
    assert c['has_ultra_far'] is True
    assert c['has_min_phase'] is True
    assert c['has_zero_phase'] is True

def test_contradiction_raw_stack_vs_angle_stack():
    """Heuristic contradictions are now relaxed — ambiguous cases like angle stack vs raw stack
    are left to the AI assessor which has full folder context. The score_candidate function
    should still give a LOW score for mismatched candidates, but not flag contradictions."""
    from app.services.evidence_service import detect_contradictions, score_candidate
    req = "Angle stack ( near, mid, far, ultra far) : Minimum & Zero Phase"
    contras = detect_contradictions(
        requirement_progress=req,
        filename="01.SEGY_RAW_PSTM_STACK_MP_KT86-15.sgy",
        header_lines=["C05 PROCESS : RAW PSTM STACK (MINIMUM PHASE)"],
        parent_dir="MINIMUM-PHASE",
        relative_path=r"01.SEGY_RAW_PSTM_STACK\MINIMUM-PHASE\01.SEGY_RAW_PSTM_STACK_MP_KT86-15.sgy"
    )
    # Contradictions are now relaxed — this should NOT flag a contradiction
    # (the AI with folder context handles this better)
    assert len(contras) == 0

def test_matching_angle_stack():
    from app.services.evidence_service import score_candidate
    req = "Angle stack ( near, mid, far, ultra far) : Minimum & Zero Phase"
    fi = {
        'filename': "06.SEGY_FAR_ANGLE_PSTM_STACK_KT86-15.sgy",
        'parent_directory': "FAR-ANGLE-STACK",
        'relative_path': r"06.ANGLE_STACK\MINIMUM PHASE\FAR-ANGLE-STACK\06.SEGY_FAR_ANGLE_PSTM_STACK_KT86-15.sgy",
        'extension': '.sgy'
    }
    hl = ["C05 PROCESS : FAR ANGLE PSTM STACK MINIMUM PHASE (22-35 DEG)"]
    tech = {'valid_segy': True}
    lvl, contras, score = score_candidate(req, fi, tech, hl, None)
    assert len(contras) == 0
    assert lvl == "VERY_HIGH"
    assert score >= 20
