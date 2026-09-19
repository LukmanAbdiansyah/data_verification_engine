from app.services.deliverable_parser import _detect_columns, parse_paste
import pytest

def test_detect_columns():
    headers = ["ID", "Deliverable Name", "Expected Format", "Notes"]
    mapping = _detect_columns(headers)
    assert mapping['progress'] == "Deliverable Name"
    assert mapping['format'] == "Expected Format"

def test_parse_paste():
    text = "ID\tProgress\tFormat\n1\tItem A\tPDF\n2\tItem B\tSEG-Y"
    rows, mapping, headers = parse_paste(text)
    assert mapping['progress'] == "Progress"
    assert mapping['format'] == "Format"
    assert len(rows) == 2
    assert rows[0]['progress'] == "Item A"
    assert rows[1]['format_str'] == "SEG-Y"

def test_parse_paste_csv():
    text = "No.,File,Format\n1,Final Velocity PSDM,SEGY\n3,Final PSDM Gather,SEGY"
    rows, mapping, headers = parse_paste(text)
    assert mapping['progress'] == "File"
    assert mapping['format'] == "Format"
    assert len(rows) == 2
    assert rows[0]['progress'] == "Final Velocity PSDM"
    assert rows[1]['format_str'] == "SEGY"
