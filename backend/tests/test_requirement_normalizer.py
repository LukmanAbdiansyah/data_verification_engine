from app.services.requirement_normalizer import normalize_format, split_formats, normalize_requirements

def test_normalize_format():
    assert normalize_format("segy") == "SEG-Y"
    assert normalize_format("MS OFFICE") == "MS-OFFICE"
    assert normalize_format("Unknown") == "Unknown"

def test_split_formats():
    assert split_formats("segy, pdf, txt") == ["SEG-Y", "PDF", "TXT"]
    assert split_formats("MS OFFICE") == ["MS-OFFICE"]

def test_normalize_requirements():
    rows = [
        {"progress": "Item 1", "format_str": "segy"},
        {"progress": "Item 1", "format_str": "SEG Y"}, # Duplicate
        {"progress": "", "format_str": "pdf"},
        {"progress": "Item 3", "format_str": "UnknownFormat"}
    ]
    reqs = normalize_requirements(rows)
    assert reqs[0]['req_id'] == "REQ-001"
    assert reqs[0]['formats'] == ["SEG-Y"]
    assert reqs[0]['validation_note'] is None
    
    assert reqs[1]['validation_note'] == "Duplicate Requirement"
    assert reqs[2]['validation_note'] == "Empty Progress"
    assert "Unknown Format" in reqs[3]['validation_note']
