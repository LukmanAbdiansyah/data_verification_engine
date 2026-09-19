from app.services.file_classifier import classify_file, is_format_match

def test_classify_file():
    assert classify_file('.sgy') == 'SEG-Y'
    assert classify_file('.pdf') == 'PDF'
    assert classify_file('.docx') == 'DOCX'
    assert classify_file('.unknown') == 'OTHER'

def test_is_format_match():
    assert is_format_match('.sgy', 'SEG-Y') is True
    assert is_format_match('.txt', 'ASCII') is True
    assert is_format_match('.pdf', 'SEG-Y') is False
