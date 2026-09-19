from app.services.segy_parser import validate_segy

def test_valid_ascii_segy(valid_ascii_segy):
    result = validate_segy(valid_ascii_segy)
    assert result['valid_segy'] is True
    assert result['textual_header_present'] is True
    assert result['textual_header_encoding'] == 'ASCII'
    assert 'PRE-STACK TIME MIGRATION' in result['textual_header_lines'][0]

def test_valid_ebcdic_segy(valid_ebcdic_segy):
    result = validate_segy(valid_ebcdic_segy)
    assert result['valid_segy'] is True
    assert result['textual_header_present'] is True
    assert result['textual_header_encoding'] == 'EBCDIC'
    assert 'PRE-STACK TIME MIGRATION' in result['textual_header_lines'][0]

def test_empty_header_segy(empty_header_segy):
    result = validate_segy(empty_header_segy)
    assert result['valid_segy'] is True
    assert result['textual_header_present'] is False

def test_corrupted_segy(corrupted_segy):
    result = validate_segy(corrupted_segy)
    assert result['valid_segy'] is False
    assert len(result['validation_errors']) > 0
